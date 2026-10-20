# Build, Test, Windows EXE, and Mobile Access Guide

This document describes the complete developer and deployment workflow for **PixelCut Local**.

---

## 1. Prerequisites

- **Operating System:** Windows 10 or Windows 11 (64-bit).
- **Python Version:** Python 3.12 64-bit.
  - *Note on Python compatibility:* Python 3.12 is chosen because prebuilt wheels for `onnxruntime`, `PySide6`, `rembg`, `scipy`, `numpy`, and `pyinstaller` are verified and tested.
- **Git:** For version control.
- **Disk Space:** ~500 MB for Python environment and packages; ~5 MB to ~180 MB for chosen AI model weights.
- **Optional GPU:** NVIDIA GPU with CUDA or DirectX 12 GPU for DirectML. CPU mode is fully supported and enabled by default.
- **Wi-Fi Network:** For mobile phone access, the PC and phone must be connected to the same trusted local Wi-Fi network.

---

## 2. Environment Setup

From the project root in PowerShell:

```powershell
# Create an isolated Python 3.12 virtual environment
py -3.12 -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e . --no-deps
```

*Note on Execution Policies:* If PowerShell blocks running `Activate.ps1`, use the standard safe bypass for the current process:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```
Or directly invoke the virtual environment's Python executable (`.\.venv\Scripts\python.exe`).

---

## 3. Running in Development Mode

### Running the Desktop GUI

```powershell
# Using the helper batch script
.\scripts\run_dev.bat

# Or directly using Python
python src/pixelcut_local/main.py
```

### Running the Mobile Web Server (Headless)

```powershell
# Localhost only (127.0.0.1:8765)
python src/pixelcut_local/main.py --server-only --port 8765

# Local network mode (0.0.0.0:8765) with phone access
python src/pixelcut_local/main.py --server-only --port 8765 --lan
```

### Running a CLI Smoke Test

```powershell
python src/pixelcut_local/main.py --cli-test test_subject.png --model u2netp
```

---

## 4. Automated Testing

All unit, composition, export, security, and API tests are automated using `pytest`:

```powershell
# Run the entire test suite
.\.venv\Scripts\pytest.exe -v

# Run with concise summary
.\.venv\Scripts\pytest.exe -q
```

### Verified Test Coverage

1. **`test_validation.py`**:
   - Decoding verification on valid PNG/JPEG/WebP images.
   - Rejection of 0-byte empty files.
   - Rejection of corrupt or renamed non-image files (`CORRUPT_OR_UNSUPPORTED`).
   - File size limits (rejecting uploads exceeding max upload MB).
   - Decompression-bomb limits (rejecting extreme pixel dimensions).
2. **`test_image_io.py`**:
   - Safe normalization of CMYK, Palette, and Grayscale images to RGBA.
   - EXIF orientation transposition.
   - High-quality thumbnail generation with aspect ratio preservation.
3. **`test_composition.py`**:
   - Solid color background rendering with accurate HEX colors.
   - 2-color linear gradient calculation across angles.
   - Background image fitting (`cover`, `contain`, `stretch`), blur, and brightness.
   - Canvas preset dimensions (`1:1`, `4:5`, `3:4`, `9:16`, `16:9`).
   - Transparent checkerboard compositing.
   - Soft drop shadows and sticker outlines.
4. **`test_export.py`**:
   - PNG export preserving true 8-bit alpha channels.
   - JPEG export correctly flattening transparency against chosen matte.
   - Naming templates (`{original_name}_cutout`).
   - Safe auto-numbering overwrite protection (`_1`, `_2`).
   - Bundled ZIP archive export.
5. **`test_mask_refinement.py`**:
   - Manual keep (foreground, 255) and remove (background, 0) brush strokes.
   - Multi-step undo/redo history stack integrity.
   - Visual rubylith mask overlay generation.
6. **`test_jobs.py`**:
   - Job lifecycle state machine (`queued` -> `processing` -> `completed` / `cancelled`).
   - Storage isolation in UUID directories.
   - Automatic cleanup of expired temporary jobs.
7. **`test_api.py`**:
   - `GET /api/v1/health` and model readiness reporting.
   - `GET /api/v1/settings/public` returning non-sensitive settings.
   - `GET /api/v1/models` reporting model sizes and license notices.
   - `GET /api/v1/server-info` returning safe connection details.
   - `POST /api/v1/jobs` multipart image upload and asynchronous processing.
   - `GET /api/v1/jobs/{id}/result` download.
   - Non-existent job IDs returning 404.
   - Path traversal rejection.
   - Rejection of unauthenticated remote LAN requests (401/403).
8. **`test_background_removal.py`**:
   - Model registry entries and license terms.
   - Provider detection containing `CPUExecutionProvider`.

---

## 5. Building the Windows Standalone Executable

### Recommended Build: One-Folder (`onedir`)

```powershell
.\scripts\build_windows.bat
```

Or manually:

```powershell
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean PixelCutLocal.spec
```

### Packaging Verification Checklist

- [x] **PySide6 Qt platform plugins:** Bundled in `dist\PixelCutLocal\_internal\PySide6\`.
- [x] **FastAPI static assets:** Bundled in `dist\PixelCutLocal\_internal\pixelcut_local\server\static\`.
- [x] **ONNX Runtime:** Bundled in `dist\PixelCutLocal\_internal\onnxruntime\`.
- [x] **No hardcoded secrets:** No pairing tokens or user data baked into binary.
- [x] **Writable paths:** Packaged app stores user settings, logs, and temporary jobs in `%APPDATA%\PixelCutLocal\`.
- [x] **Model weights:** Downloaded on first run to user cache or loaded from `%APPDATA%\PixelCutLocal\models\`.
- [x] **Standalone execution:** Runs on Windows without Python installed.

---

## 6. Mobile Access Setup (Wi-Fi)

1. Launch PixelCut Local on the PC.
2. In the top toolbar, click **Mobile Server** (`🌐`).
3. Select **Local Network (0.0.0.0)** and click **Start Server**.
4. Note the LAN URL (e.g. `http://192.168.1.50:8765`) and **Pairing PIN** (e.g. `B8D24E`).
5. On your phone (connected to the same Wi-Fi), open the browser and navigate to the LAN URL.
6. Tap the Key icon (`🔑`), enter the PIN, and connect.
7. Upload any photo from your phone's camera or photo gallery to remove its background and download the cutout directly to your device.

---

## 7. Troubleshooting Guide

### Model Download Fails / Offline Startup

- **Symptom:** App shows `Failed to load AI model`.
- **Cause:** First run requires internet access to download model weights (~4.7 MB for `u2netp`).
- **Fix:** Verify your internet connection. Alternatively, manually place `u2netp.onnx` into `%APPDATA%\PixelCutLocal\models\u2netp.onnx` or `~/.rembg/models/u2netp/u2netp.onnx`.

### Phone Cannot Reach PC over Wi-Fi

- **Symptom:** Browser on phone times out when opening `http://192.168.x.x:8765`.
- **Checks:**
  1. Confirm PC and phone are on the **exact same Wi-Fi network** (not a guest network with client isolation).
  2. Confirm the desktop app is in **Local Network** mode, not Localhost-only mode.
  3. Check Windows Firewall: allow Python / PixelCutLocal on **Private networks**.
  4. Ensure any active VPN on the PC is not isolating local LAN traffic.

### Port Occupied Error

- **Symptom:** `Port 8765 is already in use by another application`.
- **Fix:** In the **Mobile Server** dialog, change the port number to another unprivileged port (e.g. `8766`, `8800`, or `9000`) and click **Start Server**.

### JPEG Output Has No Transparency

- **Explanation:** This is standard behavior across digital imaging: the JPEG format does not have an alpha channel. If you need transparency, choose **PNG** or **WEBP**. If exporting JPEG, choose your desired background matte color (default is white) in the Background tab.
