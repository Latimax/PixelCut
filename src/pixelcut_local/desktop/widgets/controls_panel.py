"""Right control sidebar containing Background, Composition, Mask Refinement, and Export settings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pixelcut_local.config import Settings
from pixelcut_local.core.constants import CANVAS_PRESETS, EXPORT_FORMATS, FIT_MODES
from pixelcut_local.storage.paths import get_default_export_dir

logger = logging.getLogger(__name__)


class ControlsPanel(QWidget):
    """Right sidebar panel with tabs for Background, Composition, Mask Refinement, and Export."""

    composition_changed = Signal()
    brush_mode_changed = Signal(str, int)  # (mode, radius)
    mask_action_triggered = Signal(str)  # action name: "feather", "smooth", "expand", "shrink", "reset", "undo", "redo"
    mask_overlay_toggled = Signal(bool)
    request_export_current = Signal()
    request_export_batch = Signal(bool)  # as_zip: bool

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings = Settings.load()
        self.bg_image_path: Optional[str] = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._build_background_tab(), "Background")
        self.tab_widget.addTab(self._build_composition_tab(), "Composition")
        self.tab_widget.addTab(self._build_refinement_tab(), "Refine Mask")
        self.tab_widget.addTab(self._build_export_tab(), "Export")

        main_layout.addWidget(self.tab_widget)

    # -------------------------------------------------------------
    # 1. Background Tab
    # -------------------------------------------------------------
    def _build_background_tab(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        # Mode Selection
        mode_group = QGroupBox("Background Mode")
        mode_layout = QVBoxLayout(mode_group)
        self.radio_bg_trans = QRadioButton("Transparent (PNG / Alpha)")
        self.radio_bg_trans.setChecked(True)
        self.radio_bg_solid = QRadioButton("Solid Color")
        self.radio_bg_grad = QRadioButton("Linear Gradient")
        self.radio_bg_img = QRadioButton("Image Background")

        self.bg_button_group = QButtonGroup(self)
        for r in (self.radio_bg_trans, self.radio_bg_solid, self.radio_bg_grad, self.radio_bg_img):
            self.bg_button_group.addButton(r)
            mode_layout.addWidget(r)
            r.toggled.connect(self._on_bg_mode_toggled)

        layout.addWidget(mode_group)

        # Solid Color Controls
        self.solid_box = QGroupBox("Solid Color")
        solid_layout = QHBoxLayout(self.solid_box)
        self.btn_solid_color = QPushButton("Pick Color")
        self.btn_solid_color.setStyleSheet("background-color: #ffffff; color: black; font-weight: bold;")
        self.btn_solid_color.clicked.connect(self._pick_solid_color)
        self.lbl_solid_hex = QLabel("#FFFFFF")
        solid_layout.addWidget(self.btn_solid_color)
        solid_layout.addWidget(self.lbl_solid_hex)
        layout.addWidget(self.solid_box)
        self.solid_box.hide()

        # Gradient Controls
        self.grad_box = QGroupBox("Gradient Colors & Angle")
        grad_layout = QFormLayout(self.grad_box)
        self.btn_grad_c1 = QPushButton("Color 1")
        self.btn_grad_c1.setStyleSheet("background-color: #6366f1; color: white;")
        self.btn_grad_c1.clicked.connect(lambda: self._pick_gradient_color(1))
        self.c1_val = (99, 102, 241)

        self.btn_grad_c2 = QPushButton("Color 2")
        self.btn_grad_c2.setStyleSheet("background-color: #a855f7; color: white;")
        self.btn_grad_c2.clicked.connect(lambda: self._pick_gradient_color(2))
        self.c2_val = (168, 85, 247)

        colors_h = QHBoxLayout()
        colors_h.addWidget(self.btn_grad_c1)
        colors_h.addWidget(self.btn_grad_c2)
        grad_layout.addRow("Colors:", colors_h)

        self.slider_grad_angle = QSlider(Qt.Orientation.Horizontal)
        self.slider_grad_angle.setRange(0, 360)
        self.slider_grad_angle.setValue(45)
        self.slider_grad_angle.valueChanged.connect(lambda: self.composition_changed.emit())
        grad_layout.addRow("Angle (deg):", self.slider_grad_angle)

        layout.addWidget(self.grad_box)
        self.grad_box.hide()

        # Image Background Controls
        self.img_bg_box = QGroupBox("Custom Background Image")
        img_bg_layout = QFormLayout(self.img_bg_box)

        self.btn_choose_bg_img = QPushButton("Browse Image...")
        self.btn_choose_bg_img.clicked.connect(self._browse_bg_image)
        self.lbl_bg_img_name = QLabel("No image selected")
        img_bg_layout.addRow(self.btn_choose_bg_img, self.lbl_bg_img_name)

        self.combo_bg_fit = QComboBox()
        self.combo_bg_fit.addItems(["cover", "contain", "stretch"])
        self.combo_bg_fit.currentIndexChanged.connect(lambda: self.composition_changed.emit())
        img_bg_layout.addRow("Fit Mode:", self.combo_bg_fit)

        self.slider_bg_blur = QSlider(Qt.Orientation.Horizontal)
        self.slider_bg_blur.setRange(0, 30)
        self.slider_bg_blur.setValue(0)
        self.slider_bg_blur.valueChanged.connect(lambda: self.composition_changed.emit())
        img_bg_layout.addRow("Blur:", self.slider_bg_blur)

        self.slider_bg_bright = QSlider(Qt.Orientation.Horizontal)
        self.slider_bg_bright.setRange(20, 200)  # 0.2 to 2.0
        self.slider_bg_bright.setValue(100)
        self.slider_bg_bright.valueChanged.connect(lambda: self.composition_changed.emit())
        img_bg_layout.addRow("Brightness:", self.slider_bg_bright)

        layout.addWidget(self.img_bg_box)
        self.img_bg_box.hide()

        layout.addStretch()
        scroll.setWidget(content)
        outer_layout = QVBoxLayout(widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return widget

    def _on_bg_mode_toggled(self) -> None:
        self.solid_box.setVisible(self.radio_bg_solid.isChecked())
        self.grad_box.setVisible(self.radio_bg_grad.isChecked())
        self.img_bg_box.setVisible(self.radio_bg_img.isChecked())
        self.composition_changed.emit()

    def _pick_solid_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.lbl_solid_hex.text()), self)
        if color.isValid():
            hex_str = color.name().upper()
            self.lbl_solid_hex.setText(hex_str)
            text_color = "black" if color.lightness() > 128 else "white"
            self.btn_solid_color.setStyleSheet(f"background-color: {hex_str}; color: {text_color}; font-weight: bold;")
            self.composition_changed.emit()

    def _pick_gradient_color(self, index: int) -> None:
        init_c = QColor(*self.c1_val) if index == 1 else QColor(*self.c2_val)
        color = QColorDialog.getColor(init_c, self)
        if color.isValid():
            rgb = (color.red(), color.green(), color.blue())
            if index == 1:
                self.c1_val = rgb
                self.btn_grad_c1.setStyleSheet(f"background-color: {color.name()}; color: white;")
            else:
                self.c2_val = rgb
                self.btn_grad_c2.setStyleSheet(f"background-color: {color.name()}; color: white;")
            self.composition_changed.emit()

    def _browse_bg_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Image",
            "",
            "Image Files (*.jpg *.jpeg *.png *.webp *.bmp)",
        )
        if file_path:
            self.bg_image_path = file_path
            self.lbl_bg_img_name.setText(Path(file_path).name)
            self.composition_changed.emit()

    # -------------------------------------------------------------
    # 2. Composition Tab
    # -------------------------------------------------------------
    def _build_composition_tab(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        # Canvas Presets
        canvas_group = QGroupBox("Canvas Aspect Ratio")
        canvas_layout = QFormLayout(canvas_group)
        self.combo_canvas_preset = QComboBox()
        self.combo_canvas_preset.addItems(list(CANVAS_PRESETS.keys()))
        self.combo_canvas_preset.currentIndexChanged.connect(lambda: self.composition_changed.emit())
        canvas_layout.addRow("Preset:", self.combo_canvas_preset)
        layout.addWidget(canvas_group)

        # Foreground Transform
        fg_group = QGroupBox("Subject Positioning & Scale")
        fg_layout = QFormLayout(fg_group)

        self.slider_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_scale.setRange(20, 300)  # 0.2 to 3.0
        self.slider_scale.setValue(100)
        self.slider_scale.valueChanged.connect(lambda: self.composition_changed.emit())
        fg_layout.addRow("Scale (%):", self.slider_scale)

        self.slider_pos_x = QSlider(Qt.Orientation.Horizontal)
        self.slider_pos_x.setRange(-400, 400)
        self.slider_pos_x.setValue(0)
        self.slider_pos_x.valueChanged.connect(lambda: self.composition_changed.emit())
        fg_layout.addRow("Position X:", self.slider_pos_x)

        self.slider_pos_y = QSlider(Qt.Orientation.Horizontal)
        self.slider_pos_y.setRange(-400, 400)
        self.slider_pos_y.setValue(0)
        self.slider_pos_y.valueChanged.connect(lambda: self.composition_changed.emit())
        fg_layout.addRow("Position Y:", self.slider_pos_y)

        self.slider_rotation = QSlider(Qt.Orientation.Horizontal)
        self.slider_rotation.setRange(-180, 180)
        self.slider_rotation.setValue(0)
        self.slider_rotation.valueChanged.connect(lambda: self.composition_changed.emit())
        fg_layout.addRow("Rotation (°):", self.slider_rotation)

        self.slider_padding = QSlider(Qt.Orientation.Horizontal)
        self.slider_padding.setRange(0, 100)
        self.slider_padding.setValue(0)
        self.slider_padding.valueChanged.connect(lambda: self.composition_changed.emit())
        fg_layout.addRow("Padding (px):", self.slider_padding)

        layout.addWidget(fg_group)

        # Effects: Drop Shadow & Outline
        fx_group = QGroupBox("Visual Effects")
        fx_layout = QFormLayout(fx_group)

        self.chk_shadow = QCheckBox("Enable Drop Shadow")
        self.chk_shadow.toggled.connect(lambda: self.composition_changed.emit())
        self.slider_shadow_intensity = QSlider(Qt.Orientation.Horizontal)
        self.slider_shadow_intensity.setRange(10, 100)
        self.slider_shadow_intensity.setValue(50)
        self.slider_shadow_intensity.valueChanged.connect(lambda: self.composition_changed.emit())
        fx_layout.addRow(self.chk_shadow, self.slider_shadow_intensity)

        self.chk_outline = QCheckBox("Enable Sticker Outline")
        self.chk_outline.toggled.connect(lambda: self.composition_changed.emit())
        self.spin_outline_width = QSpinBox()
        self.spin_outline_width.setRange(1, 40)
        self.spin_outline_width.setValue(6)
        self.spin_outline_width.valueChanged.connect(lambda: self.composition_changed.emit())
        fx_layout.addRow(self.chk_outline, self.spin_outline_width)

        layout.addWidget(fx_group)

        # Reset button
        self.btn_reset_comp = QPushButton("Reset Composition Defaults")
        self.btn_reset_comp.clicked.connect(self._reset_composition_defaults)
        layout.addWidget(self.btn_reset_comp)

        layout.addStretch()
        scroll.setWidget(content)
        outer_layout = QVBoxLayout(widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return widget

    def _reset_composition_defaults(self) -> None:
        self.combo_canvas_preset.setCurrentIndex(0)
        self.slider_scale.setValue(100)
        self.slider_pos_x.setValue(0)
        self.slider_pos_y.setValue(0)
        self.slider_rotation.setValue(0)
        self.slider_padding.setValue(0)
        self.chk_shadow.setChecked(False)
        self.chk_outline.setChecked(False)
        self.composition_changed.emit()

    # -------------------------------------------------------------
    # 3. Mask Refinement Tab
    # -------------------------------------------------------------
    def _build_refinement_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # Interactive Brush Tool Mode
        brush_group = QGroupBox("Interactive Brush Tool")
        bg_brush = QVBoxLayout(brush_group)

        self.radio_brush_none = QRadioButton("Normal View (Brush Off)")
        self.radio_brush_none.setChecked(True)
        self.radio_brush_keep = QRadioButton("Paint to Keep (Foreground)")
        self.radio_brush_keep.setStyleSheet("color: #10b981; font-weight: 600;")
        self.radio_brush_remove = QRadioButton("Paint to Remove (Background)")
        self.radio_brush_remove.setStyleSheet("color: #ef4444; font-weight: 600;")

        self.brush_group_btn = QButtonGroup(self)
        for r in (self.radio_brush_none, self.radio_brush_keep, self.radio_brush_remove):
            self.brush_group_btn.addButton(r)
            bg_brush.addWidget(r)
            r.toggled.connect(self._on_brush_mode_toggled)

        # Brush Radius
        radius_h = QHBoxLayout()
        radius_h.addWidget(QLabel("Brush Size:"))
        self.slider_brush_radius = QSlider(Qt.Orientation.Horizontal)
        self.slider_brush_radius.setRange(2, 100)
        self.slider_brush_radius.setValue(20)
        self.lbl_brush_radius = QLabel("20 px")
        self.slider_brush_radius.valueChanged.connect(self._on_brush_radius_changed)
        radius_h.addWidget(self.slider_brush_radius)
        radius_h.addWidget(self.lbl_brush_radius)
        bg_brush.addLayout(radius_h)

        layout.addWidget(brush_group)

        # Edge Filters
        filter_group = QGroupBox("Edge Operations")
        fg_layout = QVBoxLayout(filter_group)

        btn_feather = QPushButton("Feather / Soften Edges")
        btn_feather.clicked.connect(lambda: self.mask_action_triggered.emit("feather"))
        fg_layout.addWidget(btn_feather)

        btn_smooth = QPushButton("Smooth Boundaries")
        btn_smooth.clicked.connect(lambda: self.mask_action_triggered.emit("smooth"))
        fg_layout.addWidget(btn_smooth)

        expand_shrink_h = QHBoxLayout()
        btn_expand = QPushButton("+ Expand Mask")
        btn_expand.clicked.connect(lambda: self.mask_action_triggered.emit("expand"))
        btn_shrink = QPushButton("- Shrink Mask")
        btn_shrink.clicked.connect(lambda: self.mask_action_triggered.emit("shrink"))
        expand_shrink_h.addWidget(btn_expand)
        expand_shrink_h.addWidget(btn_shrink)
        fg_layout.addLayout(expand_shrink_h)

        layout.addWidget(filter_group)

        # Undo / Redo & Overlay
        history_group = QGroupBox("History & Mask Overlay")
        hist_layout = QVBoxLayout(history_group)

        undo_redo_h = QHBoxLayout()
        self.btn_undo = QPushButton("Undo (Ctrl+Z)")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(lambda: self.mask_action_triggered.emit("undo"))

        self.btn_redo = QPushButton("Redo (Ctrl+Y)")
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(lambda: self.mask_action_triggered.emit("redo"))

        undo_redo_h.addWidget(self.btn_undo)
        undo_redo_h.addWidget(self.btn_redo)
        hist_layout.addLayout(undo_redo_h)

        self.chk_mask_overlay = QCheckBox("Show Mask Highlight Overlay (Ruby)")
        self.chk_mask_overlay.toggled.connect(self.mask_overlay_toggled.emit)
        hist_layout.addWidget(self.chk_mask_overlay)

        btn_reset_ai = QPushButton("Reset Mask to AI Result")
        btn_reset_ai.clicked.connect(lambda: self.mask_action_triggered.emit("reset"))
        hist_layout.addWidget(btn_reset_ai)

        layout.addWidget(history_group)
        layout.addStretch()
        return widget

    def _on_brush_mode_toggled(self) -> None:
        if self.radio_brush_keep.isChecked():
            mode = "keep"
        elif self.radio_brush_remove.isChecked():
            mode = "remove"
        else:
            mode = "none"
        self.brush_mode_changed.emit(mode, self.slider_brush_radius.value())

    def _on_brush_radius_changed(self, val: int) -> None:
        self.lbl_brush_radius.setText(f"{val} px")
        self._on_brush_mode_toggled()

    def update_undo_redo_state(self, can_undo: bool, can_redo: bool) -> None:
        self.btn_undo.setEnabled(can_undo)
        self.btn_redo.setEnabled(can_redo)

    # -------------------------------------------------------------
    # 4. Export Tab
    # -------------------------------------------------------------
    def _build_export_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        format_group = QGroupBox("Export Format & Quality")
        fmt_layout = QFormLayout(format_group)

        self.combo_export_fmt = QComboBox()
        self.combo_export_fmt.addItems(EXPORT_FORMATS)
        self.combo_export_fmt.setCurrentText(self.settings.export_format)
        fmt_layout.addRow("Format:", self.combo_export_fmt)

        self.slider_quality = QSlider(Qt.Orientation.Horizontal)
        self.slider_quality.setRange(10, 100)
        self.slider_quality.setValue(self.settings.export_quality)
        self.lbl_quality = QLabel(f"{self.settings.export_quality}%")
        self.slider_quality.valueChanged.connect(lambda v: self.lbl_quality.setText(f"{v}%"))

        qual_h = QHBoxLayout()
        qual_h.addWidget(self.slider_quality)
        qual_h.addWidget(self.lbl_quality)
        fmt_layout.addRow("Quality:", qual_h)

        layout.addWidget(format_group)

        # Output Folder & Naming
        dest_group = QGroupBox("Destination & Naming")
        dest_layout = QFormLayout(dest_group)

        folder_h = QHBoxLayout()
        self.edit_export_dir = QLineEdit(self.settings.default_export_dir)
        btn_browse_dir = QPushButton("Browse...")
        btn_browse_dir.clicked.connect(self._browse_export_dir)
        folder_h.addWidget(self.edit_export_dir)
        folder_h.addWidget(btn_browse_dir)
        dest_layout.addRow("Folder:", folder_h)

        self.edit_naming = QLineEdit(self.settings.naming_template)
        dest_layout.addRow("Template:", self.edit_naming)

        self.combo_overwrite = QComboBox()
        self.combo_overwrite.addItems(["auto_number", "overwrite", "skip"])
        self.combo_overwrite.setCurrentText(self.settings.overwrite_policy)
        dest_layout.addRow("Conflicts:", self.combo_overwrite)

        layout.addWidget(dest_group)

        # Export Action Buttons
        self.btn_export_single = QPushButton("💾 Export Current Image")
        self.btn_export_single.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669); "
            "color: white; font-weight: 700; padding: 10px; border-radius: 6px;"
        )
        self.btn_export_single.clicked.connect(self.request_export_current.emit)
        layout.addWidget(self.btn_export_single)

        batch_exp_h = QHBoxLayout()
        self.btn_export_batch_folder = QPushButton("Batch Export Folder")
        self.btn_export_batch_folder.clicked.connect(lambda: self.request_export_batch.emit(False))
        self.btn_export_zip = QPushButton("Export as ZIP Archive")
        self.btn_export_zip.clicked.connect(lambda: self.request_export_batch.emit(True))
        batch_exp_h.addWidget(self.btn_export_batch_folder)
        batch_exp_h.addWidget(self.btn_export_zip)
        layout.addLayout(batch_exp_h)

        layout.addStretch()
        return widget

    def _browse_export_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Export Directory", self.edit_export_dir.text())
        if folder:
            self.edit_export_dir.setText(folder)

    # -------------------------------------------------------------
    # State Accessors
    # -------------------------------------------------------------
    def get_composition_params(self) -> Dict[str, Any]:
        """Collect all parameters required by composite_image()."""
        bg_mode = "transparent"
        if self.radio_bg_solid.isChecked():
            bg_mode = "solid"
        elif self.radio_bg_grad.isChecked():
            bg_mode = "gradient"
        elif self.radio_bg_img.isChecked():
            bg_mode = "image"

        return {
            "bg_mode": bg_mode,
            "solid_color": self.lbl_solid_hex.text(),
            "gradient_colors": (self.c1_val, self.c2_val),
            "gradient_angle": float(self.slider_grad_angle.value()),
            "bg_image_path": self.bg_image_path,
            "bg_fit_mode": self.combo_bg_fit.currentText(),
            "bg_blur": float(self.slider_bg_blur.value()),
            "bg_brightness": float(self.slider_bg_bright.value() / 100.0),
            "canvas_preset": self.combo_canvas_preset.currentText(),
            "scale": float(self.slider_scale.value() / 100.0),
            "offset_x": self.slider_pos_x.value(),
            "offset_y": self.slider_pos_y.value(),
            "rotation": float(self.slider_rotation.value()),
            "padding": self.slider_padding.value(),
            "enable_shadow": self.chk_shadow.isChecked(),
            "shadow_intensity": float(self.slider_shadow_intensity.value() / 100.0),
            "enable_outline": self.chk_outline.isChecked(),
            "outline_color": (255, 255, 255),
            "outline_width": self.spin_outline_width.value(),
        }

    def get_export_params(self) -> Dict[str, Any]:
        """Collect parameters for export_image()."""
        return {
            "format_name": self.combo_export_fmt.currentText(),
            "quality": self.slider_quality.value(),
            "output_dir": self.edit_export_dir.text().strip(),
            "naming_template": self.edit_naming.text().strip(),
            "overwrite_policy": self.combo_overwrite.currentText(),
        }
