"""
Stickman Studio - Main Entry Point
==================================
A fully local, offline video generation application.
No cloud services, no paid APIs. Everything runs on your hardware.
Created by Atharv Hatwar. Released under the MIT License.

Requirements: Python 3.11+, PySide6, Pillow, requests
External: FFmpeg (see setup_windows.bat)
"""
import sys
import os
import logging
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))

# Configure logging before any imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("StickmanStudio")


def check_python_version():
    if sys.version_info < (3, 11):
        print("ERROR: Python 3.11 or newer is required.")
        print(f"You have Python {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)


def check_dependencies():
    """Check required Python packages are installed."""
    missing = []
    warnings = []

    # Required
    try:
        import PySide6
    except ImportError:
        missing.append("PySide6 (pip install PySide6)")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow (pip install Pillow)")

    try:
        import requests
    except ImportError:
        missing.append("requests (pip install requests)")

    # Optional but recommended
    try:
        import numpy
    except ImportError:
        warnings.append("numpy not installed - music synthesis will use slower fallback")

    try:
        import torch
        import diffusers
        logger.info("LCM DreamShaper AI Engine: Ready (Diffusion art backgrounds enabled)")
    except ImportError:
        pass

    if missing:
        print("MISSING REQUIRED PACKAGES:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nRun: pip install PySide6 Pillow requests numpy")
        print("Or run setup_windows.bat for full setup.")
        sys.exit(1)

    for w in warnings:
        logger.warning(w)

    return True


def find_ffmpeg() -> str:
    """Find FFmpeg binary."""
    # Check in app directory first
    app_dir = Path(__file__).parent
    local_ffmpeg = app_dir / "ffmpeg" / "ffmpeg.exe"
    if local_ffmpeg.exists():
        return str(local_ffmpeg)

    # Check PATH
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    # Check common locations
    common = [
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path.home() / "ffmpeg" / "bin" / "ffmpeg.exe",
    ]
    for path in common:
        if path.exists():
            return str(path)

    return "ffmpeg"  # Will fail gracefully in encoder


def setup_logging(log_dir: str):
    """Set up file logging."""
    log_path = Path(log_dir) / "stickman_studio.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logging.getLogger().addHandler(file_handler)


def main():
    check_python_version()
    check_dependencies()

    # Import after dependency check
    from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
    from PySide6.QtGui import QPixmap, QColor, QPainter, QFont
    from PySide6.QtCore import Qt, QTimer

    # Initialize Qt app
    app = QApplication(sys.argv)
    app.setApplicationName("Stickman Studio")
    app.setOrganizationName("StickmanStudio")
    app.setApplicationVersion("1.0.0")

    # Show splash screen
    splash_pix = QPixmap(500, 340)
    splash_pix.fill(QColor("#0F1117"))
    painter = QPainter(splash_pix)
    painter.setPen(QColor("#7C3AED"))
    title_font = QFont("Segoe UI", 24, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.drawText(0, 10, 500, 120, Qt.AlignmentFlag.AlignCenter, "🎬 Stickman Studio")
    painter.setPen(QColor("#06B6D4"))
    author_font = QFont("Segoe UI", 12, QFont.Weight.DemiBold)
    painter.setFont(author_font)
    painter.drawText(0, 110, 500, 40, Qt.AlignmentFlag.AlignCenter, "Created by Atharv Hatwar")
    painter.setPen(QColor("#94A3B8"))
    sub_font = QFont("Segoe UI", 10)
    painter.setFont(sub_font)
    painter.drawText(0, 160, 500, 50, Qt.AlignmentFlag.AlignCenter, "Starting up...")
    painter.setPen(QColor("#64748B"))
    small_font = QFont("Segoe UI", 9)
    painter.setFont(small_font)
    painter.drawText(0, 250, 500, 50, Qt.AlignmentFlag.AlignCenter, "100% Local  •  No Cloud  •  No Paid APIs")
    painter.end()

    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    try:
        # Import core modules
        from utils.config_manager import ConfigManager
        from engine.llm_manager import LLMManager
        from engine.scene_planner import ScenePlanner
        from tts.tts_manager import TTSManager
        from audio.music_synth import MusicSynth
        from audio.sfx_synth import SFXSynth
        from audio.mixer import AudioMixer
        from captions.generator import CaptionGenerator
        from captions.renderer import CaptionRenderer
        from animation.scene_composer import SceneComposer
        from video.encoder import VideoEncoder
        from video.pipeline import VideoPipeline
        from ui.main_window import MainWindow

        splash.showMessage("Loading configuration...",
                          Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                          QColor("#4FC3F7"))
        app.processEvents()

        # Initialize config
        config = ConfigManager()
        setup_logging(str(Path(config.app_data_dir) / "logs"))
        logger.info("Stickman Studio starting up")

        # Ensure output directories exist
        Path(config.get_output_dir()).mkdir(parents=True, exist_ok=True)
        Path(config.get_temp_dir()).mkdir(parents=True, exist_ok=True)

        splash.showMessage("Initializing AI engine...",
                          Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                          QColor("#4FC3F7"))
        app.processEvents()

        # Initialize LLM manager
        llm_manager = LLMManager(base_url=config.get("ollama_base_url"))

        # Determine best model
        if config.get("llm_model") == "auto":
            recommended = llm_manager.get_recommended_model()
            logger.info(f"Auto-selected model: {recommended}")
        else:
            recommended = config.get("llm_model")

        llm_manager.default_model = recommended
        llm_manager.context_window = int(config.get("llm_context_window", 2048))
        scene_planner = ScenePlanner(llm_manager)

        splash.showMessage("Initializing TTS engine...",
                          Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                          QColor("#4FC3F7"))
        app.processEvents()

        # Find FFmpeg first so TTS pitch-shifting and video encoding share the binary
        ffmpeg_path = find_ffmpeg()

        # Initialize TTS
        tts_manager = TTSManager(models_dir=config.get_voices_dir(), ffmpeg_path=ffmpeg_path)
        logger.info(f"Using FFmpeg: {ffmpeg_path}")

        splash.showMessage("Building pipeline...",
                          Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                          QColor("#4FC3F7"))
        app.processEvents()

        # Initialize pipeline components
        music_synth = MusicSynth()
        sfx_synth = SFXSynth()
        audio_mixer = AudioMixer(ffmpeg_path=ffmpeg_path)
        caption_gen = CaptionGenerator()
        video_encoder = VideoEncoder(ffmpeg_path=ffmpeg_path)

        # Build main pipeline
        pipeline = VideoPipeline(
            llm_manager=llm_manager,
            tts_manager=tts_manager,
            ffmpeg_path=ffmpeg_path,
            output_dir=config.get_output_dir(),
            temp_dir=config.get_temp_dir(),
        )

        splash.showMessage("Launching interface...",
                          Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                          QColor("#4FC3F7"))
        app.processEvents()

        # Launch main window
        window = MainWindow(
            config_manager=config,
            llm_manager=llm_manager,
            tts_manager=tts_manager,
            pipeline=pipeline,
        )

        # Restore window geometry
        wx = config.get("window_x", -1)
        wy = config.get("window_y", -1)
        ww = config.get("window_width", 1200)
        wh = config.get("window_height", 850)
        window.resize(ww, wh)
        if wx >= 0 and wy >= 0:
            window.move(wx, wy)

        window.show()
        splash.finish(window)

        logger.info("Application started successfully")
        if "--smoke-check" in sys.argv:
            QTimer.singleShot(400, app.quit)
        return app.exec()

    except ImportError as e:
        splash.hide()
        QMessageBox.critical(
            None,
            "Import Error",
            f"Failed to load a required module:\n\n{e}\n\n"
            "Please run setup_windows.bat to install all dependencies."
        )
        logger.error(f"Import error: {e}", exc_info=True)
        return 1

    except Exception as e:
        splash.hide()
        QMessageBox.critical(
            None,
            "Startup Error",
            f"An unexpected error occurred during startup:\n\n{e}\n\n"
            "Check the log file for details."
        )
        logger.error(f"Startup error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

