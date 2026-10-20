# PixelCut Local --- Python Background Remover

A project brief for building a local-first, remove.bg-style image
background remover with a Windows desktop application, batch processing,
background replacement, and a mobile-friendly LAN web interface.

> **Important:** This is a product specification, not a claim that any
> AI model can produce perfect cutouts on every image. Hair, glass,
> motion blur, low contrast, shadows, and complex overlaps may require
> manual refinement.

## Documents in this pack

1.  [`AGENT_PROMPT.md`](AGENT_PROMPT.md) --- the master instruction to
    paste into your AI coding agent.
2.  [`SPECIFICATION.md`](SPECIFICATION.md) --- detailed functional,
    technical, security, and acceptance requirements.
3.  [`BUILD_TESTING.md`](BUILD_TESTING.md) --- setup, testing, Windows
    `.exe` packaging, mobile/LAN use, and troubleshooting.

## Product goal

Build a practical, offline-first desktop tool that can:

-   Remove image backgrounds and save transparent PNGs.
-   Replace a background with a solid color, gradient, or a
    user-uploaded image.
-   Refine cutout edges and manually restore/remove parts of a mask.
-   Edit composition, size, crop, padding, and export format.
-   Process folders of images in batches.
-   Run a local web server with a configurable port so a phone on the
    same Wi-Fi network can use the tool.
-   Package as a Windows executable.

## Recommended architecture

-   **Desktop UI:** PySide6.
-   **Image processing:** Pillow + NumPy + OpenCV where useful.
-   **Background-removal engine:** a pluggable adapter around
    `rembg`/ONNX Runtime, with model choice and license review
    documented.
-   **Local mobile web server:** FastAPI + Uvicorn, serving a responsive
    local web UI.
-   **Packaging:** PyInstaller, initially in one-folder (`onedir`) mode;
    provide a one-file build as an optional target after the one-folder
    build is verified.
-   **Tests:** pytest, API tests, image-pipeline tests, and a manual
    Windows packaging checklist.

Keep the image-processing core independent of both the desktop UI and
the web API. The desktop app and mobile interface must call the same
service layer so that results are consistent.

## Privacy and licensing

-   Process images locally by default. Do not upload images to a cloud
    API unless the user explicitly enables and configures an external
    provider.
-   Do not bundle model weights until the exact weight license and
    redistribution terms have been checked.
-   The `rembg` package and its available models have different
    licensing considerations. Its current documentation lists multiple
    models and notes that some model weights, including BRIA RMBG 2.0,
    may require a paid agreement for commercial use. Review the model's
    current license before commercial distribution.
-   Bind the server to `127.0.0.1` by default. To use a phone on the
    same Wi-Fi network, the user must explicitly enable LAN access,
    which binds to `0.0.0.0` or the selected LAN interface. Never
    silently expose the server to the public internet.
-   Use a pairing token/password for LAN access, validate all uploads,
    restrict file sizes/pixel counts, and automatically clean up
    temporary files.

## Useful upstream references

-   `rembg` project and model/usage notes:
    https://github.com/danielgatis/rembg
-   `rembg` usage documentation:
    https://github.com/danielgatis/rembg/blob/main/USAGE.md
-   FastAPI deployment guidance:
    https://fastapi.tiangolo.com/deployment/manually/
-   PyInstaller operating modes:
    https://pyinstaller.org/en/stable/operating-mode.html
-   PyInstaller usage: https://pyinstaller.org/en/stable/usage.html

These links are starting points, not a substitute for checking the
current package versions, compatibility matrix, and model-weight
licenses before release.
