"""Server configuration, LAN pairing, QR code display, and controls dialog."""

from __future__ import annotations

import logging
from typing import Optional
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pixelcut_local.config import Settings
from pixelcut_local.server.network_utils import generate_qr_code_image, get_lan_ip
from pixelcut_local.server.server_manager import global_server_manager

logger = logging.getLogger(__name__)


class ServerDialog(QDialog):
    """Server control dialog with LAN pairing token, QR code, and firewall notices."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Mobile Web Server & LAN Settings")
        self.setMinimumWidth(480)
        self.settings = Settings.load()
        self._init_ui()
        self._refresh_server_status()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Host Mode Configuration
        host_group = QGroupBox("Network Binding Mode")
        hg_layout = QVBoxLayout(host_group)

        self.radio_localhost = QRadioButton("Localhost Only (127.0.0.1) — Recommended for local use")
        self.radio_lan = QRadioButton("Local Network (0.0.0.0) — Allow phones/tablets on same Wi-Fi")

        self.host_mode_group = QButtonGroup(self)
        self.host_mode_group.addButton(self.radio_localhost)
        self.host_mode_group.addButton(self.radio_lan)
        hg_layout.addWidget(self.radio_localhost)
        hg_layout.addWidget(self.radio_lan)

        if self.settings.lan_mode_enabled:
            self.radio_lan.setChecked(True)
        else:
            self.radio_localhost.setChecked(True)

        self.radio_lan.toggled.connect(self._on_lan_mode_toggled)
        layout.addWidget(host_group)

        # Firewall Warning Callout (visible in LAN mode)
        self.warning_box = QGroupBox("⚠️ Privacy & Firewall Warning")
        self.warning_box.setStyleSheet("QGroupBox { border: 1px solid #f59e0b; font-weight: bold; }")
        wb_layout = QVBoxLayout(self.warning_box)
        warn_text = QLabel(
            "Local Network mode allows any device on your trusted Wi-Fi to reach the server. "
            "To protect your privacy, a Pairing PIN is required for connection. "
            "Never connect on untrusted public Wi-Fi or configure router port forwarding."
        )
        warn_text.setWordWrap(True)
        wb_layout.addWidget(warn_text)
        layout.addWidget(self.warning_box)
        self.warning_box.setVisible(self.radio_lan.isChecked())

        # Port Configuration
        port_group = QGroupBox("Port Configuration")
        pg_layout = QFormLayout(port_group)

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(self.settings.server_port)
        pg_layout.addRow("TCP Port:", self.spin_port)
        layout.addWidget(port_group)

        # Server Control Buttons (Start / Stop)
        ctrl_h = QHBoxLayout()
        self.btn_toggle_server = QPushButton("Start Server")
        self.btn_toggle_server.setStyleSheet(
            "background: #6366f1; color: white; font-weight: bold; padding: 10px; border-radius: 6px;"
        )
        self.btn_toggle_server.clicked.connect(self._toggle_server)

        self.btn_open_browser = QPushButton("Open in Browser")
        self.btn_open_browser.setEnabled(False)
        self.btn_open_browser.clicked.connect(self._open_in_browser)

        ctrl_h.addWidget(self.btn_toggle_server)
        ctrl_h.addWidget(self.btn_open_browser)
        layout.addLayout(ctrl_h)

        # Connection Information & QR Code Area
        self.info_group = QGroupBox("Mobile Connection Info")
        info_layout = QVBoxLayout(self.info_group)

        self.lbl_server_status = QLabel("Server Status: Stopped")
        self.lbl_server_status.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.lbl_server_status)

        url_h = QHBoxLayout()
        self.lbl_server_url = QLabel("URL: http://127.0.0.1:8765")
        btn_copy_url = QPushButton("Copy URL")
        btn_copy_url.clicked.connect(self._copy_url)
        url_h.addWidget(self.lbl_server_url)
        url_h.addWidget(btn_copy_url)
        info_layout.addLayout(url_h)

        # LAN Pairing Token Display
        token_h = QHBoxLayout()
        self.lbl_token_title = QLabel("Pairing PIN:")
        self.edit_token = QLineEdit()
        self.edit_token.setReadOnly(True)
        btn_copy_token = QPushButton("Copy PIN")
        btn_copy_token.clicked.connect(self._copy_token)
        token_h.addWidget(self.lbl_token_title)
        token_h.addWidget(self.edit_token)
        token_h.addWidget(btn_copy_token)
        info_layout.addLayout(token_h)

        # QR Code Display
        self.lbl_qr_code = QLabel()
        self.lbl_qr_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr_code.setMinimumHeight(150)
        info_layout.addWidget(self.lbl_qr_code)

        layout.addWidget(self.info_group)

    def _on_lan_mode_toggled(self, checked: bool) -> None:
        self.warning_box.setVisible(checked)

    def _toggle_server(self) -> None:
        mgr = global_server_manager
        if mgr.is_running:
            mgr.stop_server()
            self._refresh_server_status()
        else:
            lan = self.radio_lan.isChecked()
            port = self.spin_port.value()
            try:
                mgr.start_server(lan_mode=lan, port=port)
                self._refresh_server_status()
            except Exception as exc:
                logger.error("Failed to start server: %s", exc)
                QMessageBox.critical(self, "Server Startup Error", str(exc))

    def _refresh_server_status(self) -> None:
        mgr = global_server_manager
        if mgr.is_running:
            self.btn_toggle_server.setText("Stop Server")
            self.btn_toggle_server.setStyleSheet(
                "background: #ef4444; color: white; font-weight: bold; padding: 10px; border-radius: 6px;"
            )
            self.btn_open_browser.setEnabled(True)
            self.spin_port.setEnabled(False)
            self.radio_localhost.setEnabled(False)
            self.radio_lan.setEnabled(False)

            lan_url = mgr.get_status().get("lan_url")
            localhost_url = mgr.get_status().get("localhost_url")
            active_url = lan_url if (mgr.lan_mode and lan_url) else localhost_url

            self.lbl_server_status.setText(f"Server Status: Running ({mgr.active_host}:{mgr.active_port})")
            self.lbl_server_url.setText(f"URL: {active_url}")
            self.edit_token.setText(mgr.pairing_token)

            # Generate QR Code image (URL only, no token in QR)
            if active_url:
                qr_bytes = generate_qr_code_image(active_url)
                qimg = QImage.fromData(qr_bytes)
                self.lbl_qr_code.setPixmap(QPixmap.fromImage(qimg).scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            self.btn_toggle_server.setText("Start Server")
            self.btn_toggle_server.setStyleSheet(
                "background: #6366f1; color: white; font-weight: bold; padding: 10px; border-radius: 6px;"
            )
            self.btn_open_browser.setEnabled(False)
            self.spin_port.setEnabled(True)
            self.radio_localhost.setEnabled(True)
            self.radio_lan.setEnabled(True)
            self.lbl_server_status.setText("Server Status: Stopped")
            self.lbl_qr_code.setPixmap(QPixmap())

    def _copy_url(self) -> None:
        url = self.lbl_server_url.text().replace("URL: ", "").strip()
        if url:
            QGuiApplication.clipboard().setText(url)
            QMessageBox.information(self, "Copied", "Server URL copied to clipboard.")

    def _copy_token(self) -> None:
        pin = self.edit_token.text().strip()
        if pin:
            QGuiApplication.clipboard().setText(pin)
            QMessageBox.information(self, "Copied", "Pairing PIN copied to clipboard.")

    def _open_in_browser(self) -> None:
        import webbrowser
        mgr = global_server_manager
        url = mgr.get_status().get("localhost_url", "http://127.0.0.1:8765")
        webbrowser.open(url)
