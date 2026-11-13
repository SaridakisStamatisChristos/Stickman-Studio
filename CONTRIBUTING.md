# Contributing to Stickman Studio

Thank you for your interest in contributing to **Stickman Studio**! Whether you are an animator, developer, or content creator, your contributions help make high-quality, 100% offline video production accessible to everyone worldwide.

---

## 🌟 How You Can Help

1. **Add New Stickman Choreographies & Metaphors**:
   - Check `src/animation/stickman.py` and `src/animation/cis_scene_illustrator.py`.
   - Implement new visual actions (e.g., ladder climb, balance scale, chess puzzle, door opening).
2. **Design New Aesthetic Style Packs**:
   - Add new palettes, lighting, and textures into `src/styles/style_packs.py` or `src/styles/cis_auto_styles.py`.
3. **Audio & Voice Improvements**:
   - Integrate new offline neural voice models or SFX synthesis improvements.
4. **Platform Compatibility & Performance**:
   - Optimize ffmpeg streaming pipelines, CPU rendering speed, and multi-threaded rendering.

---

## 🛠️ Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/atharv01h/Stickman-Studio.git
   cd Stickman-Studio
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Studio**:
   ```bash
   python main.py
   ```

---

## 📋 Pull Request Guidelines

- Branch off `main` with a descriptive branch name (e.g. `feature/chess-choreography` or `fix/tts-alignment`).
- Verify your changes by rendering a sample video in both **Moving Stickman** and **Cinematic Illustrated** modes.
- Submit your pull request with a clean description following the PR template.

Thank you for helping build the future of decentralized, offline creative software!

