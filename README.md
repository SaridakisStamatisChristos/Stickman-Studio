<p align="center">
  <img src="docs/images/banner.png" alt="Stickman Studio Banner" width="100%">
</p>

<p align="center">
  <a href="https://github.com/atharv01h"><img src="https://img.shields.io/badge/Creator-Atharv%20Hatwar-8A2BE2.svg?style=for-the-badge&logo=github" alt="Creator: Atharv Hatwar"></a>
  <a href="https://github.com/atharv01h/Stickman-Studio"><img src="https://img.shields.io/badge/Repository-Stickman--Studio-0078D6.svg?style=for-the-badge&logo=github" alt="Repository: Stickman-Studio"></a>
  <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="License: MIT">
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10 / 11">
  <img src="https://img.shields.io/badge/Privacy-100%25%20Offline-success.svg?style=for-the-badge" alt="100% Offline">
  <img src="https://img.shields.io/badge/Hardware-4GB%20VRAM%20%7C%208GB%20RAM-orange.svg?style=for-the-badge&logo=nvidia" alt="GTX 1650 Ready">
</p>

---

# 🎬 Stickman Studio

> **Designed and Engineered by [Atharv Hatwar](https://github.com/atharv01h)**  
> An autonomous, 100% local, offline AI video production suite for Windows. Turn any topic or script into a fully animated, professionally narrated, kinetic stickman reel or film in minutes — with zero paid cloud APIs, zero subscriptions, and 100% local privacy.

---

## 🌟 Overview

**Stickman Studio** brings studio-grade animated video production straight to consumer hardware. Built specifically to run smoothly on standard laptops and desktops (such as an AMD Ryzen 5 with an NVIDIA GTX 1650 and 8 GB RAM — or CPU-only systems), it combines **two complete animation modes** (`Moving Stickman` & `Cinematic Illustrated Stickman`), a script-aware AI Director, procedural vector & diffusion backgrounds, offline Kokoro ONNX neural voice acting, procedural sound design, and FFmpeg encoding inside a fast dark **Obsidian-Studio** desktop app.

<p align="center">
  <img src="docs/images/sample_scene.png" alt="Sample Scene Render" width="90%">
</p>

---

## ✨ Key Highlights

- 🔒 **100% Free, Local & Offline**: Zero cloud reliance and zero paid APIs. Uses local Kokoro ONNX / Windows SAPI TTS, local procedural vector graphics, optional local Ollama models, and optional local `SimianLuo/LCM_Dreamshaper_v7` diffusion.
- 🎬 **Dual Production Modes**:
  - **Mode 1 — Moving Stickman Studio**: Kinetic joint-animated stickmen with 3-phase acting kinematics, blinking, eye-tracking, dynamic props, camera moves, and **16 Visual Style Options** led by the flagship **`AUTO • AI Script Studio (Best)`** synthesizer.
  - **Mode 2 — Cinematic Illustrated Stickman (CIS)**: Full-screen animated illustration reels built for psychology, storytelling, self-improvement, and relationship scripts across **20 script-matched choreographies**, **6 dynamic layout architectures**, and **per-shot mixed canvas themes (`AUTO_MIX`, `B1`, `B2`, `B3`)**.
- ✨ **Flagship `AUTO` Style Synthesizer**:
  - Dynamically mixes existing style packs per scene **and** synthesizes bespoke hybrid color palettes, lighting, and camera rhythms (such as *Obsidian Amber Chalk*, *Warm Kraft Editorial*, *Midnight Blueprint Neon*, *Sage Minimalist Ink*, and *Velvet Violet Noir*) matched directly to your script's meaning and emotional beat.
- 🧠 **True Script-to-Visual Precision (20 Choreographies + 12 Semantic Props)**:
  - Recognizes real story motifs (`give_and_withdraw`, `boundary_shield`, `tether_break`, `mind_storm_calm`, `idea_spark_build`, `two_path_fork`, `mirror_truth`, `domino_chain`, `iceberg_depth`, `rocket_breakthrough`, `spotlight_reveal`, etc.) and draws matching semantic props (`heart`, `shield`, `coin`, `book`, `clock`, `lightning`, `brain`, `key`, `crown`, `phone`, `spark`) so reels never repeat the same template.
- 🎨 **Dual Background Engine (`Procedural Vector AI` & `LCM DreamShaper`)**:
  - Works seamlessly across **both Mode 1 and CIS Mode 2** (with synchronized UI selectors): choose instant zero-GPU procedural backdrops or local 4-step `LCM_Dreamshaper_v7` diffusion scenic backdrops (`9:16`, `16:9`, `1:1`).
- 🎚️ **Smart Auto Voice Speed & Optional Ending Follow/CTA Screen**:
  - Automatically calibrates narration speaking pace (`compute_auto_voice_speed` + measured refinement) to match script length and video duration, and optionally generates a custom animated ending **Follow / Subscribe CTA screen** with bespoke closing voiceover (`"Follow this page"`, `"Follow me"`, `"Save & Follow"`, or custom text).
- ⚡ **Fast, Non-Blocking Obsidian-Studio UI**:
  - Asynchronous style thumbnail rendering (`QThread`), off-thread Ollama status probing, debounced script metrics, and clean batched list updates keep startup under 1 second with smooth navigation.
- 🔊 **Built-In Sound Design & Fullscreen Encoding**:
  - Procedural DSP ambient scores and SFX (`pop`, `whoosh`, `impact`, `success`) with sidechain ducking, full-screen `9:16` / `16:9` / `1:1` output, and hardware NVENC or x264 H.264 export.

---

## 🎭 Dual Generation Modes

### Mode 1: Moving Stickman (`SceneComposer`)
- Full procedural 2x supersampled stickman acting, prop handoffs, facial expressions, blinking, and camera choreography (`PUNCH_IN`, `SLOW_ZOOM_IN`, `PAN_RIGHT`, `WIDE`).
- Interactive **16-Card Visual Style Gallery** (`auto` hero card + `s1`–`s15` style packs).

### Mode 2: Cinematic Illustrated Stickman (`CISPipeline`)
- Storyboarded specifically around script clauses (`balanced`, `detailed`, or `compact` pacing) into:
  - **20 Distinct Choreographies**: `give_and_withdraw`, `boundary_shield`, `tether_break`, `mind_storm_calm`, `idea_spark_build`, `two_path_fork`, `question_burst`, `balance_scale`, `spotlight_reveal`, `split_myth_reality`, `rocket_breakthrough`, `crowd_filter`, `loop_escape`, `iceberg_depth`, `domino_chain`, `bridge_cross`, `magnet_orbit`, `clock_sprint`, `stair_climb`, `cta_celebration`.
  - **6 Layout Architectures**: `clean_stage`, `big_typo_banner`, `split_screen`, `comic_beats`, `floating_callout`, `editorial_spread`.
  - **Visual Canvas Options**: `auto` (`AUTO_MIX` — alternates warm craft paper, sage paper, blueprint grid, dark obsidian neon, and charcoal themes per beat), `B1` (Whiteboard Grid Paper), `B2` (Tinted Card Editorial), and `B3` (Dark Chalkboard Neon).
  - **Illustration / Background Engines**: `Hand-Drawn B1 (Procedural Vector AI)` or `Local Diffusion (LCM DreamShaper)`.
  - **Custom Ending CTA Screen**: Optional interactive `+ FOLLOW` / `+ SUBSCRIBE` / `BOOKMARK & FOLLOW` closing card with animated cursor tap, bell ring, and custom spoken audio.

---

## 🎨 Visual Style Showcase (Mode 1)

Stickman Studio includes **16 Style Selections** (`auto` AI Script Studio + 15 handcrafted style packs `S1`–`S15`):

<p align="center">
  <img src="docs/images/styles_grid.png" alt="Styles Showcase Grid" width="90%">
</p>

| ID | Style Name | Description |
|---|---|---|
| `auto` | **AUTO • AI Script Studio (Best)** *(Default)* | Mixes styles per beat AND synthesizes custom hybrid palettes & lighting tuned to the script |
| `s1_rsa_whiteboard` | **S1 RSA Whiteboard Explainer** | Crisp cream paper canvas, blueprint ink, dry-erase sketch lines |
| `s2_cyberpunk_neon` | **S2 Cyberpunk Neon Terminal** | Dark futuristic slate with glowing neon cyan & magenta rim lighting |
| `s3_retro_pop_comic` | **S3 Pop Art & Retro Comic** | Halftone comic panels, bold dynamic outlines, saturated accents |
| `s4_notion_startup` | **S4 Notion & Tech Minimalist** | Clean editorial startup aesthetic with structured pastel cards |
| `s5_dark_gold_wealth` | **S5 Luxury Gold & Finance** | Obsidian-black canvas with metallic gold geometric accents |
| `s6_chalkboard_academy` | **S6 Academic Chalkboard Lecture** | Classic green slate board with textured chalk strokes & dust |
| `s7_ghibli_watercolor` | **S7 Cozy Ghibli Storybook** | Warm illustrated pastoral gradients and soft ambient lighting |
| `s8_shonen_manga` | **S8 Shonen Manga Action** | High-contrast monochrome ink, speed lines, dramatic impact frames |
| `s9_retro_arcade` | **S9 8-Bit Retro Arcade CRT** | Pixel grid backdrop with retro arcade palette & subtle scanlines |
| `s10_blueprint_cad` | **S10 Blueprint CAD Engineering** | Technical drafting grid, cyan schematic callouts, crisp geometry |
| `s11_graffiti_punk` | **S11 Urban Street Art & Graffiti** | Energetic spray-paint stencil highlights on dark urban backdrop |
| `s12_cinematic_noir` | **S12 1940s Detective Film Noir** | Moody high-contrast shadows, Venetian blind light beams, amber noir |
| `s13_cinematic_storyteller` | **S13 Cinematic Storyteller** | 2.5D narrative staging with floor reflections & golden hour glow |
| `s14_chameleon_adaptive` | **S14 Chameleon Dynamic** | Adaptive scene-by-scene selection across classic packs by mood |
| `s15_minimalist_accent` | **S15 Minimalist Ink & Accent** | High-impact distraction-free ink & single bold accent storytelling |

---

## 🏛️ System Architecture

```
                                      STICKMAN STUDIO
                                 Engineered by Atharv Hatwar
                                               │
            ┌──────────────────────────────────┴──────────────────────────────────┐
            ▼                                                                     ▼
   [ Moving Stickman Mode ]                                        [ Cinematic Illustrated Mode ]
 • Style Synthesizer (`auto`, S1–S15)                            • Semantic Storyboarder (20 Choreos)
 • 3-Phase Joint Kinematics                                      • Multi-Sprite & Prop Animator
 • Procedural Rooms & LCM Diffusion                              • AUTO_MIX / B1 / B2 / B3 + LCM Diffusion
            │                                                                     │
            └──────────────────────────────────┬──────────────────────────────────┘
                                               ▼
                                  [ Audio & Voice Pipeline ]
                        • Kokoro ONNX Neural TTS + Windows SAPI Fallback
                        • Smart Auto Voice Speed Calibration
                        • Procedural DSP Music & SFX + Sidechain Ducking
                                               │
                                               ▼
                                 [ Rendering & Export Engine ]
                       • Native Autopilot / Canvas Compositor & FFmpeg H.264
                       • Optional Animated Ending Follow / CTA Card
                                               │
                                               ▼
                                    🎬 Fullscreen 1080p MP4
```

---

## 💻 Hardware Requirements

Designed specifically to operate efficiently within tight hardware envelopes:

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Operating System** | Windows 10 (64-bit) | Windows 11 (64-bit) |
| **Processor** | Intel Core i5 / AMD Ryzen 3 | AMD Ryzen 5 4600H / Intel Core i7 |
| **System RAM** | 8 GB RAM | 8 GB – 16 GB RAM |
| **Graphics Card** | Intel UHD Graphics (CPU Mode) | NVIDIA GTX 1650 (4 GB VRAM) or higher |
| **Python** | Python 3.11+ | Python 3.11 or 3.12 (for CUDA PyTorch wheels) |
| **Disk Space** | 4 GB free space | 8 GB free space (for models & videos) |

---

## 🚀 Quick Start Guide

### 1. Clone the Repository

```bash
git clone https://github.com/atharv01h/Stickman-Studio.git
cd Stickman-Studio
```

### 2. One-Click Setup (Run Once with Internet)

Run the automated installer script to download the local dependencies:

```batch
setup_windows.bat
```

This script will automatically configure:
- Essential Python packages (`PySide6`, `Pillow`, `numpy`, `soundfile`, `requests`)
- FFmpeg video encoding binary
- Embedded In-Process AI Director (Native Python, zero external daemons required)
- Kokoro ONNX offline neural TTS model

> **Note**: Once setup finishes and optional local models (`Kokoro`, `LCM_Dreamshaper_v7`) are cached, you can completely disconnect your internet connection. Everything runs 100% offline.

### 3. Launch the Studio

Double-click `run.bat` or run:

```bash
python main.py
```

### 4. Diagnostic Health Check

Verify your system's offline components, GPU acceleration status, and libraries at any time:

```batch
health_check.bat
```

---

## 🎬 How to Generate Your First Video

1. **Launch**: Open the application via `run.bat` or `python main.py`.
2. **Choose Mode**: Pick **Moving Stickman** or **✦ Cinematic Illustrated** at the top of the studio panel.
3. **Input Topic & Script**: Type your topic and paste your script (or choose AI auto-generate / improve).
4. **Pick Visual Style & Background AI**:
   - Leave **Animation Style** on **`AUTO • AI Script Studio (Best)`** (or pick any custom style card / `B1`–`B3` canvas in CIS mode).
   - Select **Procedural Vector AI** (instant CPU) or **LCM DreamShaper AI** (local diffusion scenic backdrops).
5. **Voice, Pacing & Ending CTA**: Pick a Kokoro ONNX narrator voice, keep **Auto Voice Speed** enabled, and optionally toggle **Ending Follow / CTA Screen**.
6. **Generate & Preview**: Click **Generate Video** (or **Generate Illustrated Video**), then watch and export directly from the built-in Preview tab or `output/` folder.

---

## 📂 Project Structure

```
Stickman-Studio/
├── assets/
│   └── fonts/                         # Bundled Caveat & NotoSans typography + OFL licenses
├── docs/
│   └── images/                        # Visual previews and showcase frames
├── src/
│   ├── animation/                     # Moving Stickman kinematics, props, & compositor
│   │   ├── assets.py                  # Procedural vector props & cache-keyed backgrounds
│   │   ├── scene_composer.py          # Director transitions, camera choreography & auto styles
│   │   └── stickman.py                # 3-phase joint animator & facial expression engine
│   ├── audio/                         # Programmatic DSP music, SFX, & sidechain audio mixer
│   ├── captions/                      # Word-level kinetic typography & subtitles
│   ├── engine/                        # Core AI orchestration, CIS & diffusion engines
│   │   ├── ai_background_engine.py    # Contextual semantic vector backgrounds
│   │   ├── cis_manifest_builder.py    # Multi-shot kinetic manifest & mixed theme builder
│   │   ├── cis_pipeline.py            # Mode 2 Cinematic Illustrated end-to-end orchestrator
│   │   ├── cis_scene_illustrator.py   # 20-choreography sprite/prop/LCM backdrop illustrator
│   │   ├── cis_storyboard_planner.py  # Semantic script-to-choreography & CTA planner
│   │   ├── lcm_image_engine.py        # Local SimianLuo/LCM_Dreamshaper_v7 diffusion engine
│   │   ├── llm_manager.py             # Optional local Ollama LLM integration
│   │   └── scene_planner.py           # Natural language script decomposition
│   ├── styles/                        # Mode 1 Auto synthesizer & S1-S15 style pack registry
│   ├── tts/                           # Offline Kokoro ONNX & SAPI TTS + auto voice speed
│   ├── ui/                            # Obsidian-Studio PySide6 desktop GUI
│   │   ├── cis_mode_panel.py          # Mode 2 controls (canvas, engine, pacing, CTA)
│   │   ├── main_window.py             # Non-blocking main studio window & mode switcher
│   │   ├── preview_player.py          # Native video preview player
│   │   ├── settings_dialog.py         # Hardware & configuration controls
│   │   ├── style_cards.py             # Async 16-card style gallery with AUTO hero card
│   │   └── voice_panel.py             # Voice selection & auto/manual speed controls
│   ├── utils/                         # Configuration and hardware detection
│   └── video/                         # Mode 1 FFmpeg NVENC/CPU encoding pipeline
├── .gitignore                         # Clean repository filter (blocks cache/models/temp)
├── health_check.bat                   # Diagnostic environment checker
├── LICENSE                            # MIT License (Atharv Hatwar)
├── main.py                            # Application launch orchestrator
├── README.md                          # Project documentation
├── requirements.txt                   # Python dependencies
├── run.bat                            # One-click startup script
└── setup_windows.bat                  # Automated Windows environment installer
```

---

## 🔧 GPU Acceleration Tips (GTX 1650 / NVIDIA)

- **Python 3.11 / 3.12 with CUDA**:
  If you have an NVIDIA GPU (such as GTX 1650 4GB) and want PyTorch CUDA acceleration for LCM diffusion backgrounds:
  ```bash
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
  ```
- **NVENC Hardware Encoding**:
  In **Settings → Performance**, ensure **NVIDIA Hardware Acceleration (NVENC)** is checked. This offloads video rendering to the GTX 1650 encoder chip, rendering 1080p video in a fraction of the time.
- **Memory Management**:
  Both the LLM and LCM DreamShaper pipeline automatically unload after their stage completes to preserve RAM/VRAM for TTS synthesis and video encoding.

---

## 👤 Author & Creator

<table align="center">
  <tr>
    <td align="center">
      <b>Atharv Hatwar</b><br>
      <i>Lead Architect, Designer & Engineer</i><br>
      Creator of <b>Stickman Studio</b><br>
      GitHub: <a href="https://github.com/atharv01h">@atharv01h</a> • Repository: <a href="https://github.com/atharv01h/Stickman-Studio">Stickman-Studio</a>
    </td>
  </tr>
</table>

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for complete details.

```
MIT License

Copyright (c) 2026 Atharv Hatwar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<p align="center">
  <b>Stickman Studio</b> • Created with ❤️ by <b><a href="https://github.com/atharv01h">Atharv Hatwar</a></b> • Zero Cloud • 100% Offline
</p>
