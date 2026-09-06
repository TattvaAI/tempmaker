# TempMaker • Universal Video-to-Template Engine & Studio

**TempMaker** is an automated video processing pipeline and web studio that converts **any** animated video (invitations, event announcements, motion graphics cards, intros) into a customizable, reusable template.

Users can drop in any video, and TempMaker will automatically detect scenes, locate and recognize text using native Apple Vision OCR, inpaint original text across CPU cores to produce a clean background video plate, build an editable schema, and provide a real-time web editor to customize text, fonts, and colors before re-exporting.

---

## 🌟 Key Features

- **Automated Scene Detection**: Analyzes video frame deltas and HSV color histograms to identify shot boundaries, cuts, and keyframes.
- **Apple Vision OCR Engine**: Fast native Swift tool utilizing macOS `VNRecognizeTextRequest` to extract text strings, confidence scores, bounding boxes, and typography estimates in sub-second speeds.
- **Multi-Core Video Inpainting**: Automatically creates dilated morphological masks around detected text regions and removes original text using parallel OpenCV Telea inpainting across all CPU cores while preserving background motion and audio.
- **Dynamic Schema Generation**: Auto-generates a structured `template.json` containing scenes, fields, text alignments, and colors sampled directly from the video.
- **Interactive Web Studio**:
  - Drag-and-drop video upload modal with real-time 4-step pipeline progress.
  - Dynamic form fields generated automatically for any detected text.
  - Sub-200ms live frame preview as you type or adjust colors/sizes.
  - Interactive timeline scrubber to inspect any second of the video.
  - Dual modes: Live Frame Preview and HTML5 Video Player.
  - 1-click video exporter rendering the complete customized MP4 in ~15–20 seconds.

---

## 🏗 System Architecture

```
                                [ Upload Any Video (.mp4 / .mov) ]
                                                │
                                                ▼
                                 ┌──────────────────────────────┐
                                 │   Automated Pipeline Engine  │
                                 ├──────────────────────────────┤
                                 │ 1. Scene Boundary Detection  │
                                 │ 2. Apple Vision OCR & Layout │
                                 │ 3. Text Masking & Inpainting │
                                 │ 4. Dynamic Schema Generation │
                                 └──────────────┬───────────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
     [ clean_base.mp4 ]                                                [ template.json ]
(Audio & Backgrounds preserved)                                (Scenes, Fields, Colors, Boxes)
                 │                                                             │
                 └──────────────────────────────┬──────────────────────────────┘
                                                ▼
                                 ┌──────────────────────────────┐
                                 │    Interactive Web Studio    │
                                 │  (http://localhost:8080)     │
                                 ├──────────────────────────────┤
                                 │ • Live Frame Previewer       │
                                 │ • Dynamic Text Form Editor   │
                                 │ • Color & Font Customization │
                                 │ • 1-Click Fast MP4 Exporter  │
                                 └──────────────────────────────┘
```

---

## 📋 Prerequisites

- **macOS** (with Apple Silicon or Intel)
- **Python 3.10+**
- **FFmpeg & FFprobe**: `brew install ffmpeg`
- **Xcode Command Line Tools** (for Swift compiler `swiftc`): `xcode-select --install`

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/TattvaAI/tempmaker.git
cd tempmaker
```

### 2. Set up Virtual Environment & Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Build Native Swift Tools
```bash
./bin/build.sh
```

### 4. Start the Application
```bash
python app.py
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser!

---

## 📁 Repository Structure

```
tempmaker/
├── app.py                     # Flask REST backend server
├── requirements.txt           # Python dependencies
├── .gitignore                 # Excludes heavy binaries and media artifacts
├── README.md                  # Project documentation
├── bin/
│   └── build.sh               # Compiles native Swift CLI tools
├── pipeline/
│   ├── scene_detector.py      # Automated scene cut & keyframe detector
│   ├── vision_ocr.swift       # Swift Apple Vision OCR engine
│   ├── template_generator.py  # End-to-end schema builder & color sampler
│   ├── auto_inpaint.py        # Parallel video text inpainter
│   └── universal_renderer.py  # Dynamic multi-core video renderer
├── static/
│   ├── index.html             # Studio UI layout & upload modal
│   ├── style.css              # Luxury dark & gold design theme
│   └── app.js                 # Dynamic forms, live preview & pipeline tracker
├── fonts/                     # Curated collection of serif & script fonts
└── templates/                 # Preloaded and user-created template projects
    └── wedding_invitation/    # Preloaded sample wedding invitation template
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/templates` | List all available templates |
| `POST` | `/api/templates/upload` | Upload video file to start automated template generation |
| `GET` | `/api/templates/<id>/status` | Query template generation or render progress |
| `GET` | `/api/templates/<id>` | Fetch template JSON schema and field metadata |
| `POST` | `/api/templates/<id>/save` | Save edited text, colors, and font sizes |
| `GET` | `/api/templates/<id>/preview` | Render live preview JPEG of any frame with edits applied |
| `POST` | `/api/templates/<id>/render` | Trigger multi-process MP4 video export |
| `GET` | `/api/templates/<id>/video` | Stream rendered MP4 video with HTTP range support |
| `GET` | `/api/templates/<id>/download`| Download final customized MP4 video file |

---

## 📄 License

MIT License. Developed with ❤️ by [TattvaAI](https://github.com/TattvaAI).
