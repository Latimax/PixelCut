"""Diagnostics dialog reporting runtime environment, provider status, and log folder access."""

from __future__ import annotations

import logging
import os
import platform
import sys
from typing import Optional
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pixelcut_local import __app_name__, __version__
from pixelcut_local.config import Settings
from pixelcut_local.core.models import (
    get_available_execution_providers,
    is_gpu_available,
    is_model_downloaded,
)
from pixelcut_local.server.server_manager import global_server_manager
from pixelcut_local.storage.paths import (
    get_logs_dir,
    get_models_dir,
    get_temp_jobs_dir,
    get_user_data_dir,
    is_frozen,
)

logger = logging.getLogger(__name__)


class DiagnosticsDialog(QDialog):
    """System diagnostics dialog for troubleshooting and verification."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("System Diagnostics & Telemetry")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        settings = Settings.load()

        # System & Runtime
        sys_group = QGroupBox("Runtime & Platform")
        sg_layout = QFormLayout(sys_group)
        sg_layout.addRow("Application:", QLabel(f"{__app_name__} v{__version__}"))
        mode_str = "PyInstaller Frozen Executable" if is_frozen() else "Python Source Mode"
        sg_layout.addRow("Execution Mode:", QLabel(mode_str))
        sg_layout.addRow("Operating System:", QLabel(f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"))
        sg_layout.addRow("Python Version:", QLabel(f"{sys.version.split()[0]} ({sys.executable})"))
        layout.addWidget(sys_group)

        # AI Engine & Acceleration
        ai_group = QGroupBox("AI Engine & Providers")
        ai_layout = QFormLayout(ai_group)
        ai_layout.addRow("Default Model:", QLabel(settings.model_name))
        is_dl = is_model_downloaded(settings.model_name)
        status_color = "#10b981" if is_dl else "#f59e0b"
        status_text = "Weights Cached Locally" if is_dl else "Requires 1st-Run Download"
        lbl_status = QLabel(f"<span style='color:{status_color}; font-weight:bold;'>{status_text}</span>")
        ai_layout.addRow("Model Status:", lbl_status)

        providers = get_available_execution_providers()
        ai_layout.addRow("ONNX Providers:", QLabel(", ".join(providers)))
        gpu_str = "Enabled" if is_gpu_available() else "Not Detected (CPU Fallback Active)"
        ai_layout.addRow("Hardware Acceleration:", QLabel(gpu_str))
        layout.addWidget(ai_group)

        # Storage & Permissions
        stor_group = QGroupBox("Storage & Paths")
        st_layout = QFormLayout(stor_group)

        app_data = get_user_data_dir()
        writable = os.access(app_data, os.W_OK)
        w_color = "#10b981" if writable else "#ef4444"
        st_layout.addRow("User AppData:", QLabel(f"{app_data} (<span style='color:{w_color};'>Writable</span>)"))
        st_layout.addRow("Model Storage:", QLabel(str(get_models_dir())))
        st_layout.addRow("Temporary Storage:", QLabel(str(get_temp_jobs_dir())))
        layout.addWidget(stor_group)

        # Server State
        srv_mgr = global_server_manager
        srv_group = QGroupBox("Web Server Status")
        srv_layout = QFormLayout(srv_group)
        srv_status = "Running" if srv_mgr.is_running else "Stopped"
        srv_layout.addRow("Status:", QLabel(srv_status))
        if srv_mgr.is_running:
            srv_layout.addRow("Binding:", QLabel(f"{srv_mgr.active_host}:{srv_mgr.active_port}"))
            srv_layout.addRow("LAN Mode:", QLabel(str(srv_mgr.lan_mode)))
        layout.addWidget(srv_group)

        # Log Actions
        actions_h = QHBoxLayout()
        btn_open_logs = QPushButton("📁 Open Logs Folder")
        btn_open_logs.clicked.connect(self._open_logs_folder)
        actions_h.addWidget(btn_open_logs)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        actions_h.addWidget(btn_close)
        layout.addLayout(actions_h)

    def _open_logs_folder(self) -> None:
        logs_path = get_logs_dir()
        if platform.system() == "Windows":
            os.startfile(str(logs_path))
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(logs_path)])
