# Product and Technical Specification

## 1. Product definition

**Working name:** PixelCut Local\
**Platform:** Windows desktop first; mobile browser client on the same
local network\
**Primary purpose:** remove image backgrounds, refine cutouts, composite
new backgrounds, and export edited images without requiring a cloud
upload.

This is an original application inspired by the general workflow of
background-removal tools. It must not copy remove.bg branding, assets,
or proprietary code.

## 2. User journeys

### Journey A --- one image, transparent background

1.  User opens the app and imports an image.
2.  App validates and previews it.
3.  User selects **Remove Background**.
4.  App loads the selected model if necessary, shows progress, and
    generates a cutout.
5.  The result appears over a checkerboard transparency grid.
6.  User optionally refines the mask.
7.  User exports a transparent PNG.

### Journey B --- replace the background

1.  User removes the background.
2.  User chooses a solid color, gradient, or uploaded background image.
3.  User adjusts foreground scale, position, rotation, crop, and canvas
    ratio.
4.  User previews the composite.
5.  User exports PNG, JPEG, or WebP with the correct
    transparency/flattening behavior.

### Journey C --- batch product images

1.  User selects many images or a folder.
2.  App validates each item and creates a queue.
3.  App processes each item using a reused model session.
4.  Failures are isolated to individual files.
5.  User exports all results to a selected folder or ZIP archive and
    receives a summary.

### Journey D --- use from a phone

1.  User opens the desktop app's Server panel.
2.  User chooses a port and explicitly enables local-network mode.
3.  App starts the server and displays a LAN URL and pairing token.
4.  User connects their phone to the same trusted Wi-Fi network.
5.  User opens the URL and enters the token.
6.  User uploads an image, removes/replaces the background, and
    downloads the result.
7.  User stops the server when finished.

## 3. Functional requirements

### 3.1 File input

-   Supported required formats: JPG/JPEG, PNG, WebP, BMP, TIFF.
-   HEIC/HEIF is optional; show a clear install/unsupported message if
    unavailable.
-   Apply EXIF orientation before processing.
-   Preserve the original file untouched.
-   Validate file size, decoded dimensions, image mode, and actual
    decoding.
-   Handle grayscale, palette, CMYK, RGB, and RGBA input safely by
    converting into a documented internal representation.
-   Preserve aspect ratio by default.
-   Show filename, dimensions, format, size, and queue status.

Suggested defaults (configurable): - Maximum upload: 25 MB per image. -
Maximum decoded image size: 40 megapixels. - Maximum batch count: 100
images per batch. - Maximum simultaneous inference jobs: 1 by default on
CPU; configurable after memory checks.

These are initial safety defaults, not universal technical limits.
Document how users can adjust them.

### 3.2 Background removal and model layer

Implement an interface similar to:

-   `ModelRegistry`: lists configured models, provider requirements,
    license notice, and availability.
-   `BackgroundRemovalService`: validates input, obtains/reuses an
    inference session, returns a cutout and/or alpha mask.
-   `MaskRefinementService`: applies mask operations.
-   `CompositionService`: places the foreground over the chosen
    background.
-   `ExportService`: writes the requested output format.

Keep model-specific logic inside adapters. A model can be replaced
without changing the UI/API contracts.

The chosen backend should support local inference. CPU support is
mandatory. GPU is optional and must be detected rather than assumed.

Quality controls, where supported by the selected engine: - Model
selection. - Alpha matting. - Mask post-processing. - Edge
decontamination/color-fringe reduction. - Fast vs quality mode.

Model names and options must be queried from the actual installed
backend rather than blindly assuming every model is available.

**Licensing gate:** model package license and model-weight license are
separate concerns. Before distribution, document the exact selected
model, weight source, redistribution permission, commercial-use
permission, attribution requirements, and any download terms. If
unresolved, label it as unverified and do not bundle it or claim it is
cleared for commercial use.

### 3.3 Manual mask editing

Required interactions: - Paint foreground/keep. - Paint
background/remove. - Adjustable brush radius. - Undo/redo. - Reset to
automatic mask. - Mask overlay. - Feather/soften edges. - Expand/shrink
mask. - Preview at 100% zoom.

Implementation should store mask edits as a reversible sequence or
maintain undo snapshots efficiently. Do not repeatedly degrade the
source image by flattening each edit. Use a grayscale mask/alpha
representation and recompute the composite from the original foreground
and current mask.

### 3.4 Background and composition

Background modes: 1. Transparent. 2. Solid color. 3. Linear gradient
with two or more color stops if feasible. 4. User-uploaded background
image.

For image backgrounds: - Cover, contain, and stretch fit modes. -
Position/focal-point control. - Optional blur and brightness
adjustment. - Correct handling of orientation and image dimensions.

Foreground controls: - Scale. - X/Y position. - Rotation. - Fit to
canvas. - Center. - Padding/margins. - Crop and canvas dimensions. -
Optional shadow and outline, with preview and toggles.

Canvas presets: - Original. - 1:1. - 4:5. - 3:4. - 9:16. - 16:9. -
Custom width and height.

Do not distort the subject unless the user explicitly selects stretch.
Use alpha-aware resampling to reduce halos. Maintain a
layered/non-destructive edit state.

### 3.5 Export rules

-   PNG: supports transparency.
-   WebP: support alpha where the encoder allows it.
-   JPEG: must be flattened against a selected background color/image;
    explain this in the UI.
-   Optional quality setting for lossy formats.
-   Configurable output dimensions.
-   Naming template, e.g. `{original_name}_cutout`.
-   Conflict handling: ask, skip, or auto-number; never silently
    overwrite.
-   Batch export to folder and optional ZIP.
-   Display export summary with success/failure/skip counts.
-   Strip metadata by default for privacy; if metadata preservation is
    offered, make it explicit.

### 3.6 Desktop UX

Recommended layout: - Top: Open, Add, Remove Background, Undo, Redo,
Export, Settings. - Left: file queue and statuses. - Center: canvas with
before/after toggle and checkerboard. - Right: background, mask,
composition, crop, and export controls. - Bottom: progress,
model/provider state, and messages.

Requirements: - Responsive resize behavior. - Accessible labels and
keyboard navigation for major controls. - No blocking inference on the
UI thread. - Clear empty, loading, success, and error states. - Keyboard
shortcuts documented in the README. - Settings persisted per user. -
Autosave/recovery for a current edit session is recommended; if
implemented, do not save image content outside configured local folders
without telling the user.

### 3.7 Mobile web UX

-   Responsive layout optimized for portrait phones.
-   Large touch targets.
-   Upload from file picker/camera where browser-supported.
-   Show original and result.
-   Background mode controls.
-   Progress and errors.
-   Download result.
-   Batch upload where feasible.
-   Authentication/pairing screen in LAN mode.
-   Do not rely on desktop hover interactions.
-   Use the same image-processing services as the desktop UI.

### 3.8 Server controls

-   Default host: `127.0.0.1`.
-   Default port: `8765`.
-   Host choices: localhost only; local network.
-   Port validation: integer in `1..65535`, reject privileged ports
    where permissions/OS behavior make them unsuitable, and provide a
    useful message if binding fails.
-   Server runs in a background thread/process and does not freeze the
    desktop app.
-   Start/stop is explicit.
-   Graceful shutdown stops accepting new work and cleans up completed
    temporary jobs.
-   LAN mode requires explicit confirmation and a random token or
    pairing PIN.
-   Show reachable LAN URL if an address can be determined.
-   Provide a QR code for the URL only; display the secret separately.
-   Explain that phone and PC need to be on the same trusted Wi-Fi
    network.
-   Never enable router port forwarding automatically.
-   Do not expose the server to the public internet.

### 3.9 API contract

Prefix: `/api/v1`

  -------------------------------------------------------------------------
  Endpoint                  Method                  Purpose
  ------------------------- ----------------------- -----------------------
  `/health`                 GET                     App/server health and
                                                    version; safe,
                                                    non-sensitive fields
                                                    only

  `/settings/public`        GET                     Public UI settings only

  `/models`                 GET                     Models, availability,
                                                    provider support,
                                                    license warnings

  `/jobs`                   POST                    Upload image and create
                                                    a processing job

  `/jobs/{job_id}`          GET                     Job status and progress

  `/jobs/{job_id}/result`   GET                     Download the result for
                                                    that job

  `/jobs/{job_id}`          DELETE                  Cancel or clean up a
                                                    job when possible

  `/server-info`            GET                     Safe connection status;
                                                    never reveal tokens or
                                                    arbitrary local paths
  -------------------------------------------------------------------------

Suggested job states: - `queued` - `validating` - `loading_model` -
`processing` - `compositing` - `completed` - `failed` - `cancelled`

Every job has an opaque random ID, timestamps, progress where
measurable, safe error code, and a user-readable message. Never use a
user-supplied path as a job ID or output path.

The create-job request should support a validated set of options: model
ID, quality mode, alpha-matting flag if supported, background mode,
solid color, gradient data, background image upload, canvas dimensions,
export format, and export quality. Define schemas and reject unknown or
invalid values.

### 3.10 Temporary storage and cleanup

-   Use an app-managed temp/job directory.
-   Create one isolated directory per job.
-   Do not trust client-supplied filenames as filesystem paths.
-   Use random server-generated filenames.
-   Clean old jobs automatically, with configurable retention; suggested
    default is 12 hours.
-   Provide manual "clear temporary files" action.
-   Handle files locked by the OS gracefully.
-   Never delete the user's original source files.

## 4. Architecture

Suggested package boundaries:

``` text
src/pixelcut_local/
  __init__.py
  main.py                  # application entry point
  config.py                # paths, settings, defaults
  logging_setup.py
  core/
    image_io.py
    validation.py
    models.py
    background_removal.py
    mask_refinement.py
    composition.py
    export.py
    jobs.py
  desktop/
    main_window.py
    workers.py
    widgets/
  server/
    app.py
    auth.py
    schemas.py
    routes.py
    static/
      index.html
      styles.css
      app.js
  storage/
    paths.py
    cleanup.py
tests/
  test_validation.py
  test_composition.py
  test_export.py
  test_api.py
scripts/
  run_dev.bat
  build_windows.bat
```

The exact tree can change, but boundaries must remain clear.

### Design rules

-   UI calls service methods; it does not implement image processing
    itself.
-   API routes call the same services; they do not duplicate inference
    logic.
-   Long tasks run outside UI/event-loop blocking paths.
-   Reuse model sessions for batch jobs.
-   Use dependency injection where it makes tests simpler.
-   Use typed settings and request/response schemas.
-   Avoid global mutable state except a deliberate application service
    container.
-   Make file paths work in source mode and PyInstaller mode.
-   Put writable data in per-user application-data/cache directories,
    not beside a read-only installed executable.

## 5. Error handling

Handle at minimum: - Unsupported file format. - Corrupt image. - File
too large. - Pixel count too high. - Model missing. - Model download
unavailable/offline. - Model license notice/first-run acknowledgement
where appropriate. - Inference failure. - GPU provider unavailable. -
Out of memory. - Output directory not writable. - Disk full. - Port
occupied. - LAN IP unavailable. - Authentication failure. -
Expired/unknown job. - Cancelled processing. - ZIP/export failure. -
Server start/stop failure.

For each, show a short user-facing message and log technical details. Do
not expose full tracebacks, tokens, secrets, or server filesystem paths
to mobile clients.

## 6. Security requirements

-   Local-only processing by default.
-   No cloud upload or telemetry by default.
-   Limit request body size and decoded image pixel count.
-   Use Pillow decompression-bomb safeguards and explicit dimensions
    checks.
-   Verify files by decoding them, not by trusting extension or MIME
    type.
-   Restrict allowed output formats and image options.
-   Authenticate LAN requests with a random token or pairing code.
-   Use constant-time token comparison where applicable.
-   Avoid logging credentials.
-   Keep CORS restrictive; the served local UI should be the expected
    client.
-   Disable debug/reload mode in packaged release.
-   Do not serve arbitrary filesystem paths.
-   Prevent path traversal.
-   Rate-limit or cap queued jobs.
-   Use a job ownership/session model so one client cannot fetch another
    client's results.
-   Show a clear LAN-access warning and bind only after opt-in.
-   Document that this is not a hardened public-facing internet service.

## 7. Performance expectations

Do not promise a fixed processing time across all machines. Instead: -
Keep the UI responsive. - Reuse the model session. - Stream/measure
progress where meaningful. - Provide CPU fallback. - Limit concurrency
based on memory. - Avoid holding unnecessary full-resolution copies in
memory. - Offer a lower-resolution preview if useful, while retaining
full-resolution output processing. - Report image dimensions and
selected model/provider in diagnostics.

## 8. Acceptance criteria

A release candidate is not complete until the following are verified:

### Background removal

-   [ ] A valid JPEG can be processed and exported as transparent PNG.
-   [ ] Output has RGBA/alpha transparency, not a fake checkerboard
    baked into the pixels.
-   [ ] Input dimensions are preserved unless the user changes canvas
    settings.
-   [ ] A corrupt image fails gracefully.
-   [ ] A very large image is rejected with a clear message or handled
    under a documented limit.
-   [ ] CPU inference works on a clean supported Windows environment.
-   [ ] Model session is reused during batch processing.

### Editing and export

-   [ ] Solid color replacement works.
-   [ ] Gradient replacement works.
-   [ ] Uploaded background image replacement works.
-   [ ] Cover/contain/stretch fit modes work as documented.
-   [ ] Manual keep/remove mask edits change the result.
-   [ ] Undo/redo works for mask edits.
-   [ ] JPEG export flattens transparency against the selected
    background.
-   [ ] Existing files are never silently overwritten.
-   [ ] Batch export reports partial failures correctly.

### Desktop UX

-   [ ] Inference does not freeze the main window.
-   [ ] Progress and errors are visible.
-   [ ] Settings persist across restarts.
-   [ ] Source files remain unchanged.

### Mobile/server

-   [ ] Localhost mode starts and stops.
-   [ ] Custom port is respected.
-   [ ] An occupied port produces a helpful error.
-   [ ] LAN mode is opt-in and requires a token/PIN.
-   [ ] A phone on the same Wi-Fi can upload, process, and download an
    image.
-   [ ] An unauthenticated LAN request is rejected.
-   [ ] A client cannot retrieve an unrelated job result.
-   [ ] Stopping the server closes access and cleans up appropriately.

### Packaging

-   [ ] Windows `onedir` build starts on a clean test machine without a
    Python installation.
-   [ ] Qt plugins and static web assets are included.
-   [ ] Writable cache/model/temp paths work from the packaged
    executable.
-   [ ] First-run model download or missing-model message works.
-   [ ] One-file build is optional and tested separately if offered.
-   [ ] Build instructions identify any external model download or
    license acknowledgement.

### Documentation

-   [ ] Installation, run, build, mobile access, model license, and
    troubleshooting instructions are complete.
-   [ ] The final report distinguishes tested behavior from unverified
    behavior.
