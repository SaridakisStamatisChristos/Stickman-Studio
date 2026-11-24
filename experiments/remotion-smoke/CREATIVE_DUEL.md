# Creative Duel: original native Remotion treatment

Creative brief: 15 seconds. An isolated service robot searches a deserted nighttime city; a blue signal under the road awakens; the robot reaches toward it; a luminous wave brings the city's windows to life at dawn. Eerie atmosphere, hopeful ending. No narration, just the **identical original PCM soundtrack** used in AetherRendering's separate test. 1280x720, 24fps, 360 frames, H.264/AAC.

Visual direction is independent: one continuous tracking shot, articulated procedural robot, depth-dependent camera parallax, point lights, per-building activation wave, particles, kinetic text, dawn color shift. This is **not** the geometry-parity reproduction.

Run: `npm install && python3 scripts/make_creative_audio.py && npx remotion render src/creative.tsx CreativeDuel out/creative-remotion.mp4 --codec h264 --concurrency 2`.

Benchmark compares engine-specific creative treatments, not identical pictures. Human judgement of storytelling, image coherence and motion is required. Track render time separately from dependency setup.
