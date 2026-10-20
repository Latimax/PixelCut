# Master Prompt for the AI Coding Agent

## Your role

Act as a senior Python desktop, computer-vision, backend, frontend, QA,
and Windows-packaging engineer. Build a complete, runnable application
named **PixelCut Local**. Do not merely provide a tutorial, mock-up,
pseudocode, or isolated snippets. Create the actual project files,
implement the features, run tests where your environment permits, and
document any tests you cannot run.

The target is a practical local alternative to remove.bg. Do not copy
remove.bg branding, source code, proprietary assets, or claim identical
model quality. Build an original application with comparable core
workflows.

## Required deliverables

Create a complete repository containing, at minimum:

-   `README.md`
-   `requirements.txt` or a properly pinned `pyproject.toml`
-   `.gitignore`
-   `.env.example` only if environment variables are actually used
-   `src/pixelcut_local/` application package
-   Desktop entry point
-   FastAPI server entry point
-   Image-processing service and model adapter
-   Responsive mobile web UI assets
-   Settings/configuration module
-   Temporary-file/job manager
-   Logging and user-friendly error handling
-   Unit and API tests
-   `scripts/run_dev.bat`
-   `scripts/build_windows.bat` or PowerShell equivalent
-   PyInstaller `.spec` file or documented reproducible build commands
-   `BUILD_TESTING.md`
-   A troubleshooting guide
-   A clear list of known limitations and model-license notes

Use a maintainable project structure. Avoid placing the whole
application in one enormous Python file.

## Core stack

Use these defaults unless a concrete compatibility issue requires a
documented alternative:

-   Python version: choose a version supported by the selected versions
    of PySide6, FastAPI, Pillow, ONNX Runtime, the chosen
    background-removal library, and PyInstaller. Confirm compatibility
    before pinning.
-   Desktop UI: PySide6.
-   API/server: FastAPI + Uvicorn.
-   Image I/O/compositing: Pillow, NumPy; use OpenCV only where it adds
    measurable value.
-   AI inference: an adapter interface around `rembg`/ONNX Runtime or
    another explicitly documented, locally runnable model.
-   Tests: pytest and FastAPI test client.
-   Packaging: PyInstaller.

The image-processing layer must not depend on PySide6 or FastAPI. Both
interfaces must call the same application services.

## Must-have features

### 1. Import and preview

-   Drag and drop one or many images.
-   Browse files and folders.
-   Support JPEG/JPG, PNG, WebP, BMP, and TIFF. Treat HEIC/HEIF as
    optional and clearly report when its decoder is not installed.
-   Correct EXIF orientation before processing.
-   Show filename, dimensions, file size, and processing status.
-   Display original and result previews, with before/after comparison.
-   Provide zoom, fit-to-screen, pan, and a checkerboard transparency
    preview.
-   Never silently overwrite the source file.

### 2. AI background removal

-   Remove the background and produce an RGBA cutout with a true alpha
    channel.
-   Preserve original image dimensions by default.
-   Provide a configurable model adapter so the model can be changed
    without rewriting UI code.
-   Reuse a loaded inference session for batch processing; do not reload
    the model for every image.
-   Support CPU inference. GPU acceleration may be optional and must
    fail back to CPU gracefully when a compatible provider is
    unavailable.
-   Show model loading/download status, processing progress, and clear
    errors.
-   Support available mask/edge options such as mask post-processing,
    alpha matting, and color decontamination only when supported by the
    selected engine.
-   Offer a fast/default mode and a higher-quality/slow mode.
-   Allow users to retry with another installed model if the result is
    poor.
-   Do not claim that a model is always perfect.
-   Model weights must be downloaded only from a trusted configured
    source. Do not download arbitrary files or execute model files from
    user-supplied URLs.
-   Do not bundle or enable a model for commercial distribution until
    its exact weight license is checked.

### 3. Manual refinement

Provide a mask editor after automatic removal:

-   Brush to mark foreground/keep.
-   Brush to mark background/remove.
-   Adjustable brush size.
-   Undo/redo for edits.
-   Edge feathering.
-   Edge smoothing.
-   Expand/shrink mask.
-   Reset mask to AI result.
-   Show/hide mask overlay.
-   Keep the original source and AI-generated mask available so edits
    are non-destructive.
-   If a feature cannot be implemented in the first release, label it as
    a planned feature rather than showing a fake or inactive control.

### 4. Background editor

Users must be able to select:

-   Transparent background.
-   Solid color using a color picker and HEX input.
-   Gradient background with at least two color stops and
    angle/direction.
-   An uploaded background image.
-   Background image fit mode: cover, contain, or stretch.
-   Background blur and brightness controls, if practical.
-   Foreground scale, horizontal/vertical position, rotation, and canvas
    padding.
-   Optional shadow and outline/stroke, each with a toggle and
    adjustable intensity.
-   Crop and output canvas aspect ratio.
-   Common canvas presets such as original, 1:1, 4:5, 3:4, 9:16, and
    16:9.
-   Reset composition to defaults.

Compositing must use the alpha channel correctly. When exporting JPEG,
flatten transparency against the chosen background and tell the user
that JPEG does not support transparency.

### 5. Export

-   PNG with transparency.
-   JPEG/JPG with a chosen matte background.
-   WebP, including alpha when supported by the selected encoder.
-   Configurable output dimensions and quality.
-   Preserve aspect ratio unless the user explicitly chooses stretch.
-   Single-file export and batch export.
-   Batch export to a selected folder and optional ZIP archive.
-   Output naming template, e.g. `{original_name}_cutout`.
-   Warn before overwriting an existing output; provide safe
    auto-numbering.
-   Report successful, failed, skipped, and cancelled files separately.
-   Never overwrite originals by default.
-   Include a clear export summary.

### 6. Batch workflow

-   Add/remove/reorder queue items.
-   Start, pause where practical, cancel, retry failed, and clear
    completed jobs.
-   Show per-file and overall progress.
-   Continue processing other files after one file fails.
-   Reuse the model session.
-   Support configurable maximum parallelism; default to conservative
    concurrency to avoid memory exhaustion.
-   Provide a clear estimate only if it can be measured reliably; do not
    invent processing-time estimates.

### 7. Desktop application

Create a polished, usable desktop layout:

-   Top toolbar: Open, Add Files, Remove Background, Undo, Redo, Export,
    Settings.
-   Left panel: queue and batch status.
-   Center: canvas and before/after view.
-   Right panel: background, edge, crop, dimensions, and export
    settings.
-   Bottom/status area: model state, CPU/GPU provider, progress, and
    error messages.
-   Settings page: model choice, model storage path, cache/temp paths,
    output defaults, memory-conscious batch settings, server host/port,
    and LAN access.
-   Use worker threads/tasks so inference and file operations never
    freeze the UI.
-   Show actionable errors rather than raw tracebacks. Write technical
    details to a log file.
-   Support keyboard shortcuts for common actions and document them.

### 8. Mobile web interface and configurable server

The desktop app must include a Server panel with:

-   Start server / Stop server.
-   Host mode: `localhost only` (default) or `local network`.
-   Editable port, default `8765`.
-   Validate the port range and show a useful error if the port is
    occupied.
-   Show the current server status and URL.
-   Show the PC's reachable LAN address when available.
-   Show a QR code for the URL; do not put a secret access token into
    the QR URL.
-   For LAN mode, generate/show a pairing token or PIN and require
    authentication in the mobile UI.
-   Copy URL and token actions.
-   Open the desktop browser locally.
-   Display a short firewall/privacy warning when enabling LAN mode.
-   Server startup failure must not crash the desktop app.
-   Server shutdown must be graceful.

The mobile page must be responsive and usable on modern Android and iOS
browsers. It must support:

-   Upload from the phone's photo library/camera where the browser
    permits.
-   Preview before and after.
-   Remove background.
-   Choose transparent, solid-color, gradient, or uploaded-image
    background.
-   Basic crop/fit and export options.
-   Download result to the phone.
-   Batch selection where supported.
-   Progress and helpful errors.
-   A clear connection/authentication state.

Default server binding is `127.0.0.1`. Only bind to `0.0.0.0` or a LAN
interface after the user explicitly selects LAN mode. Do not configure
router port forwarding or public internet exposure.

### 9. Local API

Provide and document versioned endpoints. Exact internal implementation
may vary, but cover these capabilities:

-   `GET /api/v1/health` --- status/version/model readiness.
-   `GET /api/v1/settings/public` --- safe public settings only; never
    return secrets or local filesystem paths unnecessarily.
-   `GET /api/v1/models` --- supported model options and
    availability/license notices.
-   `POST /api/v1/jobs` --- accept an image and removal/compositing
    options, validate input, create a job, return a job ID.
-   `GET /api/v1/jobs/{job_id}` --- status and progress.
-   `GET /api/v1/jobs/{job_id}/result` --- securely return the result
    for that job.
-   `DELETE /api/v1/jobs/{job_id}` --- cancel/clean up where possible.
-   `GET /api/v1/server-info` --- safe connection information only;
    never expose secrets.
-   Optional batch-job endpoint if needed.

Use a job-based flow for long-running inference so mobile requests do
not time out. Use strict schemas and typed responses. Never accept
arbitrary output paths from the browser. Store results in managed
temporary storage and use opaque job IDs.

### 10. Security and privacy

-   All processing is local by default.
-   No analytics, telemetry, or external image upload by default.
-   Validate actual image decoding, not just filename extension or MIME
    header.
-   Configure maximum upload bytes and maximum decoded pixel count.
-   Protect against decompression bombs and malformed files.
-   Sanitize filenames; never use user filenames as arbitrary paths.
-   Use generated temporary names and per-job directories.
-   Prevent path traversal and unauthorized access to other job results.
-   Require a random token/pairing code for LAN access.
-   Compare authentication tokens safely and never log them.
-   Apply request-size limits and reasonable job/rate limits.
-   Bind localhost by default; clearly warn for LAN mode.
-   Do not expose debug mode or interactive API documentation to
    unauthenticated LAN clients in release mode.
-   Add automatic cleanup for temporary uploads/results after a
    configurable retention period.
-   Log errors without recording image contents or secrets.
-   Do not claim the app is safe for public internet hosting. This
    specification targets trusted local use.

### 11. Reliability and quality

-   Use structured logging with rotating log files.
-   Handle missing model weights, first-run download failure, offline
    startup, disk-full errors, unsupported image formats, corrupt
    images, out-of-memory errors, occupied ports, and interrupted jobs.
-   Keep the UI responsive during inference.
-   Avoid duplicate model initialization.
-   Provide graceful cancellation and cleanup.
-   Include a diagnostics page with app version, Python/runtime
    information where available, selected inference provider, model
    status, writable cache/temp checks, and server status. Do not reveal
    secrets.
-   Add an option to open the log folder.

### 12. Packaging

-   Build and test a Windows `onedir` executable first.
-   Provide an optional `onefile` build after the `onedir` build is
    stable.
-   Include all required Qt plugins, static web assets, templates, and
    non-secret configuration.
-   Do not assume model weights are inside the executable. Prefer a
    documented external model/cache directory with first-run download
    and license notice.
-   Resolve data paths correctly in source and PyInstaller builds.
-   Never write user data into a read-only install directory; use a
    suitable per-user application-data folder.
-   Provide a build script and a clean-machine smoke-test checklist.
-   Build on Windows for Windows. Do not promise that a Windows
    executable can be produced reliably from Linux/macOS.
-   Explain that one-file packaging can start more slowly and complicate
    diagnosis; one-folder is the default recommendation.

## Implementation order

Build in these phases, and keep the application runnable after each
phase:

1.  Repository skeleton, config, logging, image validation, and tests.
2.  Working local background-removal service and CLI smoke test.
3.  Desktop UI with single-image removal and transparent PNG export.
4.  Background replacement, composition controls, manual mask
    refinement, and export.
5.  Batch processing and queue.
6.  FastAPI job API and responsive mobile web UI.
7.  Server controls, port selection, LAN pairing, QR code, and cleanup.
8.  PyInstaller build, model-path handling, Windows scripts, and
    packaged smoke tests.
9.  Final regression, security review, and documentation.

Do not leave placeholder buttons, fake progress bars, hard-coded success
messages, or TODO-only implementations for required features. If a
feature is deferred, remove it from the active UI and document it
honestly.

## Required final response from you, the coding agent

When implementation is complete, report:

1.  Files created and project structure.
2.  Exact installation and run commands.
3.  Exact Windows build command and output location.
4.  How to start the server and connect from a phone.
5.  Which AI model is configured, where weights are stored, its license
    status, and whether first-run internet access is required.
6.  Tests actually run and their real results.
7.  Features that are complete, incomplete, or unverified.
8.  Known limitations and any remaining manual steps.

Never claim tests passed unless they were actually executed.
