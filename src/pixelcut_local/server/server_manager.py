"""Server manager for running Uvicorn asynchronously in a background thread."""

from __future__ import annotations

import logging
import secrets
import threading
import time
from typing import Optional
import uvicorn

from pixelcut_local.config import Settings
from pixelcut_local.server.app import create_app
from pixelcut_local.server.network_utils import get_lan_ip, is_port_in_use

logger = logging.getLogger(__name__)


class ServerManager:
    """Manages the background FastAPI/Uvicorn server lifecycle."""

    def __init__(self):
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.is_running: bool = False
        self.active_host: str = "127.0.0.1"
        self.active_port: int = 8765
        self.lan_mode: bool = False
        self.pairing_token: str = ""

    def start_server(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        lan_mode: Optional[bool] = None,
        pairing_token: Optional[str] = None,
    ) -> dict:
        """Start local web server.

        Validates port, applies LAN mode settings, and launches Uvicorn in a background thread.
        """
        with self._lock:
            if self.is_running:
                return self.get_status()

            settings = Settings.load()

            self.lan_mode = lan_mode if lan_mode is not None else settings.lan_mode_enabled
            self.active_port = port if port is not None else settings.server_port

            # Check port validity
            if self.active_port < 1024 or self.active_port > 65535:
                raise ValueError(f"Port {self.active_port} is outside valid unprivileged range (1024-65535).")

            # Determine host binding
            if self.lan_mode:
                self.active_host = "0.0.0.0"
                # Generate or load pairing PIN (6-digit alphanumeric or user token)
                if pairing_token:
                    self.pairing_token = pairing_token
                elif settings.pairing_token:
                    self.pairing_token = settings.pairing_token
                else:
                    self.pairing_token = secrets.token_hex(3).upper()  # e.g. "A3F19B"
                settings.pairing_token = self.pairing_token
                settings.lan_mode_enabled = True
            else:
                self.active_host = "127.0.0.1"
                self.pairing_token = ""
                settings.lan_mode_enabled = False

            settings.server_host = self.active_host
            settings.server_port = self.active_port
            settings.save()

            # Check if port is already occupied
            if is_port_in_use(self.active_port, "127.0.0.1"):
                raise RuntimeError(
                    f"Port {self.active_port} is already in use by another application. "
                    "Please choose a different port in Settings."
                )

            # Build FastAPI application
            app = create_app()

            config = uvicorn.Config(
                app=app,
                host=self.active_host,
                port=self.active_port,
                log_level="warning",
                access_log=False,
            )
            self._server = uvicorn.Server(config)

            def run():
                try:
                    self._server.run()
                except Exception as exc:
                    logger.error("Uvicorn server crashed: %s", exc)
                finally:
                    self.is_running = False

            self._thread = threading.Thread(target=run, daemon=True, name="PixelCutServerThread")
            self._thread.start()

            # Wait briefly to confirm startup
            for _ in range(10):
                time.sleep(0.1)
                if self._server.started:
                    break

            self.is_running = True
            logger.info("PixelCut Local server started at http://%s:%d", self.active_host, self.active_port)
            return self.get_status()

    def stop_server(self) -> dict:
        """Stop running Uvicorn server gracefully."""
        with self._lock:
            if not self.is_running or not self._server:
                self.is_running = False
                return self.get_status()

            logger.info("Stopping PixelCut Local server...")
            self._server.should_exit = True
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)

            self.is_running = False
            self._server = None
            self._thread = None
            logger.info("PixelCut Local server stopped successfully.")
            return self.get_status()

    def get_status(self) -> dict:
        """Get current server status and reachable URLs."""
        lan_ip = get_lan_ip()
        return {
            "is_running": self.is_running,
            "host": self.active_host,
            "port": self.active_port,
            "lan_mode": self.lan_mode,
            "pairing_token": self.pairing_token if self.lan_mode else "",
            "localhost_url": f"http://127.0.0.1:{self.active_port}",
            "lan_url": f"http://{lan_ip}:{self.active_port}" if (self.lan_mode and lan_ip) else None,
            "lan_ip": lan_ip,
        }


# Global server manager singleton
global_server_manager = ServerManager()
