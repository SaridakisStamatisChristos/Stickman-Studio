# Created by Atharv Hatwar
"""
cis_manifest_builder.py - Dynamic Multi-Style & Multi-Sprite Manifest Builder for autopilot.mjs.

Supports B1 (Sketchbook Ink), B2 (Editorial Cream), and B3 (Obsidian Dark Chalkboard),
translates modular sprite choreography plans (`_sprite_plan`, `_vector_plan`) and
6 distinct `layout_mode` architectures into valid, smooth keyframed layers for
`autopilot-render.mjs`, with full 9:16 & 16:9 aspect support.
"""

from __future__ import annotations

import json
import logging
import math
import wave
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

WORDS_PER_SECOND = 2.3
SFX_KINDS = ["tap", "pop", "chime", "paper", "jingle"]
SFX_GAINS = {"tap": 0.14, "pop": 0.18, "chime": 0.22, "paper": 0.15, "jingle": 0.20}


def _word_count(text: str) -> int:
    return max(1, len(text.split()))


def _distribute_durations(scenes: list[dict], total_duration: float) -> list[float]:
    wcs = [_word_count(s.get("narration", "")) for s in scenes]
    total_wc = sum(wcs) or 1
    base = [total_duration * (wc / total_wc) for wc in wcs]
    if total_duration > len(scenes) * 2.2:
        base = [max(2.2, b) for b in base]
    actual = sum(base)
    if actual > 0:
        scale = total_duration / actual
        base = [b * scale for b in base]
    rounded = [round(b, 3) for b in base[:-1]]
    last = round(total_duration - sum(rounded), 3)
    rounded.append(last)
    return rounded


def _build_captions(
    scenes: list[dict],
    scene_starts: list[float],
    scene_durations: list[float],
    total_duration: float,
) -> list[dict]:
    captions: list[dict] = []
    max_safe_end = max(0.1, total_duration - 0.02)
    last_end = 0.0

    for sc, start, dur in zip(scenes, scene_starts, scene_durations):
        narration = " ".join(str(sc.get("narration", "")).split())
        if not narration:
            continue
        # Ensure no speaker prefixes or markdown asterisks leak into captions
        import re as _re
        narration = _re.sub(
            r"^\s*(?:\*\*)?(?:\[)?(?:alex|maya|speaker\s*1|speaker\s*2|voice\s*1|voice\s*2|male\s*voice|female\s*voice|male|female)(?:\])?(?:\*\*)?\s*[:\-–—]\s*",
            "",
            narration,
            flags=_re.IGNORECASE,
        ).strip()
        narration = _re.sub(r"[*_]+", "", narration).strip()
        if not narration:
            continue
        words = narration.split()
        chunks: list[str] = []
        cur: list[str] = []
        for w in words:
            cur.append(w)
            joined = " ".join(cur)
            if len(cur) >= 4 or len(joined) > 26 or w.endswith((".", "!", "?", ",", ";", ":")):
                chunks.append(joined)
                cur = []
        if cur:
            chunks.append(" ".join(cur))
        if not chunks:
            chunks = [narration]

        # Spoken window for caption display (clears during breathing silence gap)
        a_dur = float(sc.get("_audio_duration", 0.0))
        spoken_span = a_dur if (a_dur > 0 and a_dur <= dur) else max(0.1, dur - float(sc.get("_silence_gap", 0.12)))

        c_weights = [_word_count(c) for c in chunks]
        total_cw = sum(c_weights) or 1
        t_cursor = max(last_end, round(start + 0.030, 3))
        cap_avail = max(0.2, spoken_span - 0.040)
        for c_text, cw in zip(chunks, c_weights):
            c_dur = cap_avail * (cw / total_cw)
            c_start = round(min(max_safe_end - 0.05, t_cursor), 3)
            c_end = round(min(max_safe_end, c_start + c_dur), 3)
            if c_end <= c_start:
                c_end = round(min(max_safe_end, c_start + 0.1), 3)
            
            chunk_words = c_text.split()
            word_list = []
            if chunk_words:
                w_step = (c_end - c_start) / max(1, len(chunk_words))
                for w_i, word_str in enumerate(chunk_words):
                    w_s = round(c_start + w_i * w_step, 3)
                    w_e = round(w_s + w_step, 3)
                    word_list.append({"word": word_str, "start": w_s, "end": w_e})

            captions.append({"start": c_start, "end": c_end, "text": c_text, "words": word_list})
            t_cursor = c_end
            last_end = c_end

    i = 1
    while i < len(captions):
        if captions[i]["start"] < captions[i - 1]["end"]:
            captions[i]["start"] = captions[i - 1]["end"]
        if captions[i]["end"] <= captions[i]["start"]:
            new_end = round(min(max_safe_end, captions[i]["start"] + 0.05), 3)
            if new_end <= captions[i]["start"]:
                captions.pop(i)  # zero-length at max_safe_end — drop it
                continue
            captions[i]["end"] = new_end
        i += 1

    if captions:
        captions[-1]["end"] = min(captions[-1]["end"], max_safe_end)
    return captions


def _build_sfx(scene_starts: list[float], total_duration: float) -> list[dict]:
    sfx: list[dict] = []
    max_t = max(0.1, total_duration - 0.45)
    for i, start in enumerate(scene_starts):
        t1 = round(start + 0.30, 2)
        if t1 < max_t:
            kind = SFX_KINDS[i % len(SFX_KINDS)]
            sfx.append({"time": t1, "kind": kind, "gain": SFX_GAINS[kind]})
        if i % 2 == 1:
            t2 = round(start + 2.6, 2)
            if t2 < max_t:
                sfx.append({"time": t2, "kind": "pop", "gain": 0.12})
    return sfx


def generate_ambient_score(output_wav: str, duration: float = 20.0) -> bool:
    p = Path(output_wav)
    if p.exists() and p.stat().st_size > 10000:
        return True
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        sr = 44100
        music_dur = max(4.0, float(duration) + 2.5)
        t = np.linspace(0, music_dur, int(sr * music_dur), endpoint=False)
        bg = np.zeros_like(t)
        chords = [
            [73.42, 110.00, 174.61, 261.63, 329.63],
            [58.27, 87.31, 146.83, 220.00],
            [65.41, 110.00, 164.81, 196.00],
            [82.41, 98.00, 130.81, 164.81],
        ]
        cycle = 6.8
        for c_i, notes in enumerate(chords):
            c_start = c_i * cycle
            while c_start < music_dur:
                mask = (t >= c_start) & (t < c_start + cycle)
                if np.any(mask):
                    t_sub = t[mask] - c_start
                    env = np.sin(np.pi * np.clip(t_sub / cycle, 0, 1)) ** 0.65
                    chord_sig = np.zeros(np.count_nonzero(mask), dtype=np.float64)
                    for n_idx, freq in enumerate(notes):
                        chord_sig += (0.55 / (n_idx + 1)) * (
                            np.sin(2 * np.pi * freq * t[mask]) + 0.22 * np.sin(4 * np.pi * freq * t[mask])
                        )
                    bg[mask] += chord_sig * env * 0.26
                c_start += 4 * cycle
        bg *= (1.0 + 0.0025 * np.sin(2 * np.pi * 0.35 * t))
        fade_in = np.clip(t / 2.0, 0, 1)
        fade_out = np.clip((music_dur - t) / 2.5, 0, 1)
        bg = bg * fade_in * fade_out * 0.22
        stereo = np.stack([bg, np.roll(bg, int(0.015 * sr))], axis=1)
        data = (np.clip(stereo, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
        with wave.open(str(p), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(data)
        return True
    except Exception as exc:
        logger.warning("Could not generate ambient score: %s", exc)
        return False


def generate_bg_paper(
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    tint_hex: str = "#FAF8F3",
    is_dark: bool = False,
    draw_grid: bool = False,
) -> bool:
    """Generate a seamless full-screen texture matched to B1/B2 light paper or B3 dark obsidian."""
    p = Path(output_path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        hex_c = tint_hex.strip() if isinstance(tint_hex, str) else "#FAF8F3"
        if not (hex_c.startswith("#") and len(hex_c) == 7):
            hex_c = "#111316" if is_dark else "#FAF8F3"
        br = int(hex_c[1:3], 16)
        bg = int(hex_c[3:5], 16)
        bb = int(hex_c[5:7], 16)

        y_idx, x_idx = np.ogrid[:height, :width]
        nx = (x_idx - width * 0.5) / (width * 0.5)
        ny = (y_idx - height * 0.5) / (height * 0.5)
        dist = np.sqrt(nx * nx + ny * ny)
        falloff = np.clip((dist - 0.45) / 0.90, 0.0, 1.0)

        rng = np.random.default_rng(42)
        base = np.zeros((height, width, 3), dtype=np.float32)

        if is_dark:
            # Dark obsidian / blueprint with soft radial center illumination
            glow = (1.0 - np.clip(dist / 1.15, 0.0, 1.0)) * 18.0
            grain = rng.normal(0.0, 1.5, size=(height, width, 1))
            base[:, :, 0] = br + glow
            base[:, :, 1] = bg + glow * 1.1
            base[:, :, 2] = bb + glow * 1.3
            if draw_grid:
                step = max(48, width // 18)
                base[::step, :, :] += np.array([10.0, 22.0, 36.0], dtype=np.float32)
                base[:, ::step, :] += np.array([10.0, 22.0, 36.0], dtype=np.float32)
            arr = np.clip(base + grain, 0, 255).astype(np.uint8)
        else:
            shade = 1.0 - 0.055 * (falloff ** 1.6)
            grain = rng.normal(0.0, 1.8, size=(height, width, 1))
            base[:, :, 0] = br * shade
            base[:, :, 1] = bg * shade
            base[:, :, 2] = bb * shade
            # Crisp notebook grid ONLY for classic B1 Sketchbook look
            if draw_grid:
                step = max(48, width // 18)
                base[::step, :, :] *= 0.955
                base[:, ::step, :] *= 0.955
            arr = np.clip(base + grain, 0, 255).astype(np.uint8)

        Image.fromarray(arr, mode="RGB").save(str(p), "PNG")
        return True
    except Exception as exc:
        logger.warning("Could not generate background texture: %s", exc)
        return False


def generate_shot_procedural_background(
    output_path: str,
    scene: dict,
    scene_idx: int,
    width: int = 1080,
    height: int = 1920,
    tint_hex: str = "#FAF8F3",
    is_dark: bool = False,
    draw_grid: bool = False,
    style: str = "B1",
    accent: str = "#38BDF8",
    topic: str = "",
) -> bool:
    """Generate an individual, topic-tailored procedural vector background for this shot."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # 1. Base paper / obsidian texture
    generate_bg_paper(output_path, width=width, height=height, tint_hex=tint_hex, is_dark=is_dark, draw_grid=draw_grid)

    # 2. Paint procedural environment on top
    try:
        from engine.ai_background_engine import AIBackgroundEngine
        im = Image.open(output_path).convert("RGBA")
        d = ImageDraw.Draw(im)
        floor_y = int(height * 0.74)
        topic_val = str(topic or scene.get("topic") or "").strip()
        narr = f"{topic_val}. {scene.get('narration', '')} {scene.get('scene_title', '')}".strip()

        style_params = {
            "fg": "#E2E8F0" if is_dark else "#334155",
            "bg": tint_hex,
            "accent": accent,
            "accent_secondary": "#F43F5E" if is_dark else "#0284C7",
            "line_width": max(2, int(width / 360)),
            "is_dark": is_dark,
        }
        sid = "b3_dark" if is_dark else "b1_light"
        AIBackgroundEngine.render_ai_background(
            draw=d,
            narration=narr,
            scene_idx=scene_idx,
            w=width,
            h=height,
            floor_y=floor_y,
            style_params=style_params,
            style_id=sid,
        )
        im.convert("RGB").save(output_path, "PNG")
        return True
    except Exception as exc:
        logger.warning("Could not render procedural shot background for scene %d: %s", scene_idx, exc)
        return False


def _make_relative(path_str: str, base_dir: str) -> str:
    try:
        return str(Path(path_str).relative_to(base_dir)).replace("\\", "/")
    except ValueError:
        return Path(path_str).name.replace("\\", "/")


def _safe_autopilot_text(raw: str, max_chars: int = 28) -> str:
    cleaned = " ".join((raw or "").split())
    words = [w[:16] for w in cleaned.split()]
    out = " ".join(words)
    if len(out) > max_chars:
        cut = out[:max_chars].rsplit(" ", 1)[0]
        out = cut if cut else out[:max_chars]
    return out or "INSIGHT"


def _fit_font_size(text: str, target_size: int, box_w: float) -> int:
    """Prevent autopilot wrap() errors when long uppercase words appear."""
    tokens = (text or "X").split()
    longest = max((len(t) for t in tokens), default=1)
    max_safe = int((box_w * 0.86) / max(1.0, longest * 0.72))
    return max(18, min(target_size, max_safe))


def _stage_mapper(plane_w: float, plane_h: float):
    """Map virtual 1280x2140 portrait stage coords cleanly to either 9:16 or 16:9."""
    if plane_h >= plane_w:
        scale = 1.0
        ox = 0.0
        oy = 0.0
    else:
        scale = max(0.24, (plane_h - 110.0) / 1720.0)
        ox = (plane_w - 1280.0 * scale) * 0.5
        oy = -35.0 * scale

    def pt(vx: float, vy: float) -> tuple[float, float]:
        return round(ox + vx * scale, 1), round(max(10.0, oy + vy * scale), 1)

    def sz(vw: float) -> float:
        return max(12.0, round(vw * scale, 1))

    return pt, sz, scale


def _norm_t(frac: float, span: float) -> float:
    safe_max = max(0.05, span - 0.02)
    return round(max(0.0, min(safe_max, frac * safe_max)), 3)


def _clean_keys(keys: list[dict], span: float) -> list[dict]:
    """Ensure strictly increasing timestamps in [0, span - 0.02] and valid values."""
    safe_max = max(0.05, span - 0.02)
    out: list[dict] = []
    prev_t = -1.0
    for k in sorted(keys, key=lambda item: float(item.get("t", 0.0))):
        kt = max(0.0, min(safe_max, float(k.get("t", 0.0))))
        if kt <= prev_t:
            kt = round(prev_t + 0.015, 3)
        if kt > safe_max:
            continue
        prev_t = kt
        ck: dict[str, Any] = {"t": round(kt, 3)}
        for fld in ("x", "y", "angle"):
            if fld in k and k[fld] is not None:
                ck[fld] = round(float(k[fld]), 4 if fld == "angle" else 1)
        if "w" in k and k["w"] is not None:
            ck["w"] = max(4.0, round(float(k["w"]), 1))
        for fld in ("alpha", "progress"):
            if fld in k and k[fld] is not None:
                ck[fld] = round(max(0.0, min(1.0, float(k[fld]))), 3)
        for fld in ("scaleX", "scaleY"):
            if fld in k and k[fld] is not None:
                ck[fld] = round(max(0.05, min(10.0, float(k[fld]))), 3)
        out.append(ck)
    return out


def _rotated_xy(
    cx: float,
    cy: float,
    w: float,
    img_w: int,
    img_h: int,
    angle: float,
    anchor: tuple[float, float] = (0.5, 0.5),
) -> tuple[float, float]:
    """Compensate top-left (x, y) so top-left canvas rotation pivots cleanly at anchor."""
    h = w * (float(img_h) / max(1.0, float(img_w)))
    dx = anchor[0] * w
    dy = anchor[1] * h
    ca = math.cos(angle)
    sa = math.sin(angle)
    x = cx - (dx * ca - dy * sa)
    y = cy - (dx * sa + dy * ca)
    return round(x, 1), round(y, 1)


def _generate_alive_keyframes(
    cx_base: float,
    cy_base: float,
    w_base: float,
    img_w: int,
    img_h: int,
    from_frac: float,
    to_frac: float,
    span: float,
    sz_fn,
    lerp_t_fn,
    base_angle: float = 0.0,
) -> list[dict[str, Any]]:
    """Generate continuous organic living kinematics (breathing, sway, emphasis gesture) so actors never freeze."""
    keys: list[dict[str, Any]] = []
    dur_sec = max(0.2, (to_frac - from_frac) * span)
    steps = max(3, min(16, int(round(dur_sec / 0.42))))

    for i in range(1, steps + 1):
        frac = from_frac + (i / float(steps)) * (to_frac - from_frac)
        t_sec = frac * span

        # 1. Breathing cycle (~1.25 Hz)
        t_breath = t_sec * 2.0 * math.pi * 1.25
        dy_breath = math.sin(t_breath) * sz_fn(4.5)
        dw_breath = w_base * (1.0 + 0.012 * math.cos(t_breath))

        # 2. Subtle weight sway (~0.65 Hz)
        t_sway = t_sec * 2.0 * math.pi * 0.65 + 0.5
        dx_sway = math.sin(t_sway) * sz_fn(3.2)
        dang_sway = math.sin(t_sway) * 0.016

        # 3. Narrative emphasis gesture envelope (peaks around mid-shot)
        norm_progress = (frac - from_frac) / max(0.01, to_frac - from_frac)
        if 0.38 <= norm_progress <= 0.62:
            env = math.sin((norm_progress - 0.38) / 0.24 * math.pi)
            dy_gest = -sz_fn(7.0) * env
            dang_gest = 0.028 * env
            dw_gest = w_base * 0.02 * env
        else:
            dy_gest = 0.0
            dang_gest = 0.0
            dw_gest = 0.0

        cur_cx = cx_base + dx_sway
        cur_cy = cy_base + dy_breath + dy_gest
        cur_w = dw_breath + dw_gest
        cur_ang = base_angle + dang_sway + dang_gest

        kx, ky = _rotated_xy(cur_cx, cur_cy, cur_w, img_w, img_h, cur_ang)
        keys.append({
            "t": lerp_t_fn(frac),
            "x": kx,
            "y": ky,
            "w": cur_w,
            "angle": cur_ang,
            "alpha": 1.0,
        })
    return keys


def _animate_sprite(
    spec: dict[str, Any],
    meta: dict[str, Any],
    out_dir: Path,
    span: float,
    pt,
    sz,
) -> dict[str, Any]:
    """Translate a declarative `_sprite_plan` item into rich autopilot keyframes."""
    anim = str(spec.get("anim", "pop_bounce"))
    rel_path = _make_relative(meta["path"], str(out_dir))
    img_w, img_h = int(meta.get("w", 300)), int(meta.get("h", 300))

    from_f = float(spec.get("from_f", 0.0))
    to_f = max(from_f + 0.15, float(spec.get("to_f", 1.0)))
    from_t = _norm_t(from_f, span)
    to_t = _norm_t(to_f, span) if to_f < 0.99 else None
    w = sz(float(spec.get("w", 320)))

    sp_name = str(spec.get("sprite", ""))
    sp_name_l = sp_name.lower()
    actor_keywords = (
        "actor", "hero", "thinker", "climber", "runner", "trader", "doctor",
        "student", "person", "stickman", "worker", "coder", "boss", "couple",
        "pedestal", "mentor", "user", "speaker", "seeker", "giver", "fig",
        "expert", "master", "challenger", "winner", "rival", "player", "audience",
        "patient", "client", "buyer", "seller", "founder", "leader"
    )
    is_actor = (spec.get("is_actor", False) or any(k in sp_name_l for k in actor_keywords)) and not any(
        ck in sp_name_l for ck in ("card", "badge", "banner", "board", "wall", "cliff", "floor", "bg", "lamp", "bulb", "screen", "chart", "window", "pill", "ring", "aura", "spark", "phone", "goal", "button", "shield")
    )

    def _lerp_t(p: float) -> float:
        end_p = min(1.0, to_f) if to_t is not None else 1.0
        return _norm_t(from_f + p * max(0.08, end_p - from_f), span)

    raw_keys: list[dict[str, Any]] = []
    init_cx, init_cy = pt(float(spec.get("cx0", 640)), float(spec.get("cy0", 960)))
    init_x, init_y = _rotated_xy(init_cx, init_cy, w, img_w, img_h, 0.0)

    if anim == "walk_to":
        cx0, cy0 = pt(float(spec.get("cx0", 300)), float(spec.get("cy0", 1050)))
        cx1, cy1 = pt(float(spec.get("cx1", 850)), float(spec.get("cy1", 1050)))
        hops = max(2, min(6, int(spec.get("hops", 3))))
        steps = hops * 2 + 1
        walk_end_frac = 0.55 if (is_actor and to_f >= 0.95 and spec.get("hops", 3) <= 2) else 1.0
        for k in range(steps):
            frac = (k / float(steps - 1)) * walk_end_frac
            cx = cx0 + (cx1 - cx0) * (k / float(steps - 1))
            lift = -abs(math.sin((k / float(steps - 1)) * hops * math.pi)) * sz(34.0)
            cy = cy0 + (cy1 - cy0) * (k / float(steps - 1)) + lift
            ang = 0.045 * math.sin((k / float(steps - 1)) * hops * math.pi * 2)
            x, y = _rotated_xy(cx, cy, w, img_w, img_h, ang)
            raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": w, "angle": ang, "alpha": 1.0 if k > 0 else 0.7})
        if is_actor and walk_end_frac < 0.95:
            raw_keys.extend(_generate_alive_keyframes(cx1, cy1, w, img_w, img_h, walk_end_frac, 1.0, span, sz, _lerp_t))
        init_x, init_y = raw_keys[0]["x"], raw_keys[0]["y"]

    elif anim == "hop_steps":
        pts_v = spec.get("pts") or [[265, 955], [620, 795], [975, 640]]
        pts = [pt(p[0], p[1]) for p in pts_v]
        if len(pts) >= 2:
            raw_pts_t: list[tuple[float, float, float, float]] = []
            seg = 1.0 / (len(pts) - 1)
            for idx in range(len(pts) - 1):
                p0, p1 = pts[idx], pts[idx + 1]
                t0 = idx * seg
                t_mid = (idx + 0.5) * seg
                raw_pts_t.append((t0, p0[0], p0[1], -0.04))
                raw_pts_t.append((t_mid, (p0[0] + p1[0]) * 0.5, min(p0[1], p1[1]) - sz(110.0), 0.05))
            raw_pts_t.append((1.0, pts[-1][0], pts[-1][1], 0.0))
            for frac, cx, cy, ang in raw_pts_t:
                x, y = _rotated_xy(cx, cy, w, img_w, img_h, ang)
                raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": w, "angle": ang})
            init_x, init_y = raw_keys[0]["x"], raw_keys[0]["y"]

    elif anim == "shake_ring":
        cx, cy = init_cx, init_cy
        amp = float(spec.get("amp", 0.08))
        seq = [(0.0, 0.0), (0.12, -amp), (0.24, amp), (0.36, -amp * 0.85), (0.48, amp * 0.85), (0.62, -amp * 0.4), (0.76, amp * 0.3), (1.0, 0.0)]
        for frac, ang in seq:
            x, y = _rotated_xy(cx, cy, w, img_w, img_h, ang)
            raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": w, "angle": ang, "alpha": 1.0})

    elif anim == "tilt_pivot":
        cx, cy = init_cx, init_cy
        anchor = tuple(spec.get("anchor", [0.5, 0.5]))
        ang0 = float(spec.get("ang0", 0.0))
        ang_mid = float(spec.get("ang_mid", ang0))
        ang1 = float(spec.get("ang1", 0.3))
        # Stagger domino wave naturally when multiple dom1..dom4 appear
        t_delay = 0.0
        if sp_name.startswith("dom") and sp_name[-1:].isdigit():
            t_delay = min(0.55, (int(sp_name[-1:]) - 1) * 0.16)
        seq = [(0.0, ang0)]
        if t_delay > 0.05:
            seq.append((t_delay, ang0))
        mid_f = max(t_delay + 0.12, 0.45)
        if mid_f < 0.90:
            seq.append((mid_f, ang_mid if ang_mid != ang0 else (ang0 + ang1) * 0.55))
        seq.append((1.0, ang1))
        for frac, ang in seq:
            x, y = _rotated_xy(cx, cy, w, img_w, img_h, ang, anchor=(anchor[0], anchor[1]))
            raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": w, "angle": ang, "alpha": 1.0})
        init_x, init_y = raw_keys[0]["x"], raw_keys[0]["y"]

    elif anim == "pop_bounce":
        cx, cy = init_cx, init_cy
        if is_actor:
            for frac, mult, a in [(0.0, 0.72, 0.0), (0.14, 1.07, 1.0), (0.28, 1.0, 1.0)]:
                wk = w * mult
                x, y = _rotated_xy(cx, cy, wk, img_w, img_h, 0.0)
                raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": wk, "alpha": a})
            raw_keys.extend(_generate_alive_keyframes(cx, cy, w, img_w, img_h, 0.28, 1.0, span, sz, _lerp_t))
        else:
            for frac, mult, a in [(0.0, 0.72, 0.0), (0.14, 1.07, 1.0), (0.30, 1.0, 1.0), (1.0, 1.02, 1.0)]:
                wk = w * mult
                x, y = _rotated_xy(cx, cy, wk, img_w, img_h, 0.0)
                raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": wk, "alpha": a})
        init_x, init_y = raw_keys[0]["x"], raw_keys[0]["y"]

    elif anim == "slide_in":
        cx0, cy0 = pt(float(spec.get("cx0", 200)), float(spec.get("cy0", 980)))
        cx1, cy1 = pt(float(spec.get("cx1", 640)), float(spec.get("cy1", 980)))
        if is_actor:
            for frac, px, py, a in [
                (0.0, cx0, cy0, 0.0),
                (0.35, cx1 + (cx1 - cx0) * 0.04, cy1, 1.0),
                (0.50, cx1, cy1, 1.0),
            ]:
                x, y = _rotated_xy(px, py, w, img_w, img_h, 0.0)
                raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": w, "alpha": a})
            raw_keys.extend(_generate_alive_keyframes(cx1, cy1, w, img_w, img_h, 0.50, 1.0, span, sz, _lerp_t))
        else:
            for frac, px, py, a in [
                (0.0, cx0, cy0, 0.0),
                (0.45, cx1 + (cx1 - cx0) * 0.04, cy1, 1.0),
                (0.65, cx1, cy1, 1.0),
                (1.0, cx1, cy1 - sz(6.0), 1.0),
            ]:
                x, y = _rotated_xy(px, py, w, img_w, img_h, 0.0)
                raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": w, "alpha": a})
        init_x, init_y = raw_keys[0]["x"], raw_keys[0]["y"]

    elif anim == "sweep":
        pts_v = spec.get("pts") or [[320, 960], [960, 960]]
        pts = [pt(p[0], p[1]) for p in pts_v]
        n = max(2, len(pts))
        is_click = spec.get("sprite") == "cursor"
        is_rocket = spec.get("sprite") == "rocket"
        for idx, (cx, cy) in enumerate(pts):
            frac = idx / float(n - 1)
            ang = (-0.08 + 0.04 * frac) if is_rocket else 0.0
            wk = w * (0.86 if (is_click and idx == n - 1) else 1.0)
            x, y = _rotated_xy(cx, cy, wk, img_w, img_h, ang)
            raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": wk, "angle": ang, "alpha": 1.0 if idx > 0 else 0.75})
        init_x, init_y = raw_keys[0]["x"], raw_keys[0]["y"]

    elif anim == "crossfade":
        cx, cy = init_cx, init_cy
        a0 = float(spec.get("a0", 1.0))
        a1 = float(spec.get("a1", 0.0))
        x0, y0 = _rotated_xy(cx, cy, w, img_w, img_h, 0.0)
        x1, y1 = _rotated_xy(cx, cy, w * 1.03, img_w, img_h, 0.0)
        raw_keys = [
            {"t": _lerp_t(0.0), "x": x0, "y": y0, "w": w, "alpha": a0},
            {"t": _lerp_t(1.0), "x": x1, "y": y1, "w": w * 1.03, "alpha": a1},
        ]

    elif anim == "orbit_burst":
        cx0, cy0 = pt(float(spec.get("cx0", 640)), float(spec.get("cy0", 780)))
        cx1, cy1 = pt(float(spec.get("cx1", 860)), float(spec.get("cy1", 520)))
        for frac, ox_m, oy_m, ang, a in [
            (0.0, cx0, cy0, -0.05, 0.85),
            (0.35, cx0 + sz(14), cy0 - sz(18), 0.06, 1.0),
            (0.68, cx0 - sz(10), cy0 + sz(8), -0.05, 1.0),
            (1.0, cx1, cy1, 0.18, 0.0),
        ]:
            x, y = _rotated_xy(ox_m, oy_m, w, img_w, img_h, ang)
            raw_keys.append({"t": _lerp_t(frac), "x": x, "y": y, "w": w, "angle": ang, "alpha": a})
        init_x, init_y = raw_keys[0]["x"], raw_keys[0]["y"]

    layer: dict[str, Any] = {
        "type": "image",
        "path": rel_path,
        "x": init_x,
        "y": init_y,
        "w": w,
        "keys": _clean_keys(raw_keys, span),
    }
    if from_t > 0.0:
        layer["from"] = from_t
    if to_t is not None and to_t > from_t + 0.05:
        layer["to"] = to_t
    return layer


def _build_layout_layers(
    sc: dict,
    style: str,
    span: float,
    plane_w: float,
    plane_h: float,
    pt,
    sz,
) -> list[dict]:
    """
    Create distinctly styled typographic / divider / B3 vector layers per `layout_mode`
    so shots NEVER repeat a single uniform top-card/bottom-card pattern!
    """
    th = sc.get("theme") or {}
    ink = th.get("ink", "#191916")
    muted = th.get("ink_muted", "#4E5358")
    accent = str(sc.get("accent_color", "#E63946"))
    layout = str(sc.get("layout_mode", "clean_stage"))

    title_txt = _safe_autopilot_text(sc.get("scene_title", "INSIGHT"), max_chars=24)
    sub_txt = _safe_autopilot_text(sc.get("scene_subtitle", ""), max_chars=36)
    stamp_txt = _safe_autopilot_text(sc.get("stamp_word", title_txt), max_chars=20)
    beat_a = _safe_autopilot_text(sc.get("beat_a_label", sub_txt), max_chars=30)
    beat_b = _safe_autopilot_text(sc.get("beat_b_label", stamp_txt), max_chars=30)
    left_tag = _safe_autopilot_text(sc.get("left_tag", "BEFORE"), max_chars=16)
    right_tag = _safe_autopilot_text(sc.get("right_tag", "AFTER"), max_chars=16)

    out: list[dict] = []
    portrait = plane_h >= plane_w
    font_scale = 1.0 if portrait else 0.56

    # Native B3 animated geometric glow ring behind action!
    if style == "B3" and portrait and sc.get("choreography") != "cta_celebration":
        out.append({
            "type": "ellipse",
            "x": 290,
            "y": 540,
            "w": 700,
            "h": 700,
            "fill": "none",
            "stroke": accent,
            "lineWidth": 3,
            "pivotX": 350,
            "pivotY": 350,
            "alpha": 0.22,
            "keys": _clean_keys([
                {"t": 0.0, "scaleX": 0.90, "scaleY": 0.90, "alpha": 0.14},
                {"t": _norm_t(0.5, span), "scaleX": 1.06, "scaleY": 1.06, "alpha": 0.28},
                {"t": _norm_t(1.0, span), "scaleX": 0.96, "scaleY": 0.96, "alpha": 0.18},
            ], span),
        })

    if layout == "clean_stage":
        # Zero top header box! Punchy floating impact stamp arrives on narrative beat
        if sc.get("choreography") != "cta_celebration":
            sx, sy = pt(150, 320)
            t0 = _norm_t(0.18, span)
            t1 = _norm_t(0.42, span)
            bw = sz(980)
            out.append({
                "type": "text",
                "text": stamp_txt,
                "x": sx,
                "y": sy,
                "w": bw,
                "size": _fit_font_size(stamp_txt, max(24, int(64 * font_scale)), bw),
                "bold": True,
                "color": accent,
                "from": t0,
                "keys": _clean_keys([{"t": t0, "alpha": 0, "y": sy + 18}, {"t": t1, "alpha": 1, "y": sy}], span),
            })

    elif layout == "big_typo_banner":
        bx, by = pt(100, 190)
        ux, uy = pt(100, 305)
        t1 = _norm_t(0.32, span)
        t_u0, t_u1 = _norm_t(0.14, span), _norm_t(0.58, span)
        bw = sz(1080)
        out.append({
            "type": "text",
            "text": title_txt,
            "x": bx,
            "y": by,
            "w": bw,
            "size": _fit_font_size(title_txt, max(26, int(74 * font_scale)), bw),
            "bold": True,
            "color": ink,
            "keys": _clean_keys([{"t": 0.0, "alpha": 0, "x": bx - 36}, {"t": t1, "alpha": 1, "x": bx}], span),
        })
        if t_u1 > t_u0 + 0.04:
            out.append({
                "type": "underline",
                "x": ux,
                "y": uy,
                "w": sz(min(820, max(280, len(title_txt) * 34))),
                "color": accent,
                "lineWidth": 8 if portrait else 5,
                "from": t_u0,
                "keys": _clean_keys([{"t": t_u0, "progress": 0}, {"t": t_u1, "progress": 1}], span),
            })

    elif layout == "split_screen":
        lx, ly = pt(105, 295)
        rx, ry = pt(700, 295)
        vx1, vy1 = pt(640, 250)
        vx2, vy2 = pt(640, 440)
        t_m = _norm_t(0.35, span)
        sw = sz(480)
        out.append({
            "type": "text",
            "text": left_tag,
            "x": lx,
            "y": ly,
            "w": sw,
            "size": _fit_font_size(left_tag, max(22, int(48 * font_scale)), sw),
            "bold": True,
            "color": muted,
            "keys": _clean_keys([{"t": 0.0, "alpha": 0}, {"t": t_m, "alpha": 1}], span),
        })
        out.append({
            "type": "line",
            "points": [[vx1, vy1], [vx2, vy2]],
            "color": accent,
            "lineWidth": 6,
            "keys": _clean_keys([{"t": 0.0, "progress": 0}, {"t": t_m, "progress": 1}], span),
        })
        t_r0, t_r1 = _norm_t(0.28, span), _norm_t(0.55, span)
        out.append({
            "type": "text",
            "text": right_tag,
            "x": rx,
            "y": ry,
            "w": sw,
            "size": _fit_font_size(right_tag, max(22, int(50 * font_scale)), sw),
            "bold": True,
            "color": accent,
            "from": t_r0,
            "keys": _clean_keys([{"t": t_r0, "alpha": 0}, {"t": t_r1, "alpha": 1}], span),
        })

    elif layout == "comic_beats":
        # Beat A phrase fades out mid-shot, Beat B insight pops in!
        t_mid = _norm_t(0.48, span)
        ax, ay = pt(120, 255)
        bx, by = pt(120, 255)
        cw = sz(1040)
        if t_mid > 0.28:
            t_in = min(_norm_t(0.14, span), max(0.08, t_mid - 0.18))
            t_hold = max(t_in + 0.04, t_mid - 0.12)
            t_out = max(t_hold + 0.02, t_mid - 0.02)
            out.append({
                "type": "text",
                "text": beat_a,
                "x": ax,
                "y": ay,
                "w": cw,
                "size": _fit_font_size(beat_a, max(22, int(48 * font_scale)), cw),
                "bold": False,
                "color": ink,
                "to": t_mid,
                "keys": _clean_keys(
                    [
                        {"t": 0.0, "alpha": 0.2},
                        {"t": t_in, "alpha": 1.0},
                        {"t": t_hold, "alpha": 1.0},
                        {"t": t_out, "alpha": 0.0},
                    ],
                    span,
                ),
            })
        t_b1 = min(_norm_t(0.72, span), max(t_mid + 0.12, _norm_t(0.68, span)))
        if t_mid < span - 0.25:
            out.append({
                "type": "text",
                "text": beat_b,
                "x": bx,
                "y": by,
                "w": cw,
                "size": _fit_font_size(beat_b, max(24, int(52 * font_scale)), cw),
                "bold": True,
                "color": accent,
                "from": t_mid,
                "keys": _clean_keys([{"t": t_mid, "alpha": 0, "y": by + 18}, {"t": t_b1, "alpha": 1, "y": by}], span),
            })

    elif layout == "floating_callout":
        tx, ty = pt(500, 240)
        ax, ay = pt(210, 325)
        t_e = _norm_t(0.42, span)
        fw = sz(680)
        out.append({
            "type": "text",
            "text": stamp_txt,
            "x": tx,
            "y": ty,
            "w": fw,
            "size": _fit_font_size(stamp_txt, max(22, int(50 * font_scale)), fw),
            "bold": True,
            "color": accent,
            "keys": _clean_keys([{"t": 0.0, "alpha": 0}, {"t": t_e, "alpha": 1}], span),
        })
        t_a1 = _norm_t(0.65, span)
        if t_a1 > 0.1:
            out.append({
                "type": "arrow",
                "x": ax,
                "y": ay,
                "w": sz(250),
                "color": ink,
                "lineWidth": 5,
                "keys": _clean_keys([{"t": 0.05, "progress": 0}, {"t": t_a1, "progress": 1}], span),
            })

    else:  # editorial_spread
        lx1, ly1 = pt(105, 195)
        lx2, ly2 = pt(105, 360)
        tx, ty = pt(135, 195)
        sx, sy = pt(135, 275)
        t1 = _norm_t(0.35, span)
        ew = sz(1020)
        out.append({
            "type": "line",
            "points": [[lx1, ly1], [lx2, ly2]],
            "color": accent,
            "lineWidth": 8,
            "keys": _clean_keys([{"t": 0.0, "progress": 0}, {"t": t1, "progress": 1}], span),
        })
        out.append({
            "type": "text",
            "text": title_txt,
            "x": tx,
            "y": ty,
            "w": ew,
            "size": _fit_font_size(title_txt, max(22, int(52 * font_scale)), ew),
            "bold": True,
            "color": ink,
            "keys": _clean_keys([{"t": 0.0, "alpha": 0}, {"t": t1, "alpha": 1}], span),
        })
        out.append({
            "type": "text",
            "text": sub_txt,
            "x": sx,
            "y": sy,
            "w": ew,
            "size": _fit_font_size(sub_txt, max(18, int(40 * font_scale)), ew),
            "bold": False,
            "color": muted,
            "keys": _clean_keys([{"t": _norm_t(0.12, span), "alpha": 0}, {"t": _norm_t(0.45, span), "alpha": 1}], span),
        })

    return out


def _build_shot_layers(
    sc: dict,
    fallback_png: str,
    bg_paper_rel: str,
    out_dir: Path,
    dur: float,
    plane_w: int,
    plane_h: float,
    style: str,
) -> list[dict]:
    layers: list[dict] = [
        {"type": "image", "path": bg_paper_rel, "x": 0, "y": 0, "w": plane_w}
    ]

    span = max(0.3, dur)
    pt, sz, _ = _stage_mapper(plane_w, plane_h)
    sprites = sc.get("_sprites") or {}
    sprite_plan = sc.get("_sprite_plan") or []
    vector_plan = sc.get("_vector_plan") or []

    # Optional LCM DreamShaper atmospheric scenic backdrop behind sprites
    if "lcm_wash" in sprites:
        lw_meta = sprites["lcm_wash"]
        layers.append({
            "type": "image",
            "path": _make_relative(lw_meta["path"], str(out_dir)),
            "x": 0,
            "y": 0,
            "w": plane_w,
            "h": plane_h,
            "keys": _clean_keys([{"t": 0.0, "alpha": 0.92}, {"t": _norm_t(1.0, span), "alpha": 1.0}], span),
        })

    # Layout-specific kinetic headers/dividers/callouts (6 distinct architectures)
    layers.extend(_build_layout_layers(sc, style, span, plane_w, plane_h, pt, sz))

    # Choreography-specific animated vectors (lines, arrows)
    for vp in vector_plan:
        vf = float(vp.get("from_f", 0.0))
        vt = float(vp.get("to_f", 1.0))
        t_start = _norm_t(vf, span)
        t_end = _norm_t(vt, span)
        if t_end <= t_start + 0.04:
            continue
        kind = vp.get("kind", "line")
        if kind == "line":
            if "p1" in vp and "p2" in vp:
                p1 = pt(vp["p1"][0], vp["p1"][1])
                p2 = pt(vp["p2"][0], vp["p2"][1])
                pts_pair = [[p1[0], p1[1]], [p2[0], p2[1]]]
            else:
                ox, oy = float(vp.get("x", 0)), float(vp.get("y", 0))
                raw_pts = vp.get("points") or [[0, 0], [100, 0]]
                pts_pair = []
                for rp in raw_pts:
                    mp = pt(ox + float(rp[0]), oy + float(rp[1]))
                    pts_pair.append([mp[0], mp[1]])
            layer = {
                "type": "line",
                "points": pts_pair,
                "color": str(vp.get("color", "#191916")),
                "lineWidth": max(2, int(vp.get("lw", 4))),
                "keys": _clean_keys([{"t": t_start, "progress": 0}, {"t": t_end, "progress": 1}], span),
            }
            if t_start > 0.0:
                layer["from"] = t_start
            layers.append(layer)
        elif kind == "ring_pulse" and style == "B3":
            rcx, rcy = pt(float(vp.get("cx", 640)), float(vp.get("cy", 800)))
            rr = sz(float(vp.get("r", 150)))
            layers.append({
                "type": "ellipse",
                "x": round(rcx - rr, 1),
                "y": round(rcy - rr, 1),
                "w": round(rr * 2, 1),
                "h": round(rr * 2, 1),
                "fill": "none",
                "stroke": str(vp.get("color", "#38BDF8")),
                "lineWidth": max(2, int(vp.get("lw", 4))),
                "pivotX": round(rr, 1),
                "pivotY": round(rr, 1),
                "from": t_start,
                "keys": _clean_keys(
                    [
                        {"t": t_start, "scaleX": 0.65, "scaleY": 0.65, "alpha": 0.15},
                        {"t": round((t_start + t_end) * 0.5, 3), "scaleX": 1.05, "scaleY": 1.05, "alpha": 0.85},
                        {"t": t_end, "scaleX": 1.18, "scaleY": 1.18, "alpha": 0.30},
                    ],
                    span,
                ),
            })
        elif kind == "arrow":
            ax, ay = pt(vp.get("x", 450), vp.get("y", 1200))
            layer = {
                "type": "arrow",
                "x": ax,
                "y": ay,
                "w": sz(float(vp.get("w", 340))),
                "color": str(vp.get("color", "#E63946")),
                "lineWidth": max(2, int(vp.get("lw", 5))),
                "keys": _clean_keys([{"t": t_start, "progress": 0}, {"t": t_end, "progress": 1}], span),
            }
            if t_start > 0.0:
                layer["from"] = t_start
            layers.append(layer)

    # Modular independently-animated actor & prop sprites!
    if sprites and sprite_plan:
        for spec in sprite_plan:
            sp_name = spec.get("sprite")
            meta = sprites.get(sp_name)
            if not meta or not Path(meta["path"]).exists():
                continue
            layers.append(_animate_sprite(spec, meta, out_dir, span, pt, sz))
    elif fallback_png:
        rel_png = _make_relative(fallback_png, str(out_dir))
        layers.append({
            "type": "image",
            "path": rel_png,
            "x": 0,
            "y": 0,
            "w": plane_w,
            "keys": _clean_keys([{"t": 0.0, "x": 0, "y": 0, "w": plane_w}, {"t": _norm_t(1.0, span), "x": -20, "y": -25, "w": plane_w + 40}], span),
        })

    return layers


def build_manifest(
    scenes: list[dict],
    scene_png_paths: list[str],
    narration_wav_path: str,
    narration_duration: float,
    music_path: Optional[str],
    output_project_dir: str,
    aspect_ratio: str = "9:16",
    music_gain: float = 0.12,
    contains_sfx: bool = False,
) -> str:
    """Build valid multi-style (B1/B2/B3), multi-sprite choreographed project.json."""
    out_dir = Path(output_project_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    width = 1920 if aspect_ratio == "16:9" else 1080
    height = 1080 if aspect_ratio == "16:9" else 1920
    plane_w = 1280
    plane_h = 1280.0 * height / width

    style = str(scenes[0].get("visual_style", "B1")) if scenes else "B1"
    if style not in ("B1", "B2", "B3"):
        style = "B1"
    th = scenes[0].get("theme") or {}
    is_dark = bool(th.get("is_dark", style == "B3"))
    tint_hex = str(scenes[0].get("bg_wash_tint") or th.get("paper_bg") or ("#111316" if is_dark else "#FAF8F3"))

    bg_mode0 = str(th.get("bg_mode", ""))
    draw_grid0 = (style == "B1") or ("grid" in bg_mode0)
    scenes_dir = out_dir / "assets" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    bg_paper_file = scenes_dir / "bg_paper.png"
    generate_bg_paper(str(bg_paper_file), width=width, height=height, tint_hex=tint_hex, is_dark=is_dark, draw_grid=draw_grid0)
    bg_paper_rel = "assets/scenes/bg_paper.png"
    bg_cache: dict[tuple[str, bool, bool], str] = {(tint_hex, is_dark, draw_grid0): bg_paper_rel}

    has_audio_timings = bool(scenes) and all(sc.get("_audio_start") is not None for sc in scenes)
    if has_audio_timings:
        scene_starts = [round(float(sc["_audio_start"]), 3) for sc in scenes]
        if scene_starts:
            scene_starts[0] = 0.0  # Autopilot engine strictly requires Shot 0 to begin at 0.0
        durations = []
        for i, sc in enumerate(scenes):
            cur_s = scene_starts[i]
            if i + 1 < len(scenes):
                next_s = round(float(scenes[i + 1]["_audio_start"]), 3)
                if next_s <= cur_s:
                    next_s = round(cur_s + max(0.5, float(sc.get("duration", 1.5))), 3)
                d = max(0.4, next_s - cur_s)
            else:
                d = max(0.5, narration_duration - cur_s)
            durations.append(round(d, 3))
    else:
        durations = _distribute_durations(scenes, narration_duration)
        scene_starts = []
        t = 0.0
        for d in durations:
            scene_starts.append(round(t, 3))
            t += d

    shots: list[dict] = []
    current_shot_start = 0.0
    for i, (sc, png, _, dur) in enumerate(zip(scenes, scene_png_paths, scene_starts, durations)):
        shot_start = round(current_shot_start, 3)
        if i == len(scenes) - 1:
            end = round(narration_duration, 3)
            dur = max(0.5, end - shot_start)
        else:
            end = round(shot_start + dur, 3)
        current_shot_start = end

        sc_th = sc.get("theme") or {}
        sc_dark = bool(sc_th.get("is_dark", is_dark))
        sc_tint = str(sc.get("bg_wash_tint") or sc_th.get("paper_bg") or tint_hex)
        sc_grid = (style == "B1") or ("grid" in str(sc_th.get("bg_mode", "")))
        sc_accent = str(sc.get("accent_color") or "#38BDF8")

        shot_bg_name = f"bg_shot_{i + 1:02d}.png"
        shot_bg_path = scenes_dir / shot_bg_name
        generate_shot_procedural_background(
            output_path=str(shot_bg_path),
            scene=sc,
            scene_idx=i,
            width=width,
            height=height,
            tint_hex=sc_tint,
            is_dark=sc_dark,
            draw_grid=sc_grid,
            style=style,
            accent=sc_accent,
            topic=str(sc.get("topic") or ""),
        )
        shot_bg_rel = f"assets/scenes/{shot_bg_name}"

        layers = _build_shot_layers(
            sc=sc,
            fallback_png=png,
            bg_paper_rel=shot_bg_rel,
            out_dir=out_dir,
            dur=dur,
            plane_w=plane_w,
            plane_h=plane_h,
            style=style,
        )
        shots.append({"start": round(shot_start, 3), "end": end, "layers": layers})

    captions = _build_captions(scenes, scene_starts, durations, narration_duration)
    sfx = [] if contains_sfx else _build_sfx(scene_starts, narration_duration)
    voice_rel = _make_relative(narration_wav_path, str(out_dir))

    manifest: dict[str, Any] = {
        "version": 1,
        "style": style,
        "width": width,
        "height": height,
        "fps": 30,
        "captionSize": 34 if style != "B2" else 36,
        "voice": {"path": voice_rel, "lead": 0, "tail": 0, "contains_sfx": bool(contains_sfx)},
        "captions": captions,
        "shots": shots,
        "sfx": sfx,
    }

    if style == "B3":
        # Disable heavy per-frame canvas blur filter so B3 renders smoothly (~15s vs 140s+)
        manifest["television"] = {"enabled": False, "intensity": 0.0}

    if music_path and Path(music_path).exists():
        manifest["music"] = {
            "path": _make_relative(music_path, str(out_dir)),
            "gain": round(max(0.01, min(0.18, float(music_gain))), 2),
        }

    manifest_path = out_dir / "project.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    logger.info(
        "Built %s project.json at %s (%d shots, %d captions)",
        style, manifest_path, len(shots), len(captions)
    )
    return str(manifest_path)
