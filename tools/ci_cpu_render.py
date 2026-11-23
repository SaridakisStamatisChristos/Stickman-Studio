"""End-to-end CPU smoke: topic -> native CIS pipeline -> silent MP4.

Voice models are intentionally absent in this stage. Results are not evidence
of functioning Kokoro narration or of audiovisual quality.
"""
import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from engine.cis_pipeline import CISPipeline

OUTPUT = Path(os.environ.get("STICKMAN_SMOKE_OUTPUT", "smoke-output")).resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)
topic = "A lonely robot discovers a signal from a lost civilization"
report = {
    "mode": "real CISPipeline, CPU-only, no TTS model",
    "topic": topic,
    "ffmpeg_path": shutil.which("ffmpeg"),
    "film": None,
    "error": None,
    "logs": [],
}
def log(msg):
    print(str(msg), flush=True)
    report["logs"].append(str(msg))

try:
    pipeline = CISPipeline(
        llm_manager=None, tts_manager=None,
        output_dir=str(OUTPUT / "jobs"), temp_dir=str(OUTPUT / "temporary")
    )
    params = {
        "topic": topic,
        "script_mode": "auto_generate",
        "duration": 5,
        "format": "9:16",
        "preview_mode": True,
        "cis_visual_style": "B1",
        "cis_illustration_mode": "pil",
        "cis_scene_density": "sparse",
        "sfx_volume": 0.0,
        "music_volume": 0.0,
        "acoustic_mastering": False,
    }
    film = pipeline.generate_video(
        params, log_callback=log,
        progress_callback=lambda stage, pct: print(f"{stage}: {pct}%", flush=True),
    )
    report["script"] = pipeline.last_script_used
    if not film or not Path(film).is_file() or Path(film).stat().st_size < 1024:
        raise RuntimeError("CISPipeline did not produce a nonempty MP4")
    report["film"] = str(film)
    report["file_size_bytes"] = Path(film).stat().st_size
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        probe = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "format=duration,size:stream=codec_name,codec_type,width,height",
             "-of", "json", str(film)],
            capture_output=True, text=True, check=True, timeout=30
        )
        report["ffprobe"] = json.loads(probe.stdout)
        streams = report["ffprobe"].get("streams", [])
        if not any(s.get("codec_type") == "video" for s in streams):
            raise RuntimeError("ffprobe found no video stream")
    print("SUCCESS: playable MP4 generated without GUI, GPU, or character uploads")
except Exception as exc:
    report["error"] = str(exc)
    report["traceback"] = traceback.format_exc()
    print(report["traceback"], file=sys.stderr)
finally:
    (OUTPUT / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
if report["error"]:
    sys.exit(1)
