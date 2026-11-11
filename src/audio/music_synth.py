"""
Music Synthesizer - Generates royalty-free background music locally using synthesis.
No copyrighted content. All generated programmatically.
"""

from __future__ import annotations

import array
import logging
import math
import os
import wave
from typing import Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional numpy import – fall back to stdlib array+math when absent
# ---------------------------------------------------------------------------
try:
    import numpy as np
    _NP = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore
    _NP = False

# Type alias for the audio buffer that works in both paths
AudioBuf = Union["np.ndarray", array.array]  # type: ignore[type-arg]

# ---------------------------------------------------------------------------
# Musical constants (MIDI-style frequencies, Hz)
# ---------------------------------------------------------------------------

def _freq(note: str) -> float:
    """Return the frequency in Hz for a note string like 'C3', 'A#4', 'Eb2'."""
    NOTE_MAP = {
        "C": 0, "C#": 1, "Db": 1,
        "D": 2, "D#": 3, "Eb": 3,
        "E": 4,
        "F": 5, "F#": 6, "Gb": 6,
        "G": 7, "G#": 8, "Ab": 8,
        "A": 9, "A#": 10, "Bb": 10,
        "B": 11,
    }
    for name, semitone in sorted(NOTE_MAP.items(), key=lambda x: -len(x[0])):
        if note.startswith(name):
            octave = int(note[len(name):])
            midi = (octave + 1) * 12 + semitone
            return 440.0 * (2.0 ** ((midi - 69) / 12.0))
    raise ValueError(f"Unknown note: {note!r}")


class MusicSynth:
    """
    Programmatic background-music generator.
    Uses numpy when available; falls back to stdlib array + math.
    """

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate = sample_rate

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_music(self, style: str, duration: float, output_path: str) -> bool:
        """
        Generate background music of *style* lasting *duration* seconds
        and write to *output_path* (WAV).

        Supported styles: "calm", "dark_ambient", "emotional",
                          "tension", "energetic", "none".
        """
        if style == "none" or not style:
            return self.add_silence(duration, output_path)

        generator_map = {
            "calm":         self._generate_calm,
            "dark_ambient": self._generate_dark_ambient,
            "emotional":    self._generate_emotional,
            "tension":      self._generate_tension,
            "energetic":    self._generate_energetic,
            "tribal":       self._generate_tribal,
            "feudal":       self._generate_feudal,
            "lofi":         self._generate_lofi,
            "noir_jazz":    self._generate_noir_jazz,
        }

        generator = generator_map.get(style)
        if generator is None:
            logger.warning("Unknown music style '%s'; defaulting to 'calm'", style)
            generator = self._generate_calm

        try:
            signal = generator(duration)
            signal = self._normalize(signal)
            self._save_wav(signal, output_path)
            return True
        except Exception as exc:
            logger.error("Music generation failed (style=%s): %s", style, exc, exc_info=True)
            return False

    def add_silence(self, duration: float, output_path: str) -> bool:
        """Write a silent WAV file of *duration* seconds."""
        try:
            n = int(self.sample_rate * duration)
            if _NP:
                silence = np.zeros(n, dtype=np.float32)
            else:
                silence = array.array("f", [0.0] * n)
            self._save_wav(silence, output_path)
            return True
        except Exception as exc:
            logger.error("Silence generation failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Style generators
    # ------------------------------------------------------------------

    def _generate_calm(self, duration: float) -> AudioBuf:
        """C major chord tones layered with slow envelope modulation."""
        notes = [_freq("C3"), _freq("E3"), _freq("G3"), _freq("C4")]
        mix = self._zeros(int(self.sample_rate * duration))
        n = self._buf_len(mix)

        for i, f in enumerate(notes):
            amp = 0.18 - i * 0.02
            tone = self._synthesize_tone(f, duration, amplitude=amp, wave_type="sine")
            # Stagger entry slightly for interest
            offset = int(i * 0.4 * self.sample_rate)
            mix = self._mix_at(mix, tone, offset)

        # Reverb simulation: add delayed+attenuated copy
        mix = self._simple_reverb(mix, delay_ms=120, attenuation=0.35)
        mix = self._apply_envelope(mix, attack=0.4, decay=0.2, sustain=0.75, release=0.6)
        return mix

    def _generate_dark_ambient(self, duration: float) -> AudioBuf:
        """Low drones with slow LFO modulation."""
        notes = [_freq("A2"), _freq("E2"), _freq("A2") * 1.005]  # slight detuning
        mix = self._zeros(int(self.sample_rate * duration))

        for i, f in enumerate(notes):
            tone = self._synthesize_tone(f, duration, amplitude=0.22, wave_type="sine")
            # Slow tremolo via LFO
            tone = self._apply_lfo(tone, rate=0.08 + i * 0.03, depth=0.15)
            mix = self._add(mix, tone)

        # Add very low sub tone for weight
        sub = self._synthesize_tone(_freq("A1"), duration, amplitude=0.12, wave_type="sine")
        mix = self._add(mix, sub)
        mix = self._simple_reverb(mix, delay_ms=250, attenuation=0.4)
        mix = self._apply_envelope(mix, attack=0.8, decay=0.3, sustain=0.65, release=1.0)
        return mix

    def _generate_emotional(self, duration: float) -> AudioBuf:
        """Piano-like pentatonic arpeggios."""
        # A minor pentatonic: A3 C4 D4 E4 G4
        pentatonic = [
            _freq("A3"), _freq("C4"), _freq("D4"),
            _freq("E4"), _freq("G4"), _freq("A4"),
        ]
        note_dur = 0.35  # each note lasts 350 ms
        n_total = int(self.sample_rate * duration)
        mix = self._zeros(n_total)

        t = 0.0
        idx = 0
        while t < duration:
            remaining = duration - t
            nd = min(note_dur, remaining)
            f = pentatonic[idx % len(pentatonic)]
            tone = self._synthesize_tone(f, nd, amplitude=0.25, wave_type="sine")
            # Piano-like: fast attack, medium decay, low sustain
            tone = self._apply_envelope(tone, attack=0.01, decay=0.15, sustain=0.3, release=0.1)
            offset = int(t * self.sample_rate)
            mix = self._mix_at(mix, tone, offset)
            t += note_dur * 0.75  # slight overlap
            idx += 1

        mix = self._simple_reverb(mix, delay_ms=80, attenuation=0.25)
        mix = self._apply_envelope(mix, attack=0.3, decay=0.1, sustain=0.8, release=0.5)
        return mix

    def _generate_tension(self, duration: float) -> AudioBuf:
        """Dissonant intervals with a rising pulse."""
        n_total = int(self.sample_rate * duration)
        mix = self._zeros(n_total)

        # Rising tritone swell
        start_f, end_f = 110.0, 220.0  # one octave up
        for step in range(8):
            frac = step / 7.0
            f = start_f * (2.0 ** frac)
            t_start = frac * duration * 0.9
            seg_dur = duration / 8.0 * 1.2
            remaining = duration - t_start
            seg_dur = min(seg_dur, remaining)
            if seg_dur <= 0:
                break
            tone = self._synthesize_tone(f, seg_dur, amplitude=0.18, wave_type="sawtooth")
            tone = self._apply_envelope(tone, attack=0.05, decay=0.2, sustain=0.5, release=0.25)
            offset = int(t_start * self.sample_rate)
            mix = self._mix_at(mix, tone, offset)

        # Pulsing low thud every beat (120 bpm → 0.5 s)
        beat = 0.5
        t = 0.0
        while t < duration:
            remaining = duration - t
            bd = min(0.15, remaining)
            if bd <= 0:
                break
            pulse = self._synthesize_tone(80.0, bd, amplitude=0.3, wave_type="sine")
            pulse = self._apply_envelope(pulse, attack=0.005, decay=0.08, sustain=0.1, release=0.05)
            mix = self._mix_at(mix, pulse, int(t * self.sample_rate))
            t += beat

        mix = self._apply_envelope(mix, attack=0.1, decay=0.05, sustain=0.9, release=0.4)
        return mix

    def _generate_energetic(self, duration: float) -> AudioBuf:
        """Fast pulse in C major with brighter harmonics."""
        # C major: C4 E4 G4 C5
        notes = [_freq("C4"), _freq("E4"), _freq("G4"), _freq("C5")]
        note_dur = 0.2  # 200 ms per note → ~150 bpm 8ths
        n_total = int(self.sample_rate * duration)
        mix = self._zeros(n_total)

        t = 0.0
        idx = 0
        while t < duration:
            remaining = duration - t
            nd = min(note_dur, remaining)
            if nd <= 0:
                break
            f = notes[idx % len(notes)]
            # Square wave for brightness
            tone = self._synthesize_tone(f, nd, amplitude=0.2, wave_type="square")
            tone = self._apply_envelope(tone, attack=0.005, decay=0.05, sustain=0.6, release=0.05)
            # Add harmonic (5th above)
            harm = self._synthesize_tone(f * 1.5, nd, amplitude=0.08, wave_type="sine")
            tone = self._add(tone, harm)
            mix = self._mix_at(mix, tone, int(t * self.sample_rate))
            t += note_dur
            idx += 1

        mix = self._apply_envelope(mix, attack=0.05, decay=0.05, sustain=0.9, release=0.2)
        return mix

    def _generate_tribal(self, duration: float) -> AudioBuf:
        """Earthy rhythmic cave drum pulse + deep primitive wood drone (A3 Cave)."""
        n_total = int(self.sample_rate * duration)
        mix = self._zeros(n_total)
        # Warm cave drone in D2/A2
        for freq, amp in ((_freq("D2"), 0.22), (_freq("A2"), 0.14)):
            drone = self._synthesize_tone(freq, duration, amplitude=amp, wave_type="triangle")
            drone = self._apply_lfo(drone, rate=0.35, depth=0.2)
            mix = self._add(mix, drone)
        # Earthy primitive hand-drum rhythm (heartbeat + syncopation)
        beat = 0.65
        t = 0.0
        step = 0
        while t < duration:
            rem = min(0.22, duration - t)
            if rem <= 0.02:
                break
            f_drum = 82.0 if (step % 4 == 0) else 118.0
            amp_d = 0.34 if (step % 4 == 0) else 0.20
            hit = self._synthesize_tone(f_drum, rem, amplitude=amp_d, wave_type="sine")
            hit = self._apply_envelope(hit, attack=0.004, decay=0.09, sustain=0.05, release=0.08)
            mix = self._mix_at(mix, hit, int(t * self.sample_rate))
            t += (beat * 0.5) if (step % 4 == 2) else beat
            step += 1
        mix = self._simple_reverb(mix, delay_ms=110, attenuation=0.28)
        return self._apply_envelope(mix, attack=0.2, decay=0.1, sustain=0.85, release=0.4)

    def _generate_feudal(self, duration: float) -> AudioBuf:
        """Japanese Hirajoshi pentatonic pluck melody + subtle taiko pulse (A5 Historical)."""
        # Hirajoshi scale in A: A3 B3 C4 E4 F4 A4
        scale = [_freq("A3"), _freq("B3"), _freq("C4"), _freq("E4"), _freq("F4"), _freq("A4")]
        pattern = [0, 3, 2, 1, 4, 3, 5, 3]
        n_total = int(self.sample_rate * duration)
        mix = self._zeros(n_total)

        # Warm bowed low A2 drone
        drone = self._synthesize_tone(_freq("A2"), duration, amplitude=0.14, wave_type="sine")
        mix = self._add(mix, drone)

        note_step = 0.42
        t = 0.0
        idx = 0
        while t < duration:
            nd = min(0.55, duration - t)
            if nd <= 0.05:
                break
            f = scale[pattern[idx % len(pattern)]]
            # Koto-like triangle + bright 2nd harmonic pluck
            pluck = self._synthesize_tone(f, nd, amplitude=0.24, wave_type="triangle")
            over = self._synthesize_tone(f * 2.0, nd, amplitude=0.07, wave_type="sine")
            tone = self._apply_envelope(self._add(pluck, over), attack=0.006, decay=0.18, sustain=0.12, release=0.18)
            mix = self._mix_at(mix, tone, int(t * self.sample_rate))
            if idx % 4 == 0:
                drum_d = min(0.24, duration - t)
                taiko = self._synthesize_tone(72.0, drum_d, amplitude=0.26, wave_type="sine")
                taiko = self._apply_envelope(taiko, attack=0.005, decay=0.10, sustain=0.08, release=0.08)
                mix = self._mix_at(mix, taiko, int(t * self.sample_rate))
            t += note_step
            idx += 1
        mix = self._simple_reverb(mix, delay_ms=140, attenuation=0.32)
        return self._apply_envelope(mix, attack=0.2, decay=0.1, sustain=0.85, release=0.5)

    def _generate_lofi(self, duration: float) -> AudioBuf:
        """Warm cozy cafe Rhodes 7th chords + gentle soft pulse (A4 Cozy Storytelling)."""
        # Warm Cmaj7 -> Am7 progression
        chords = [
            [_freq("C3"), _freq("E3"), _freq("G3"), _freq("B3")],
            [_freq("A2"), _freq("C3"), _freq("E3"), _freq("G3")],
            [_freq("F3"), _freq("A3"), _freq("C4"), _freq("E4")],
            [_freq("G3"), _freq("B3"), _freq("D4"), _freq("F4")],
        ]
        n_total = int(self.sample_rate * duration)
        mix = self._zeros(n_total)
        chord_dur = 2.0
        t = 0.0
        c_idx = 0
        while t < duration:
            cd = min(chord_dur, duration - t)
            if cd <= 0.1:
                break
            for f in chords[c_idx % len(chords)]:
                key = self._synthesize_tone(f, cd, amplitude=0.13, wave_type="sine")
                key = self._apply_envelope(key, attack=0.05, decay=0.25, sustain=0.65, release=0.35)
                mix = self._mix_at(mix, key, int(t * self.sample_rate))
            t += chord_dur
            c_idx += 1
        mix = self._simple_reverb(mix, delay_ms=125, attenuation=0.30)
        return self._apply_envelope(mix, attack=0.3, decay=0.1, sustain=0.85, release=0.5)

    def _generate_noir_jazz(self, duration: float) -> AudioBuf:
        """Moody twilight Dm7 walking bass + velvet electric piano chords (A6 Amber Noir)."""
        bass_notes = [_freq("D2"), _freq("F2"), _freq("A2"), _freq("G2"), _freq("C2"), _freq("E2"), _freq("G2"), _freq("A1")]
        chords = [
            [_freq("D3"), _freq("F3"), _freq("A3"), _freq("C4")],
            [_freq("G3"), _freq("Bb3"), _freq("D4"), _freq("F4")],
        ]
        n_total = int(self.sample_rate * duration)
        mix = self._zeros(n_total)

        step = 0.55
        t = 0.0
        idx = 0
        while t < duration:
            nd = min(0.48, duration - t)
            if nd <= 0.05:
                break
            fb = bass_notes[idx % len(bass_notes)]
            b = self._synthesize_tone(fb, nd, amplitude=0.26, wave_type="sine")
            b = self._apply_envelope(b, attack=0.01, decay=0.14, sustain=0.35, release=0.12)
            mix = self._mix_at(mix, b, int(t * self.sample_rate))
            if idx % 4 == 0:
                cd = min(2.0, duration - t)
                for fc in chords[(idx // 4) % len(chords)]:
                    p = self._synthesize_tone(fc, cd, amplitude=0.11, wave_type="sine")
                    p = self._apply_envelope(p, attack=0.06, decay=0.30, sustain=0.45, release=0.40)
                    mix = self._mix_at(mix, p, int(t * self.sample_rate))
            t += step
            idx += 1
        mix = self._simple_reverb(mix, delay_ms=160, attenuation=0.35)
        return self._apply_envelope(mix, attack=0.35, decay=0.1, sustain=0.8, release=0.6)

    # ------------------------------------------------------------------
    # Core DSP primitives
    # ------------------------------------------------------------------

    def _synthesize_tone(
        self,
        freq: float,
        duration: float,
        amplitude: float = 0.3,
        wave_type: str = "sine",
    ) -> AudioBuf:
        """Generate a single tone of *duration* seconds at *freq* Hz."""
        n = int(self.sample_rate * duration)
        sr = self.sample_rate

        if _NP:
            t = np.linspace(0.0, duration, n, endpoint=False, dtype=np.float32)
            phase = 2.0 * np.pi * freq * t
            if wave_type == "sine":
                sig = amplitude * np.sin(phase)
            elif wave_type == "square":
                sig = amplitude * np.sign(np.sin(phase)).astype(np.float32)
            elif wave_type == "triangle":
                sig = amplitude * (2.0 / math.pi * np.arcsin(np.sin(phase))).astype(np.float32)
            elif wave_type == "sawtooth":
                sig = amplitude * (2.0 * (freq * t - np.floor(freq * t + 0.5))).astype(np.float32)
            else:
                sig = amplitude * np.sin(phase)
            return sig

        # --- Pure-Python fallback ---
        buf = array.array("f", [0.0] * n)
        inv_sr = 1.0 / sr
        two_pi_f = 2.0 * math.pi * freq
        for i in range(n):
            tt = i * inv_sr
            phase = two_pi_f * tt
            if wave_type == "sine":
                v = amplitude * math.sin(phase)
            elif wave_type == "square":
                v = amplitude * (1.0 if math.sin(phase) >= 0 else -1.0)
            elif wave_type == "triangle":
                v = amplitude * (2.0 / math.pi * math.asin(math.sin(phase)))
            elif wave_type == "sawtooth":
                v = amplitude * (2.0 * (freq * tt - math.floor(freq * tt + 0.5)))
            else:
                v = amplitude * math.sin(phase)
            buf[i] = v
        return buf

    def _apply_envelope(
        self,
        signal: AudioBuf,
        attack: float = 0.1,
        decay: float = 0.1,
        sustain: float = 0.7,
        release: float = 0.3,
    ) -> AudioBuf:
        """Apply an ADSR envelope to *signal*."""
        n = self._buf_len(signal)
        sr = self.sample_rate

        a_samps = max(1, int(attack * sr))
        d_samps = max(1, int(decay * sr))
        r_samps = max(1, int(release * sr))
        # Clamp so they don't exceed total length
        total_ad = a_samps + d_samps
        if total_ad + r_samps > n:
            scale = n / max(1, total_ad + r_samps)
            a_samps = max(1, int(a_samps * scale))
            d_samps = max(1, int(d_samps * scale))
            r_samps = max(1, int(r_samps * scale))
        s_samps = max(0, n - a_samps - d_samps - r_samps)

        if _NP:
            env = np.zeros(n, dtype=np.float32)
            # Attack
            env[:a_samps] = np.linspace(0.0, 1.0, a_samps, dtype=np.float32)
            # Decay
            end_d = a_samps + d_samps
            env[a_samps:end_d] = np.linspace(1.0, sustain, d_samps, dtype=np.float32)
            # Sustain
            end_s = end_d + s_samps
            env[end_d:end_s] = sustain
            # Release
            env[end_s:end_s + r_samps] = np.linspace(sustain, 0.0, r_samps, dtype=np.float32)
            return (np.asarray(signal, dtype=np.float32) * env).astype(np.float32)

        # Pure Python
        env = array.array("f", [0.0] * n)
        for i in range(a_samps):
            env[i] = i / a_samps
        for i in range(d_samps):
            env[a_samps + i] = 1.0 - (i / d_samps) * (1.0 - sustain)
        end_d = a_samps + d_samps
        for i in range(s_samps):
            env[end_d + i] = sustain
        end_s = end_d + s_samps
        for i in range(r_samps):
            if end_s + i < n:
                env[end_s + i] = sustain * (1.0 - i / r_samps)
        out = array.array("f", [signal[i] * env[i] for i in range(n)])
        return out

    def _apply_lfo(
        self,
        signal: AudioBuf,
        rate: float = 0.5,
        depth: float = 0.3,
    ) -> AudioBuf:
        """Apply a slow sinusoidal LFO (tremolo) to *signal*."""
        n = self._buf_len(signal)
        if _NP:
            t = np.linspace(0.0, n / self.sample_rate, n, endpoint=False, dtype=np.float32)
            lfo = 1.0 - depth + depth * np.sin(2.0 * math.pi * rate * t)
            return (np.asarray(signal, dtype=np.float32) * lfo).astype(np.float32)

        out = array.array("f", [0.0] * n)
        inv_sr = 1.0 / self.sample_rate
        two_pi_rate = 2.0 * math.pi * rate
        for i in range(n):
            lfo = 1.0 - depth + depth * math.sin(two_pi_rate * i * inv_sr)
            out[i] = signal[i] * lfo
        return out

    def _simple_reverb(
        self,
        signal: AudioBuf,
        delay_ms: float = 120.0,
        attenuation: float = 0.3,
    ) -> AudioBuf:
        """Very simple comb-filter reverb (single delay line)."""
        delay_samps = int(delay_ms * 0.001 * self.sample_rate)
        n = self._buf_len(signal)

        if _NP:
            sig = np.asarray(signal, dtype=np.float32)
            echo = np.zeros(n, dtype=np.float32)
            echo[delay_samps:] = sig[:n - delay_samps] * attenuation
            return np.clip(sig + echo, -1.0, 1.0)

        out = array.array("f", list(signal))
        for i in range(delay_samps, n):
            v = out[i] + signal[i - delay_samps] * attenuation
            out[i] = max(-1.0, min(1.0, v))
        return out

    def _normalize(self, signal: AudioBuf) -> AudioBuf:
        """Normalize *signal* to peak amplitude of ~0.9 to prevent clipping."""
        if _NP:
            sig = np.asarray(signal, dtype=np.float32)
            peak = np.max(np.abs(sig))
            if peak > 1e-6:
                sig = sig / peak * 0.9
            return sig

        peak = max(abs(v) for v in signal) if signal else 0.0
        if peak > 1e-6:
            factor = 0.9 / peak
            out = array.array("f", [v * factor for v in signal])
            return out
        return signal

    # ------------------------------------------------------------------
    # Buffer helpers (unified numpy / stdlib path)
    # ------------------------------------------------------------------

    def _zeros(self, n: int) -> AudioBuf:
        if _NP:
            return np.zeros(n, dtype=np.float32)
        return array.array("f", [0.0] * n)

    def _buf_len(self, buf: AudioBuf) -> int:
        if _NP and isinstance(buf, np.ndarray):
            return len(buf)
        return len(buf)

    def _add(self, a: AudioBuf, b: AudioBuf) -> AudioBuf:
        """Element-wise add two buffers, truncating to shorter length."""
        n = min(self._buf_len(a), self._buf_len(b))
        if _NP:
            return (np.asarray(a, dtype=np.float32)[:n] + np.asarray(b, dtype=np.float32)[:n]).astype(np.float32)
        out = array.array("f", [0.0] * n)
        for i in range(n):
            out[i] = a[i] + b[i]
        return out

    def _mix_at(self, dest: AudioBuf, src: AudioBuf, offset: int) -> AudioBuf:
        """Add *src* into *dest* starting at *offset* samples."""
        d_len = self._buf_len(dest)
        s_len = self._buf_len(src)
        end = min(offset + s_len, d_len)
        if end <= offset:
            return dest

        if _NP:
            dest_np = np.asarray(dest, dtype=np.float32)
            src_np = np.asarray(src, dtype=np.float32)
            dest_np[offset:end] += src_np[: end - offset]
            return dest_np

        for i in range(end - offset):
            dest[offset + i] = dest[offset + i] + src[i]
        return dest

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def _save_wav(self, signal: AudioBuf, path: str) -> None:
        """Save *signal* (float32 in [-1, 1]) as a 16-bit mono WAV file."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        if _NP:
            pcm_data = (np.asarray(signal, dtype=np.float32) * 32767).astype(np.int16).tobytes()
        else:
            import struct
            pcm_parts = []
            for v in signal:
                s = max(-32768, min(32767, int(v * 32767)))
                pcm_parts.append(struct.pack("<h", s))
            pcm_data = b"".join(pcm_parts)

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_data)
