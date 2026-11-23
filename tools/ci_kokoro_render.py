"""CPU-only offline Kokoro smoke and narrated CIS integration test.

Models are downloaded once in CI, then synthesis/rendering use local files.
The test distinguishes voice creation from full narrated-video success.
"""
import json
import sys
import traceback
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tts.tts_manager import TTSManager
from engine.cis_pipeline import CISPipeline

OUT = Path("voice-output").resolve()
OUT.mkdir(parents=True, exist_ok=True)
report = {"tts_ok": False, "narrated_video_ok": False, "error": None, "logs": []}
def log(message):
    message = str(message)
    print(message, flush=True)
    report["logs"].append(message)

try:
    tts = TTSManager(models_dir=str(OUT / "models"))
    ready = tts.download_kokoro_models(
        progress_callback=lambda name, pct: print(f"{name}: {pct}%", flush=True)
    )
    if not ready or not tts.is_kokoro_available():
        raise RuntimeError("Kokoro weights could not be downloaded or validated")
    wav = tts.synthesize(
        text="A lonely robot discovered a tiny blue light beneath the silent city.",
        voice_id="af_heart",
        speed=1.0,
        output_path=str(OUT / "kokoro_proof.wav"),
    )
    if not wav or not Path(wav).exists():
        raise RuntimeError("Kokoro failed to synthesize a WAV file")
    with wave.open(wav, "rb") as wf:
        samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32)
        duration = wf.getnframes() / float(wf.getframerate())
    rms = float(np.sqrt(np.mean(samples ** 2)) / 32768.0)
    report.update({"tts_ok": duration > 0.5 and rms > 0.002,
                   "wav_duration_seconds": duration, "wav_rms": rms})
    if not report["tts_ok"]:
        raise RuntimeError(f"Kokoro WAV was missing or silent: duration={duration}, rms={rms}")

    story = (
        "A lonely robot walked through the silent city. "
        "Suddenly, a blue light glowed beneath the old pavement. "
        "It was a message from a child waiting beyond the stars."
    )
    pipeline = CISPipeline(
        llm_manager=None, tts_manager=tts,
        output_dir=str(OUT / "jobs"), temp_dir=str(OUT / "temp")
    )
    mp4 = pipeline.generate_video(
        {
            "topic": "The last signal",
            "script": story,
            "script_mode": "use_as_is",
            "duration": 12,
            "format": "9:16",
            "preview_mode": True,
            "cis_visual_style": "B1",
            "cis_illustration_mode": "pil",
            "sfx_volume": 0.0,
            "music_volume": 0.0,
            "acoustic_mastering": False,
            "voice_id": "af_heart",
        },
        log_callback=log,
    )
    if not mp4 or not Path(mp4).is_file() or Path(mp4).stat().st_size < 1024:
        raise RuntimeError("Kokoro integrated pipeline failed to export an MP4")
    report.update({"narrated_video_ok": True, "film_path": str(mp4),
                   "film_size": Path(mp4).stat().st_size})
except Exception as exc:
    report["error"] = str(exc)
    report["traceback"] = traceback.format_exc()
    print(report["traceback"], file=sys.stderr)
finally:
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
if report["error"]:
    sys.exit(1)
