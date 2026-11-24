# Remotion backend smoke test (isolated)
10 seconds / 1280x720 / 24 fps of procedural stickman robot animation, parallax, title/caption, glowing artifact, and original synthesized soundtrack. This prototype does **not** modify the existing Stickman Studio renderer.

## Run
```sh
npm install
python3 scripts/make_audio.py
npm run compositions
npm run render
ffprobe -v error -show_format -show_streams -of json out/remotion-smoke.mp4
```

A dedicated GitHub Actions workflow generates a video and checks the resolution, audio/video streams, and duration. It publishes MP4 and metrics as artifacts. A comparative 30-second benchmark against Stickman Studio remains a separate task.
