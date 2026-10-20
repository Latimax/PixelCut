# Build, Test, Windows EXE, and Mobile Access Guide

This document describes the intended developer workflow. The coding
agent must update commands and version pins to match the actual
repository it creates.

## 1. Prerequisites

-   Windows 10/11 for the Windows executable build.
-   A supported Python version compatible with all pinned dependencies.
-   Git (recommended).
-   Enough disk space for Python dependencies and the selected AI model
    weights.
-   Optional: a compatible NVIDIA GPU and matching ONNX Runtime/CUDA
    stack. CPU mode must remain supported.
-   For phone access: PC and phone connected to the same trusted Wi-Fi
    network.

Do not assume the newest Python version is compatible with every
dependency. Verify compatibility and pin tested versions.

## 2. Create an isolated environment

From the project root, create a virtual environment:

``` powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If the project uses `pyproject.toml` instead of `requirements.txt`,
follow the installation command documented in the repository README.

If PowerShell blocks environment activation, use the documented Windows
policy-safe alternative or run the environment's Python executable
directly. Do not instruct users to weaken system security broadly.

## 3. Run in development mode

The project should provide a helper script, for example:

``` powershell
.\scripts\run_dev.bat
```

The README must also document direct commands for: - Starting the
desktop app. - Starting the API server in development mode, if
supported. - Running tests. - Running a single image-processing smoke
test.

Do not run Uvicorn with reload/debug settings in packaged release mode.

## 4. First-run model setup

The application must clearly indicate whether model weights are: -
already installed, - being downloaded, - unavailable offline, -
incompatible with the selected provider, or - blocked by an unresolved
license/configuration issue.

Prefer a dedicated user cache/model directory rather than the
installation directory. Document the exact path in the app's diagnostics
page and README.

Do not silently download an enormous model without showing the user the
model name, approximate size when known, source, and license notice.
Avoid claiming a size unless verified for the selected model/version.

After a successful first download, confirm the app can restart and
process an image without downloading the same weights again.

## 5. Automated tests

Run tests from the project root:

``` powershell
pytest -q
```

At minimum, automate tests for:

-   Image validation and unsupported formats.
-   EXIF orientation handling.
-   Alpha-channel output.
-   Solid-color compositing.
-   Gradient compositing.
-   Background-image compositing.
-   JPEG flattening behavior.
-   Output naming and overwrite protection.
-   Temp-file cleanup.
-   API health and job lifecycle.
-   Unauthorized LAN request rejection.
-   Invalid job IDs and path traversal attempts.
-   Port validation.
-   Graceful handling of a failed model load.

Use small synthetic test images so most tests do not require a model
download. Keep at least one separately documented end-to-end test that
uses the real selected model.

Do not mark model-dependent tests as passed if the model could not be
downloaded or run.

## 6. Manual acceptance test

Use at least these sample cases:

1.  Product on a plain white background.
2.  Person with hair against a contrasting background.
3.  Object with fine edges or fur.
4.  Subject with a low-contrast edge.
5.  PNG with existing transparency.
6.  Very wide or very tall image.
7.  Corrupt or renamed non-image file.
8.  Multiple images in a batch with one invalid file.
9.  Solid background replacement.
10. Uploaded background replacement.
11. Transparent PNG export and JPEG export.
12. Manual mask edit with undo/redo.
13. Mobile upload and download over Wi-Fi.

Judge quality visually. Do not claim the model passes every edge case
because it passes one sample image.

## 7. Build a Windows executable

### Recommended first build: one-folder

First verify the app runs from source and the tests pass. Then use the
project's build script, for example:

``` powershell
.\scripts\build_windows.bat
```

Or run the project's documented PyInstaller command. A typical pattern
is:

``` powershell
pyinstaller --noconfirm --clean PixelCutLocal.spec
```

The actual `.spec` filename and command must match the repository.

The first release target should be a one-folder distribution (`onedir`)
because it is easier to debug and usually simpler for large native
dependencies and model-related files. The deliverable folder should
include the executable and required support files.

### Optional one-file build

Only after the one-folder build is verified, offer a separate one-file
target. One-file builds extract bundled support files at launch, can
start more slowly, and can be more difficult to troubleshoot. Do not
promise that one-file mode is always the best choice.

### Packaging checklist

-   [ ] PySide6 Qt platform plugins included.
-   [ ] FastAPI static assets included.
-   [ ] Config defaults and templates included.
-   [ ] No secrets included.
-   [ ] Writable settings/cache/temp paths point to user data
    directories.
-   [ ] Model weights are either intentionally bundled with license
    clearance or downloaded/stored externally with a clear first-run
    workflow.
-   [ ] CPU provider works.
-   [ ] Missing model gives a helpful message.
-   [ ] Server starts and stops from the packaged app.
-   [ ] Phone UI assets load from the packaged app.
-   [ ] Build tested on a clean Windows machine without Python
    installed.
-   [ ] Antivirus false-positive risks considered; do not tell users to
    disable antivirus.
-   [ ] App version and build instructions recorded.

Build the Windows executable on Windows. A build created on Linux/macOS
is not a substitute for a verified Windows build.

## 8. Mobile access from the same Wi-Fi network

1.  Launch PixelCut Local on the PC.
2.  Open **Settings → Server**.
3.  Leave host mode on `localhost only` unless phone access is needed.
4.  To use a phone, select **Local network**, review the warning, and
    confirm.
5.  Enter the desired port (default `8765`) and start the server.
6.  Read the LAN URL shown by the app, such as
    `http://192.168.x.x:8765`. Use the actual address shown by the app;
    do not guess the IP.
7.  Connect the phone to the same trusted Wi-Fi network.
8.  Open the URL in the phone browser and enter the pairing token/PIN
    shown by the desktop app.
9.  Upload a test image, process it, and download the result.
10. Stop the server when finished.

### If the phone cannot connect

-   Confirm both devices are on the same Wi-Fi network, not isolated
    guest networks.
-   Confirm the desktop app is in **Local network** mode rather than
    localhost-only mode.
-   Confirm the server is running and the port displayed in the UI
    matches the URL.
-   Check Windows Firewall and allow the app on the private network only
    if appropriate.
-   Check whether another application is using the port.
-   Do not disable the firewall globally.
-   Do not enable router port forwarding or expose the app to the public
    internet.
-   If the PC uses a VPN, verify that the phone can reach the PC's LAN
    interface.

## 9. Port and server behavior

The app should validate the port as an integer in the valid TCP port
range and show a clear error if the port is unavailable. The server must
not silently switch to a different port without updating the displayed
URL.

Default to `127.0.0.1`. LAN mode should bind to the selected LAN
interface or `0.0.0.0` only after the user opts in. Require a pairing
token for LAN requests. The token must not be placed in the QR code or
URL query string.

## 10. Troubleshooting

### Model download fails

-   Check the model source and internet connection.
-   Show the exact model name and a concise error.
-   Allow retry.
-   Do not fall back to a cloud API without explicit user consent.
-   If offline, explain which local models are already available.

### GPU does not work

-   Fall back to CPU if possible.
-   Report the active inference provider.
-   Document the exact compatible ONNX Runtime/GPU dependency
    combination for the tested build.
-   Do not assume all NVIDIA machines have a compatible CUDA/cuDNN
    setup.

### Executable opens and immediately closes

-   Reproduce with a console-enabled diagnostic build.
-   Write a rotating log to a per-user writable directory.
-   Check missing PyInstaller hidden imports, Qt plugins, model paths,
    and native DLLs.
-   Do not ask the user to run as administrator as a generic fix.

### UI assets missing in packaged app

-   Check the `.spec` file's data-file collection.
-   Resolve paths using a helper that supports both source and
    PyInstaller runtime locations.
-   Test the packaged server's `/` page and static CSS/JS.

### Output has a halo

-   Try the higher-quality edge mode or model.
-   Enable supported decontamination/alpha matting options.
-   Refine the mask manually.
-   Check the background color around the subject in the original image.
-   Do not assume one setting is optimal for every image.

### JPEG output has no transparency

This is expected: JPEG does not support an alpha channel. Choose PNG or
alpha-capable WebP for transparency, or select the background color
against which the JPEG should be flattened.

## 11. Release checklist

-   [ ] Tests run and results recorded honestly.
-   [ ] Model and weight license reviewed.
-   [ ] Privacy and LAN security reviewed.
-   [ ] Upload limits tested.
-   [ ] App works without GPU.
-   [ ] One-folder executable tested on a clean Windows machine.
-   [ ] Mobile UI tested on a real phone.
-   [ ] Server can be stopped and restarted.
-   [ ] No source images are overwritten.
-   [ ] Temporary files are cleaned up.
-   [ ] Known limitations are visible in the documentation.
