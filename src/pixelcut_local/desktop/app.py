"""Desktop application runner and modern Qt styling."""

from __future__ import annotations

import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QApplication

from pixelcut_local import __app_name__, __version__
from pixelcut_local.desktop.main_window import MainWindow

DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #0b0f19;
    color: #f8fafc;
}

QWidget {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    color: #e2e8f0;
}

QToolBar {
    background-color: #131b2e;
    border-bottom: 1px solid #1e293b;
    padding: 6px;
    spacing: 8px;
}

QToolButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #2e3c54;
    border-color: #6366f1;
}

QToolButton:pressed, QToolButton:checked {
    background-color: #4f46e5;
    color: white;
    border-color: #6366f1;
}

QGroupBox {
    border: 1px solid #1e293b;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: 600;
    padding-top: 14px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #a5b4fc;
}

QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    color: #f8fafc;
}

QPushButton:hover {
    background-color: #2d3b55;
    border-color: #6366f1;
}

QPushButton:disabled {
    background-color: #0f172a;
    color: #64748b;
    border-color: #1e293b;
}

QLineEdit, QSpinBox, QComboBox {
    background-color: #131b2e;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #6366f1;
}

QListWidget {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    border-radius: 6px;
    padding: 8px;
    margin: 3px 0;
    background-color: #131b2e;
}

QListWidget::item:selected {
    background-color: rgba(99, 102, 241, 0.25);
    border: 1px solid #6366f1;
    color: #ffffff;
}

QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 8px;
    background-color: #0f172a;
}

QTabBar::tab {
    background-color: #131b2e;
    border: 1px solid #1e293b;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 14px;
    margin-right: 2px;
    color: #94a3b8;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #1e293b;
    color: #f8fafc;
    border-color: #6366f1;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #6366f1;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #6366f1;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QStatusBar {
    background-color: #131b2e;
    border-top: 1px solid #1e293b;
    color: #94a3b8;
}

QProgressBar {
    background-color: #1e293b;
    border-radius: 4px;
    text-align: center;
    color: white;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: #6366f1;
    border-radius: 4px;
}
"""


def run_desktop_app() -> int:
    """Initialize and run the PySide6 desktop application."""
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("PixelCut")
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    return app.exec()
