"""Application settings dialog for model choice, quality modes, and resource limits."""

from __future__ import annotations

import logging
from typing import Optional
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pixelcut_local.config import Settings
from pixelcut_local.core.background_removal import clear_session_cache
from pixelcut_local.core.models import (
    MODEL_REGISTRY,
    is_gpu_available,
    is_model_downloaded,
)
from pixelcut_local.storage.cleanup import clear_all_temporary_files

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Settings dialog managing AI models, inference options, and hardware limits."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("PixelCut Local Settings")
        self.setMinimumWidth(460)
        self.settings = Settings.load()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # AI Model Settings
        model_group = QGroupBox("AI Model & Quality")
        mg_layout = QFormLayout(model_group)

        self.combo_model = QComboBox()
        for m_id, info in MODEL_REGISTRY.items():
            status_text = "Downloaded" if is_model_downloaded(m_id) else f"~{info.approx_size_mb}MB on 1st run"
            self.combo_model.addItem(f"{info.name} ({status_text})", m_id)

        # Select current model
        idx = self.combo_model.findData(self.settings.model_name)
        if idx >= 0:
            self.combo_model.setCurrentIndex(idx)
        self.combo_model.currentIndexChanged.connect(self._on_model_changed)
        mg_layout.addRow("Inference Model:", self.combo_model)

        # License notice display
        self.lbl_license_notice = QLabel()
        self.lbl_license_notice.setWordWrap(True)
        self.lbl_license_notice.setStyleSheet("color: #94a3b8; font-size: 11px;")
        mg_layout.addRow("License Terms:", self.lbl_license_notice)
        self._update_license_display()

        self.chk_matting = QCheckBox("Enable Alpha Matting (Refines hair/fur boundaries)")
        self.chk_matting.setChecked(self.settings.use_alpha_matting)
        mg_layout.addRow("", self.chk_matting)

        gpu_ok = is_gpu_available()
        gpu_status_str = " (Hardware GPU Detected)" if gpu_ok else " (CPU Only on this system)"
        self.chk_gpu = QCheckBox(f"Prefer GPU Acceleration{gpu_status_str}")
        self.chk_gpu.setChecked(self.settings.prefer_gpu and gpu_ok)
        self.chk_gpu.setEnabled(gpu_ok)
        mg_layout.addRow("", self.chk_gpu)

        layout.addWidget(model_group)

        # Safety & Resource Limits
        limits_group = QGroupBox("Safety & Resource Limits")
        lg_layout = QFormLayout(limits_group)

        self.spin_upload_mb = QSpinBox()
        self.spin_upload_mb.setRange(5, 100)
        self.spin_upload_mb.setValue(self.settings.max_upload_mb)
        lg_layout.addRow("Max File Size (MB):", self.spin_upload_mb)

        self.spin_megapixels = QSpinBox()
        self.spin_megapixels.setRange(10, 100)
        self.spin_megapixels.setValue(self.settings.max_megapixels)
        lg_layout.addRow("Max Megapixels:", self.spin_megapixels)

        self.spin_concurrency = QSpinBox()
        self.spin_concurrency.setRange(1, 4)
        self.spin_concurrency.setValue(self.settings.max_concurrent_jobs)
        lg_layout.addRow("Max Concurrent Jobs:", self.spin_concurrency)

        layout.addWidget(limits_group)

        # Cache & Maintenance
        maint_group = QGroupBox("Storage & Maintenance")
        maint_layout = QHBoxLayout(maint_group)

        btn_clear_cache = QPushButton("Clear Temporary Files")
        btn_clear_cache.clicked.connect(self._clear_cache)
        maint_layout.addWidget(btn_clear_cache)

        btn_clear_models = QPushButton("Reset Model Sessions")
        btn_clear_models.clicked.connect(self._clear_sessions)
        maint_layout.addWidget(btn_clear_models)

        layout.addWidget(maint_group)

        # Save / Cancel Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_save = QPushButton("Save Settings")
        btn_save.setStyleSheet("background: #6366f1; color: white; font-weight: bold; padding: 6px 16px;")
        btn_save.clicked.connect(self._save_and_close)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _on_model_changed(self) -> None:
        self._update_license_display()

    def _update_license_display(self) -> None:
        m_id = self.combo_model.currentData()
        info = MODEL_REGISTRY.get(m_id)
        if info:
            color = "#10b981" if info.commercial_cleared else "#f59e0b"
            self.lbl_license_notice.setText(
                f"<span style='color:{color}; font-weight:bold;'>[{info.license_type}]</span> {info.license_notice}"
            )

    def _clear_cache(self) -> None:
        count = clear_all_temporary_files()
        QMessageBox.information(self, "Cache Cleared", f"Removed {count} temporary job directory(ies).")

    def _clear_sessions(self) -> None:
        clear_session_cache()
        QMessageBox.information(self, "Sessions Cleared", "Model inference session cache has been reset.")

    def _save_and_close(self) -> None:
        self.settings.model_name = self.combo_model.currentData()
        self.settings.use_alpha_matting = self.chk_matting.isChecked()
        self.settings.prefer_gpu = self.chk_gpu.isChecked()
        self.settings.max_upload_mb = self.spin_upload_mb.value()
        self.settings.max_megapixels = self.spin_megapixels.value()
        self.settings.max_concurrent_jobs = self.spin_concurrency.value()
        self.settings.save()
        self.accept()
