# Robot Treasure — Kokoro narration

Same 360-frame Remotion composition; only the audio pipeline changes. Default neural voice: af_heart. The script synthesizes locally using Kokoro ONNX INT8, fits each phrase to its scene without truncation, resamples to 48 kHz, ducks music under speech, and writes an isolated narration WAV plus timing report. No eSpeak voice fallback. eSpeak NG is only a phonemization dependency.

Run the workflow for initial model acquisition and render, or install dependencies and model files locally using the workflow instructions. Model files are not committed.
