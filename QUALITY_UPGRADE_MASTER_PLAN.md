# Stickman Studio — Quality Upgrade Directive (Experimental)

**Status:** Proposed; not implemented or merged.  
**Baseline:** Real Ubuntu CPU tests, branch `test/cpu-e2e-smoke`, and inspected output from 2026-11-23.  
**Goal:** Higher-quality *actual animation* and reliable topic-to-video generation, offline-first, CPU-capable, without pre-drawn assets.

## Verified baseline and observed failure modes

1. The original Cinematic Illustrated Stickman (CIS) pipeline creates a voice file, procedural PNG illustrations, separate sprite files, and a `project.json` manifest with per-layer keyframes.
2. The project's `src/engine/cis_pipeline.py` references Node `scripts/autopilot.mjs`, but that file is not in the forked upstream tree. On CPU GitHub Actions, the fallback uses finished scene PNGs plus Ken Burns transforms and does *not* execute manifest layer keyframes. This produces camera motion rather than acting and choreography.
3. Topic-only input `A lonely robot discovers a signal from a lost civilization` produced computer-programming tips, even though the expected output was fiction. `InbuiltAIDirector` has domain-specific template catalogs but no general fiction narrative model.
4. CPU video and Kokoro-with-voice end-to-end smoke tests now pass after fixing false NVENC selection (checking actual encoder initialization rather than advertised codec support). This does not demonstrate cinematic visual quality.
5. The initial native-manifest renderer prototype demonstrates sprite- and text-layer transitions; it remains an experiment and does not yet match the original scene layout and captions. Rigged body motion is still absent.

## Quality acceptance criteria

- **Story fidelity:** For three precommitted unrelated requests (science explanation, emotional fiction, and historical/philosophical narrative), narration must pursue the specific premise; no template-domain leakage or unrelated advice. Include adversarial examples like `robot` (character vs robotics lesson).
- **Independent animation:** At least one major character performs visibly changing body poses, and at least two non-camera objects/layers move during each action scene. Tests must distinguish local actor motion from global camera-only changes.
- **Continuity:** Stable character palette, head/body geometry, and scene landmarks through all shots where the actor recurs.
- **Composition:** Subject occupies an intentional readable region; title and caption safe zones; no clipping, overlap, or empty 35%-of-frame dead zone unless artistically intended.
- **Audio:** Non-silent offline Kokoro voice; audible, mixed sound effects where appropriate; no clipped peaks; synchronized scene-to-narration timings.
- **Operational:** 30-second portrait CPU-only MP4 without GUI, GPU, Internet after model provisioning; memory peak, rendering throughput, and output metrics recorded. Never claim 0-ms AV drift based only on a successful export.
- **Regression:** Deterministic seeds for benchmark cases; preserve sample MP4, frame contact sheet, metadata, SHA, and CI logs. Compare reference outputs visually and numerically. CPU/GPU paths verified separately.

## Implementation phases (strict order)

### Q0 — Source correctness and narrative contract
- Add explicit `content_mode`: `fiction`, `explanation`, `motivation`, `dialogue`, `auto`.
- Separate **topic classification** from **script production**. Never assume `robot` implies software engineering, or fabricate factual claims.
- Require an internally structured plan before narration: topic/premise, characters, setting, narrative/argument arc, 4–8 beats, emotional change, ending, per-beat visual brief, visual consistency anchors.
- If an optional *local* LLM is available via Ollama, use it to generate structured beats with schema validation. Offline deterministic fallback remains but must be domain-appropriate, with honest limits for arbitrary fiction.
- Add regression tests that *fail* when fiction is transformed into coding/business advice.

### Q1 — Real layer rendering on CPU (highest visual ROI)
- Implement `src/video/native_manifest_renderer.py` to render `project.json` shot layers, rather than flattening to `sceneNN.png`. Read image/text/line/arrow/underline layers, honor `from`, `keys`, alpha, position, scale and rotation with deterministic interpolation.
- Reuse generated sprite PNGs and shot background PNGs with a bounded resize/cache strategy. Composite at 24–30 fps, output H.264 + AAC using FFmpeg stdin streaming, `libx264` fallback.
- Preserve manifest typography and captions. Ensure scene duration follows the **final audio timeline**. Make the fallback informative on errors instead of redirecting FFmpeg stderr to DEVNULL.
- Keep the old Ken Burns renderer behind a safe compatibility switch until comparable acceptance passes.
- Unit tests: interpolation endpoints, visibility, geometry, absent asset handling, constant memory bound, audio output, and temporal continuity.
- Visual evaluation: contact-sheet and optical-difference tests focusing on the *actor*, not only camera movement.

### Q2 — Articulated stickman acting
- Use a hierarchical 2D rig: pelvis/torso/head, shoulders/elbows/wrists, hips/knees/ankles, facing direction, foot contacts.
- Add pose states and transitions: idle/breathing, look, point, reach, pick up, walk, run, surprise, recoil, celebrate; stance and arm-gaze constraints.
- Use analytical 2-bone IK or FABRIK for hand/foot targets; ensure foot planting and no limb pop or frame-to-frame coordinate jumps.
- Maintain actor identity via a character sheet/seed/config across scenes. Reuse face shape, apparel palette and limb proportions. Add per-character pose tests.

### Q3 — Art direction and cinematography
- Compose a coherent 3-shot palette rather than rotating unrelated backgrounds. Choose one visual grammar per clip.
- Improve narrative props and background assets; separate front/mid/back planes for limited parallax. Do not hide unsupported objects behind a text-labeled generic emblem.
- Add 3–6 shot architectures, clear focal subject, deliberate framing, readable typography. Prefer 720p/1080p 24 fps polished motion over 4K still slides.
- Captions: one or two short lines, high contrast, safe margins, per-word highlights only when aligned; avoid collisions with scene labels.

### Q4 — Sound and pacing
- Keep Kokoro ONNX local; match pauses and emphasis to action beats, not just text quantity.
- Synchronize prop SFX (footfall, UI taps, signal beeps) to actual timeline events, mix background audio underneath voice, normalize and limit peaks.
- Add automated audio-probe and no-silent-WAV acceptance checks; render a voice+effects sample for inspection.

## Scientific comparison

Precommit and preserve three 20–30 second test topics and two prompts per category. Export every phase with the same seed and duration; compare script-topic fidelity, actor-motion isolation, visual continuity, caption readability, narrative arc, clipping, FPS, throughput and RAM. Do not label a pipeline SOTA merely because CI passes.

## Recommended next implementation
Implement Q0 script fidelity + Q1 native layered rendering on this experimental branch; run baseline/after videos with the same prompts. Only then consider Q2 rigs and larger models. Keep `main` unchanged pending explicit acceptance.
