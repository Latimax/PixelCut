# PixelCut Local — Offline AI Background Remover & Editor

PixelCut Local is a local-first, privacy-respecting alternative to cloud-based background removers. It features a Windows desktop application (PySide6), multi-image batch queue processing, interactive composition/background editing, manual mask refinement with undo/redo, and a built-in FastAPI mobile web server for local Wi-Fi pairing.

No images are ever uploaded to cloud servers or third parties; all inference and compositing run locally on your machine.

---

## Key Features

- **Local AI Background Removal:**
  - Pluggable model registry supporting `u2netp` (fast lightweight default), `u2net` (high quality), `isnet-general-use` (intricate edges/hair), and `bria-rmbg` (research only).
  - CPU inference enabled out-of-the-box; detects and supports hardware GPU acceleration (DirectML / CUDA) automatically.
  - Reusable ONNX runtime session pooling across batch operations to avoid reloading model weights for every image.
  - Generates true RGBA cutouts with alpha channels—no fake baked-in checkerboards.
  - Preserves original image dimensions and aspect ratios.
- **Interactive Background & Composition Editor:**
  - Transparent background preview with custom high-contrast checkerboard.
  - Solid color background with visual color picker and HEX input.
  - Linear gradient background with custom multi-color stops and angle control.
  - Custom background image upload with `cover`, `contain`, and `stretch` fit modes, Gaussian blur, and brightness adjustments.
  - Foreground scale, horizontal/vertical positioning, 360° rotation, and canvas margin padding.
  - Aspect ratio canvas presets: Original, 1:1 (Square), 4:5 (Portrait), 3:4, 9:16 (Story/Reel), 16:9 (Landscape).
  - Visual effects: soft drop shadow with opacity control, and sticker outline/stroke with custom width and color.
- **Manual Mask Refinement:**
  - Non-destructive mask editing with Keep (foreground) and Remove (background) brushes.
  - Adjustable brush radius with interactive real-time cursor overlay.
  - Multi-level Undo (Ctrl+Z) and Redo (Ctrl+Y) history stack.
  - Edge feathering (Gaussian soften), boundary smoothing, and mask dilation/erosion (+/- expand & shrink).
  - Rubylith visual mask inspection overlay.
  - One-click reset to AI-generated mask.
- **Multi-Image Batch Processing & Queue:**
  - Drag-and-drop multiple images or whole folders directly onto the queue.
  - Queue management: add, remove, clear completed, and reorder.
  - Non-blocking background worker threads (`QThread`) ensure the desktop UI never freezes during inference.
  - Reuses active inference session across all queued images.
  - Batch export to custom destination folders or bundled ZIP archives.
- **Configurable Mobile Web Server & LAN Access:**
  - Built-in FastAPI + Uvicorn server running asynchronously in a background thread.
  - Configurable TCP port (default: `8765`) with port conflict detection.
  - Safe default binding (`127.0.0.1`). Explicit opt-in required for LAN mode (`0.0.0.0`).
  - Constant-time token/PIN authentication protects LAN access from unauthorized clients.
  - Reachable LAN IP auto-discovery and on-screen QR code for phone browsers.
  - Mobile-first responsive web client with camera capture, gallery upload, preview slider, background replacement, and instant download.
- **Standalone Native Android App (100% On-Device AI):**
  - Fully native Android project (`android/`) built in Kotlin and Jetpack Compose (Material 3).
  - Bundled ONNX Runtime Mobile engine (`u2netp.onnx`) running on-device with zero internet needed.
  - Interactive Before/After split slider, live transparency checkerboard, solid colors, curated gradients, and custom background photo.
  - Social media framing presets (1:1, 4:5, 9:16, 16:9), drop shadow, and outline effects.
  - One-tap save to MediaStore (`Pictures/PixelCut`) and system sharing sheet.
  - Pre-built APK available at `dist/android/PixelCut-v1.0-debug.apk`.
- **Security & Reliability Safeguards:**

  - Decompression-bomb protections and strict pixel-count caps (default 40 MP).
  - Verified image raster decoding rather than trusting file extensions or MIME headers.
  - Isolated per-job temporary directories with opaque UUIDs and path-traversal prevention.
  - Automatic cleanup of temporary job files with configurable retention (default 12 hours).
  - Rotating file logging without logging sensitive tokens, credentials, or image payloads.

---

## System Requirements

- **Operating System:** Windows 10 or Windows 11 (64-bit).
- **Python Version:** Python 3.12 64-bit (recommended for full prebuilt wheel compatibility).
- **Hardware:**
  - CPU: Any modern 64-bit multi-core Intel or AMD processor.
  - RAM: 4 GB minimum (8 GB+ recommended for large batch processing).
  - Disk Space: ~500 MB for Python environment and dependencies; ~5 MB for `u2netp` model weights (downloaded on first run).
  - Optional GPU: Compatible NVIDIA GPU with CUDA/cuDNN or DirectX 12 GPU for DirectML.

---

## Quick Start (Development Mode)

### 1. Clone & Set Up Virtual Environment

From PowerShell or Command Prompt:

```powershell
# Clone the repository
git clone https://github.com/your-repo/pixelcut-local.git
cd pixelcut-local

# Create isolated Python 3.12 virtual environment
py -3.12 -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e . --no-deps
```

### 2. Launch the Application

```powershell
# Run the Desktop UI
python src/pixelcut_local/main.py

# Or use the convenience helper script
.\scripts\run_dev.bat
```

### 3. Alternative Launch Modes

```powershell
# Run only the background FastAPI server on port 8765
python src/pixelcut_local/main.py --server-only --port 8765

# Run in LAN mode to allow mobile access
python src/pixelcut_local/main.py --server-only --port 8765 --lan

# Run a CLI smoke test on an image
python src/pixelcut_local/main.py --cli-test path/to/image.jpg --model u2netp
```

---

## Desktop Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+O` | Open Image File(s) |
| `Ctrl+Shift+O` | Add Entire Folder to Batch Queue |
| `Ctrl+R` | Run AI Background Removal on Selected Image |
| `Ctrl+Z` | Undo Last Mask Brush / Refinement Edit |
| `Ctrl+Y` | Redo Last Mask Brush / Refinement Edit |
| `Ctrl+S` | Export Current Image |
| `Ctrl+0` | Fit Image to Viewport |
| `+` / `-` | Zoom In / Zoom Out |
| `Mouse Wheel` | Smooth Zoom Centered Under Mouse |
| `Middle Click + Drag` | Pan Around Canvas |
| `Shift + Left Drag` | Pan Around Canvas (alternative) |

---

## Connecting from a Mobile Phone / Tablet

1. Open PixelCut Local on your PC.
2. In the top toolbar, click **Mobile Server** (`🌐`).
3. Select **Local Network (0.0.0.0)** to enable LAN access. Review the security notice.
4. Click **Start Server**.
5. The dialog displays:
   - Your computer's reachable LAN URL (e.g. `http://192.168.1.50:8765`).
   - A 6-character **Pairing PIN** (e.g. `B8D24E`).
   - A QR code pointing to the LAN URL.
6. Connect your phone to the **same Wi-Fi network**.
7. Scan the QR code or type the LAN URL into your mobile browser (Safari, Chrome, Firefox).
8. Tap the Key icon (`🔑`) in the mobile header, enter the Pairing PIN, and tap **Connect**.
9. Tap **Take Photo or Upload** to process any photo from your phone, adjust backgrounds, and download the finished cutout!

---

## Building the Windows Executable (`.exe`)

PixelCut Local includes a tested PyInstaller specification file (`PixelCutLocal.spec`) and automated build script.

### 1. Build Standalone One-Folder Distribution (`onedir`)

```powershell
.\scripts\build_windows.bat
```

Or manually:

```powershell
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean PixelCutLocal.spec
```

### 2. Output Location

The compiled standalone Windows distribution is created at:
```text
dist\PixelCutLocal\
  ├── PixelCutLocal.exe                     # Main standalone Windows application
  ├── _internal\
  │   ├── pixelcut_local\server\static\    # Mobile web client assets
  │   ├── PySide6\                          # Qt platform plugins and rendering DLLs
  │   ├── onnxruntime\                      # ONNX Runtime inference engine
  │   └── ...                               # Runtime dependencies
```

No Python installation is required on the target machine.

---

## AI Models and Licensing

PixelCut Local supports four open model options:

| Model ID | Name | Size | License | Commercial Cleared? | Description |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **`u2netp`** | U2-Net Light | ~4.7 MB | Apache-2.0 | **Yes** | Fast portrait/object segmentation. Recommended default for CPU workflows. |
| **`u2net`** | U2-Net Standard | ~176 MB | Apache-2.0 | **Yes** | Full-depth U2-Net model providing high-quality edge segmentation. |
| **`isnet-general-use`**| DIS IS-Net | ~174 MB | Apache-2.0 | **Yes** | High-precision Dichotomous Image Segmentation for complex boundaries. |
| **`bria-rmbg`** | BRIA RMBG 1.4/2.0 | ~176 MB | Non-Commercial CC | **No** | BRIA AI research weights. Restricted to non-commercial evaluation. |

> **First-Run Note:** Model weights are downloaded automatically on first use from trusted upstream repositories and cached in `%APPDATA%\PixelCutLocal\models` or `~/.rembg/models/`. Once downloaded, the application works 100% offline.

---

## Running the Automated Test Suite

Run all unit, integration, and API tests using pytest:

```powershell
.\.venv\Scripts\pytest.exe -v
```

The automated test suite verifies:
- Image validation (valid files, corrupt files, size limits, decompression-bomb defense).
- EXIF orientation correction and color mode conversions (CMYK, Grayscale, Palette to RGBA).
- True alpha transparency in cutouts (verifying pixel alpha channels).
- Background generation (solid colors, linear gradients, image backgrounds with cover/contain/stretch).
- Composition transformations (scale, offsets, rotation, padding, drop shadows, sticker outlines).
- Mask refinement operations (keep/remove brush strokes, feathering, smoothing, dilation/erosion, undo/redo).
- Export formats (PNG transparency, JPEG matte flattening, WebP, naming templates, overwrite rules, ZIP archiving).
- Storage isolation, UUID job directories, and temporary file retention cleanup.
- Local REST API (`/health`, `/models`, `/settings/public`, `/server-info`, `/jobs`).
- LAN authentication rejection (verifying 401/403 for unauthorized remote requests).
- Path traversal prevention.

---

## Project Structure

```text
PixelCut/
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git ignore rules
├── AGENT_PROMPT.md                  # Master prompt specification
├── BUILD_TESTING.md                 # Setup, testing, and packaging guide
├── PixelCutLocal.spec               # PyInstaller Windows build specification
├── pyproject.toml                   # Standard Python packaging configuration
├── README.md                        # Documentation and user manual
├── requirements.txt                 # Pinned Python package dependencies
├── SPECIFICATION.md                 # Technical specification and architecture
├── scripts/
│   ├── build_windows.bat            # Windows PyInstaller build script
│   └── run_dev.bat                  # Development environment runner
├── src/
│   └── pixelcut_local/
│       ├── __init__.py              # Package version and metadata
│       ├── config.py                # Typed settings and JSON persistence
│       ├── logging_setup.py         # Rotating logging with secret redaction
│       ├── main.py                  # CLI & Desktop application entry point
│       ├── core/                    # UI-agnostic core processing engine
│       │   ├── background_removal.py# Model session manager and rembg adapter
│       │   ├── composition.py       # Canvas, backgrounds, transforms, and effects
│       │   ├── constants.py         # Canvas presets, formats, and constants
│       │   ├── export.py            # PNG, JPEG flattening, WebP, and ZIP packaging
│       │   ├── image_io.py          # EXIF rotation, safe loading, and thumbnails
│       │   ├── jobs.py              # Thread-safe job manager and isolation
│       │   ├── mask_refinement.py   # Mask painting, filters, and undo/redo
│       │   ├── models.py            # Model registry, licenses, and providers
│       │   └── validation.py        # Decompression bomb and corrupt image checks
│       ├── desktop/                 # PySide6 desktop application
│       │   ├── app.py               # Application bootstrap and dark stylesheet
│       │   ├── canvas.py            # Interactive canvas with zoom, pan, and brush
│       │   ├── main_window.py       # Main window layout and event routing
│       │   ├── workers.py           # Background QThread workers
│       │   └── widgets/             # UI sidebar panels and dialogs
│       │       ├── controls_panel.py# Background, composition, and export tabs
│       │       ├── diagnostics_dialog.py # System telemetry and log folder opener
│       │       ├── queue_panel.py   # Multi-image batch queue with drag & drop
│       │       ├── server_dialog.py # Server manager, LAN pairing, and QR code
│       │       └── settings_dialog.py# Model choice, limits, and cache controls
│       ├── server/                  # FastAPI local web server
│       │   ├── app.py               # FastAPI application factory
│       │   ├── auth.py              # Constant-time LAN pairing authentication
│       │   ├── network_utils.py     # LAN IP detection and QR code generator
│       │   ├── routes.py            # Versioned API routes (/api/v1/...)
│       │   ├── schemas.py           # Pydantic request and response models
│       │   ├── server_manager.py    # Background Uvicorn thread manager
│       │   └── static/              # Responsive mobile web client
│       │       ├── app.js           # Client application logic and polling
│       │       ├── index.html       # Mobile-first web interface
│       │       └── styles.css       # Dark mode glassmorphism stylesheet
│       └── storage/                 # Storage management
│           ├── cleanup.py           # Temporary job cleanup and retention
│           └── paths.py             # User AppData and bundle path resolution
└── tests/                           # Automated test suite (pytest)
    ├── conftest.py                  # Test fixtures and synthetic images
    ├── test_api.py                  # API routes, auth, and traversal tests
    ├── test_background_removal.py   # Model registry and inference tests
    ├── test_composition.py          # Backgrounds, transforms, and effects tests
    ├── test_export.py               # Format and overwrite protection tests
    ├── test_image_io.py             # EXIF and conversion tests
    ├── test_jobs.py                 # Job lifecycle and storage tests
    ├── test_mask_refinement.py      # Mask brush and undo/redo tests
    └── test_validation.py           # File validation and security tests
```

---

## Known Limitations

1. **Model Edge Cases:** AI segmentation models perform best on distinct foreground subjects. Extreme low contrast, motion blur, and fine overlapping transparent glass may require manual refinement using the built-in Mask Editor brush.
2. **HEIC/HEIF Format:** Support for Apple HEIC/HEIF requires the optional `pillow-heif` library. If unavailable, PixelCut Local displays an actionable warning instructing the user to convert the file or install the optional decoder.
3. **JPEG Transparency:** The JPEG specification does not support alpha transparency. JPEG exports are automatically flattened against the chosen matte or background color.
4. **Local Network Use Only:** PixelCut Local is intentionally designed for trusted local network use. It is not hardened for public internet hosting and should never be exposed via router port forwarding.
