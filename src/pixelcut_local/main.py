"""Application entry point for PixelCut Local.

Supports:
- Desktop GUI (default)
- Headless FastAPI server mode (--server-only)
- CLI background removal smoke test (--cli-test)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pixelcut_local import __app_name__, __version__
from pixelcut_local.config import Settings
from pixelcut_local.logging_setup import setup_logging

logger = logging.getLogger("pixelcut_local")


def main() -> int:
    """Parse command line arguments and launch appropriate application mode."""
    setup_logging(level=logging.INFO)

    parser = argparse.ArgumentParser(
        prog="pixelcut_local",
        description=f"{__app_name__} v{__version__} - Offline-first AI Background Remover and Editor.",
    )
    parser.add_argument(
        "--server-only",
        action="store_true",
        help="Run only the FastAPI background removal server without launching the desktop GUI.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host interface to bind the web server (e.g. 127.0.0.1 or 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="TCP port for web server (default: 8765).",
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help="Enable local network (LAN) access mode for mobile devices.",
    )
    parser.add_argument(
        "--cli-test",
        type=str,
        default=None,
        metavar="IMAGE_PATH",
        help="Run a quick background removal smoke test on an image and exit.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Specify AI model (u2netp, u2net, isnet-general-use, bria-rmbg).",
    )

    args = parser.parse_args()

    # 1. CLI Smoke Test Mode
    if args.cli_test:
        input_path = Path(args.cli_test)
        if not input_path.exists():
            print(f"Error: Test file not found: {input_path}", file=sys.stderr)
            return 1

        print(f"[{__app_name__}] Running CLI smoke test on: {input_path}")
        from pixelcut_local.core.background_removal import remove_background
        from pixelcut_local.core.export import export_image
        from pixelcut_local.core.image_io import load_image

        try:
            model = args.model or "u2netp"
            print(f"Loading image and initializing model '{model}'...")
            img = load_image(input_path, ensure_rgba=True)
            cutout, _ = remove_background(img, model_name=model)

            out_path = input_path.parent / f"{input_path.stem}_cutout.png"
            export_image(cutout, out_path, format_name="PNG")
            print(f"SUCCESS: Cutout saved to -> {out_path}")
            return 0
        except Exception as exc:
            print(f"ERROR: Smoke test failed: {exc}", file=sys.stderr)
            return 1

    # 2. Headless Server Mode
    if args.server_only:
        import uvicorn
        from pixelcut_local.server.app import create_app
        from pixelcut_local.server.network_utils import get_lan_ip

        settings = Settings.load()
        host = args.host or ("0.0.0.0" if args.lan else settings.server_host)
        port = args.port or settings.server_port

        lan_ip = get_lan_ip()
        print(f"[{__app_name__}] Starting FastAPI server on http://{host}:{port}")
        if args.lan and lan_ip:
            print(f"[{__app_name__}] Mobile devices can connect via: http://{lan_ip}:{port}")
        if settings.pairing_token:
            print(f"[{__app_name__}] LAN Pairing PIN: {settings.pairing_token}")

        app = create_app()
        uvicorn.run(app, host=host, port=port, log_level="info")
        return 0

    # 3. Default: Desktop GUI Mode
    from pixelcut_local.desktop.app import run_desktop_app
    return run_desktop_app()


if __name__ == "__main__":
    sys.exit(main())
