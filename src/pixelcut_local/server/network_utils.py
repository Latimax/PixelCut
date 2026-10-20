"""Network utility functions for LAN IP discovery, port checks, and QR codes."""

from __future__ import annotations

import io
import logging
import socket
from typing import Optional
import qrcode

logger = logging.getLogger(__name__)


def get_lan_ip() -> Optional[str]:
    """Discover the local network IPv4 address of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually establish connection or send data
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        return ip
    except Exception as exc:
        logger.debug("Could not determine LAN IP via UDP socket: %s", exc)
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return None
    finally:
        s.close()


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check whether a TCP port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        res = s.connect_ex((host, port))
        return res == 0


def generate_qr_code_image(data: str) -> bytes:
    """Generate a PNG QR code for a URL (without secret tokens)."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
