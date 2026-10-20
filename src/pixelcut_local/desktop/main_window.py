"""Main desktop application window for PixelCut Local."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)

from pixelcut_local import __app_name__, __version__
from pixelcut_local.config import Settings
from pixelcut_local.core.composition import composite_image
from pixelcut_local.core.export import export_image, generate_safe_output_path
from pixelcut_local.core.image_io import load_image
from pixelcut_local.core.models import (
    get_available_execution_providers,
    is_gpu_available,
)
from pixelcut_local.desktop.canvas import InteractiveCanvas
from pixelcut_local.desktop.widgets.controls_panel import ControlsPanel
from pixelcut_local.desktop.widgets.diagnostics_dialog import DiagnosticsDialog
from pixelcut_local.desktop.widgets.queue_panel import QueueItemData, QueuePanel
from pixelcut_local.desktop.widgets.server_dialog import ServerDialog
from pixelcut_local.desktop.widgets.settings_dialog import SettingsDialog
from pixelcut_local.desktop.workers import BatchWorker, ExportWorker, InferenceWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window coordinating Queue, Canvas, and Controls."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.resize(1360, 850)
        self.setMinimumSize(900, 600)

        self.settings = Settings.load()
        self.current_worker: Optional[InferenceWorker] = None
        self.batch_worker: Optional[BatchWorker] = None
        self.export_worker: Optional[ExportWorker] = None

        self._init_ui()
        self._init_shortcuts()
        self._update_status_bar("Ready. Drag and drop images or click Open Files to begin.")

    def _init_ui(self) -> None:
        # Central Splitter (Left: Queue, Center: Canvas, Right: Controls)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # 1. Left Queue Panel
        self.queue_panel = QueuePanel(self)
        self.queue_panel.setMinimumWidth(260)
        self.queue_panel.setMaximumWidth(380)
        self.queue_panel.item_selected.connect(self._on_queue_item_selected)
        self.queue_panel.request_start_batch.connect(self._start_batch_processing)
        self.queue_panel.request_cancel_batch.connect(self._cancel_batch_processing)
        splitter.addWidget(self.queue_panel)

        # 2. Center Canvas
        self.canvas = InteractiveCanvas(self)
        self.canvas.stroke_finished.connect(self._on_brush_stroke_finished)
        splitter.addWidget(self.canvas)

        # 3. Right Controls Panel
        self.controls_panel = ControlsPanel(self)
        self.controls_panel.setMinimumWidth(320)
        self.controls_panel.setMaximumWidth(450)
        self.controls_panel.composition_changed.connect(self._update_composition)
        self.controls_panel.brush_mode_changed.connect(self._on_brush_mode_changed)
        self.controls_panel.mask_action_triggered.connect(self._on_mask_action)
        self.controls_panel.mask_overlay_toggled.connect(self._on_mask_overlay_toggled)
        self.controls_panel.request_export_current.connect(self._export_current_image)
        self.controls_panel.request_export_batch.connect(self._export_batch_images)
        splitter.addWidget(self.controls_panel)

        # Splitter layout ratios
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 2)
        self.setCentralWidget(splitter)

        # Toolbars & Status Bar
        self._build_toolbar()
        self._build_status_bar()

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main Toolbar", self)
        tb.setIconSize(QSize(22, 22))
        tb.setMovable(False)
        self.addToolBar(tb)

        # File actions
        self.act_open = QAction("Open Image", self)
        self.act_open.setShortcut(QKeySequence("Ctrl+O"))
        self.act_open.triggered.connect(self.queue_panel._on_add_files_clicked)
        tb.addAction(self.act_open)

        self.act_open_folder = QAction("Add Folder", self)
        self.act_open_folder.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self.act_open_folder.triggered.connect(self.queue_panel._on_add_folder_clicked)
        tb.addAction(self.act_open_folder)

        tb.addSeparator()

        # Inference Action
        self.act_remove_bg = QAction("✂ Remove Background", self)
        self.act_remove_bg.setShortcut(QKeySequence("Ctrl+R"))
        self.act_remove_bg.setStyleSheet("font-weight: bold;")
        self.act_remove_bg.triggered.connect(self._remove_background_current)
        tb.addAction(self.act_remove_bg)

        tb.addSeparator()

        # Canvas Controls
        self.act_fit = QAction("Fit Screen", self)
        self.act_fit.setShortcut(QKeySequence("Ctrl+0"))
        self.act_fit.triggered.connect(self.canvas.fit_to_screen)
        tb.addAction(self.act_fit)

        self.act_zoom_in = QAction("Zoom +", self)
        self.act_zoom_in.setShortcut(QKeySequence("+"))
        self.act_zoom_in.triggered.connect(self.canvas.zoom_in)
        tb.addAction(self.act_zoom_in)

        self.act_zoom_out = QAction("Zoom -", self)
        self.act_zoom_out.setShortcut(QKeySequence("-"))
        self.act_zoom_out.triggered.connect(self.canvas.zoom_out)
        tb.addAction(self.act_zoom_out)

        self.act_before_after = QAction("View Original", self)
        self.act_before_after.setCheckable(True)
        self.act_before_after.toggled.connect(self.canvas.toggle_before_after)
        tb.addAction(self.act_before_after)

        tb.addSeparator()

        # Dialogs
        self.act_server = QAction("🌐 Mobile Server", self)
        self.act_server.triggered.connect(self._open_server_dialog)
        tb.addAction(self.act_server)

        self.act_settings = QAction("⚙ Settings", self)
        self.act_settings.triggered.connect(self._open_settings_dialog)
        tb.addAction(self.act_settings)

        self.act_diagnostics = QAction("🩺 Diagnostics", self)
        self.act_diagnostics.triggered.connect(self._open_diagnostics_dialog)
        tb.addAction(self.act_diagnostics)

        tb.addSeparator()

        self.act_export = QAction("💾 Export Image", self)
        self.act_export.setShortcut(QKeySequence("Ctrl+S"))
        self.act_export.triggered.connect(self._export_current_image)
        tb.addAction(self.act_export)

    def _build_status_bar(self) -> None:
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)

        provider_str = "GPU (Accelerated)" if is_gpu_available() else "CPU"
        self.lbl_model_info = QLabel(f"Model: {self.settings.model_name} • {provider_str}")
        self.lbl_model_info.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.status_bar.addPermanentWidget(self.lbl_model_info)

    def _init_shortcuts(self) -> None:
        # Undo / Redo
        act_undo = QAction("Undo", self)
        act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        act_undo.triggered.connect(lambda: self._on_mask_action("undo"))
        self.addAction(act_undo)

        act_redo = QAction("Redo", self)
        act_redo.setShortcut(QKeySequence("Ctrl+Y"))
        act_redo.triggered.connect(lambda: self._on_mask_action("redo"))
        self.addAction(act_redo)

    def _update_status_bar(self, message: str) -> None:
        self.status_bar.showMessage(message)

    # -------------------------------------------------------------
    # Queue Selection & Display
    # -------------------------------------------------------------
    def _on_queue_item_selected(self, index: int) -> None:
        item = self.queue_panel.items[index]
        try:
            raw_img = Image.open(item.path)
            self.canvas.set_original_image(raw_img)

            if item.composite is not None:
                self.canvas.set_display_image(item.composite)
            elif item.cutout is not None:
                self.canvas.set_display_image(item.cutout)
            else:
                self.canvas.set_display_image(raw_img)

            self.canvas.fit_to_screen()
            self._update_undo_redo_controls()
            self._update_status_bar(f"Loaded: {item.filename} ({item.dimensions[0]}x{item.dimensions[1]})")
        except Exception as exc:
            logger.error("Failed to load queue item preview: %s", exc)
            self._update_status_bar(f"Error loading {item.filename}: {exc}")

    # -------------------------------------------------------------
    # AI Background Removal Workflow
    # -------------------------------------------------------------
    def _remove_background_current(self) -> None:
        item = self.queue_panel.get_current_item()
        if not item:
            QMessageBox.information(self, "No Image Selected", "Please add or select an image from the queue.")
            return

        self.settings = Settings.load()
        self.act_remove_bg.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(10)
        self._update_status_bar("Starting background removal...")

        self.current_worker = InferenceWorker(
            image_source=item.path,
            model_name=self.settings.model_name,
            use_alpha_matting=self.settings.use_alpha_matting,
            prefer_gpu=self.settings.prefer_gpu,
            parent=self,
        )
        self.current_worker.progress_signal.connect(self._on_inference_progress)
        self.current_worker.finished_signal.connect(self._on_inference_finished)
        self.current_worker.error_signal.connect(self._on_inference_error)
        self.current_worker.start()

    def _on_inference_progress(self, percent: int, msg: str) -> None:
        self.progress_bar.setValue(percent)
        self._update_status_bar(msg)

    def _on_inference_finished(self, cutout: Image.Image, mask: Image.Image) -> None:
        self.progress_bar.hide()
        self.act_remove_bg.setEnabled(True)

        idx = self.queue_panel.list_widget.currentRow()
        if idx >= 0:
            self.queue_panel.update_item_result(idx, cutout, mask)

        self._update_composition()
        self._update_undo_redo_controls()
        self._update_status_bar("Background removed successfully.")

    def _on_inference_error(self, err_msg: str) -> None:
        self.progress_bar.hide()
        self.act_remove_bg.setEnabled(True)
        self._update_status_bar("Inference error occurred.")
        QMessageBox.critical(self, "Background Removal Error", f"Failed to process image:\n\n{err_msg}")

    # -------------------------------------------------------------
    # Composition Updates
    # -------------------------------------------------------------
    def _update_composition(self) -> None:
        item = self.queue_panel.get_current_item()
        if not item or item.cutout is None:
            return

        # If mask editor exists, obtain refined cutout
        cutout = item.mask_editor.get_cutout() if item.mask_editor else item.cutout
        params = self.controls_panel.get_composition_params()

        # Load background image if chosen
        bg_img = None
        if params["bg_mode"] == "image" and params["bg_image_path"]:
            try:
                bg_img = load_image(params["bg_image_path"], ensure_rgba=True)
            except Exception as exc:
                logger.warning("Failed to load background image: %s", exc)

        composite = composite_image(
            cutout=cutout,
            bg_mode=params["bg_mode"],
            solid_color=params["solid_color"],
            gradient_colors=params["gradient_colors"],
            gradient_angle=params["gradient_angle"],
            bg_image=bg_img,
            bg_fit_mode=params["bg_fit_mode"],
            bg_blur=params["bg_blur"],
            bg_brightness=params["bg_brightness"],
            canvas_preset=params["canvas_preset"],
            scale=params["scale"],
            offset_x=params["offset_x"],
            offset_y=params["offset_y"],
            rotation=params["rotation"],
            padding=params["padding"],
            enable_shadow=params["enable_shadow"],
            shadow_intensity=params["shadow_intensity"],
            enable_outline=params["enable_outline"],
            outline_color=params["outline_color"],
            outline_width=params["outline_width"],
        )

        item.composite = composite
        self.canvas.set_display_image(composite)

    # -------------------------------------------------------------
    # Mask Editing & Brush
    # -------------------------------------------------------------
    def _on_brush_mode_changed(self, mode: str, radius: int) -> None:
        self.canvas.brush_mode = mode
        self.canvas.brush_radius = radius
        self.canvas.viewport().update()

    def _on_brush_stroke_finished(self, points: List[tuple[int, int]], radius: int, mode: str) -> None:
        item = self.queue_panel.get_current_item()
        if not item or not item.mask_editor:
            return

        item.mask_editor.apply_brush_stroke(points, radius, mode)
        self._update_composition()
        self._update_undo_redo_controls()

    def _on_mask_action(self, action: str) -> None:
        item = self.queue_panel.get_current_item()
        if not item or not item.mask_editor:
            return

        editor = item.mask_editor
        if action == "feather":
            editor.feather_edges(radius=2.0)
        elif action == "smooth":
            editor.smooth_edges(size=3)
        elif action == "expand":
            editor.expand_mask(pixels=2)
        elif action == "shrink":
            editor.shrink_mask(pixels=2)
        elif action == "reset":
            editor.reset_to_ai()
        elif action == "undo":
            editor.undo()
        elif action == "redo":
            editor.redo()

        self._update_composition()
        self._update_undo_redo_controls()

    def _on_mask_overlay_toggled(self, checked: bool) -> None:
        item = self.queue_panel.get_current_item()
        if not item or not item.mask_editor:
            return

        if checked:
            overlay = item.mask_editor.get_mask_overlay()
            self.canvas.set_display_image(overlay)
        else:
            self._update_composition()

    def _update_undo_redo_controls(self) -> None:
        item = self.queue_panel.get_current_item()
        if item and item.mask_editor:
            self.controls_panel.update_undo_redo_state(
                can_undo=item.mask_editor.can_undo,
                can_redo=item.mask_editor.can_redo,
            )
        else:
            self.controls_panel.update_undo_redo_state(False, False)

    # -------------------------------------------------------------
    # Batch Processing
    # -------------------------------------------------------------
    def _start_batch_processing(self) -> None:
        if not self.queue_panel.items:
            QMessageBox.information(self, "Batch Empty", "Queue has no images to process.")
            return

        self.settings = Settings.load()
        self.queue_panel.btn_process_all.setEnabled(False)
        self.queue_panel.btn_cancel.setEnabled(True)
        self.progress_bar.show()
        self.progress_bar.setValue(0)

        # Prepare queue dicts
        tasks = [{"path": item.path} for item in self.queue_panel.items]

        self.batch_worker = BatchWorker(
            queue_items=tasks,
            model_name=self.settings.model_name,
            use_alpha_matting=self.settings.use_alpha_matting,
            prefer_gpu=self.settings.prefer_gpu,
            parent=self,
        )
        self.batch_worker.item_started.connect(self._on_batch_item_started)
        self.batch_worker.item_finished.connect(self._on_batch_item_finished)
        self.batch_worker.all_finished.connect(self._on_batch_all_finished)
        self.batch_worker.start()

    def _cancel_batch_processing(self) -> None:
        if self.batch_worker:
            self.batch_worker.cancel()
            self._update_status_bar("Cancelling batch processing...")

    def _on_batch_item_started(self, index: int, filename: str) -> None:
        self.queue_panel.update_item_status(index, "Processing...")
        total = len(self.queue_panel.items)
        self.progress_bar.setValue(int((index / total) * 100))
        self._update_status_bar(f"Batch processing [{index + 1}/{total}]: {filename}")

    def _on_batch_item_finished(self, index: int, success: bool, msg: str, cutout: Any, mask: Any) -> None:
        if success and cutout and mask:
            self.queue_panel.update_item_result(index, cutout, mask)
        else:
            self.queue_panel.update_item_status(index, "Failed", error_msg=msg)

    def _on_batch_all_finished(self, summary: Dict[str, Any]) -> None:
        self.progress_bar.hide()
        self.queue_panel.btn_process_all.setEnabled(True)
        self.queue_panel.btn_cancel.setEnabled(False)
        self._update_status_bar(f"Batch completed: {summary['success']} succeeded, {summary['failed']} failed.")
        QMessageBox.information(
            self,
            "Batch Complete",
            f"Finished processing batch queue:\n\n"
            f"• Succeeded: {summary['success']}\n"
            f"• Failed: {summary['failed']}\n"
            f"• Cancelled: {summary.get('cancelled', 0)}\n\n"
            "You can now review any image and use 'Batch Export' to save all cutouts.",
        )

    # -------------------------------------------------------------
    # Single and Batch Exporting
    # -------------------------------------------------------------
    def _export_current_image(self) -> None:
        item = self.queue_panel.get_current_item()
        if not item or (item.composite is None and item.cutout is None):
            QMessageBox.warning(self, "Export Warning", "Please remove background first before exporting.")
            return

        img_to_export = item.composite if item.composite is not None else item.cutout
        exp_params = self.controls_panel.get_export_params()

        ext = ".jpg" if exp_params["format_name"].upper() in ("JPEG", "JPG") else f".{exp_params['format_name'].lower()}"
        target_path, is_skipped = generate_safe_output_path(
            output_dir=exp_params["output_dir"],
            original_filename=item.filename,
            naming_template=exp_params["naming_template"],
            extension=ext,
            overwrite_policy=exp_params["overwrite_policy"],
        )

        if is_skipped or not target_path:
            QMessageBox.information(self, "Export Skipped", "Export was skipped according to overwrite policy.")
            return

        try:
            saved = export_image(
                image=img_to_export,
                destination_path=target_path,
                format_name=exp_params["format_name"],
                quality=exp_params["quality"],
            )
            self._update_status_bar(f"Exported to: {saved}")
            QMessageBox.information(self, "Export Successful", f"Saved successfully to:\n\n{saved}")
        except Exception as exc:
            logger.error("Export error: %s", exc)
            QMessageBox.critical(self, "Export Failed", f"Could not export image:\n\n{exc}")

    def _export_batch_images(self, as_zip: bool) -> None:
        processed_items = [it for it in self.queue_panel.items if (it.composite or it.cutout)]
        if not processed_items:
            QMessageBox.warning(self, "No Cutouts", "No processed cutouts in queue to export. Process queue first.")
            return

        exp_params = self.controls_panel.get_export_params()
        tasks = [
            {
                "composite_image": it.composite if it.composite else it.cutout,
                "original_filename": it.filename,
            }
            for it in processed_items
        ]

        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.export_worker = ExportWorker(
            export_tasks=tasks,
            output_dir=exp_params["output_dir"],
            export_format=exp_params["format_name"],
            export_quality=exp_params["quality"],
            as_zip=as_zip,
            naming_template=exp_params["naming_template"],
            overwrite_policy=exp_params["overwrite_policy"],
            parent=self,
        )
        self.export_worker.progress_signal.connect(lambda pct, msg: (self.progress_bar.setValue(pct), self._update_status_bar(msg)))
        self.export_worker.finished_signal.connect(self._on_export_finished)
        self.export_worker.error_signal.connect(lambda err: QMessageBox.critical(self, "Export Error", err))
        self.export_worker.start()

    def _on_export_finished(self, summary: Dict[str, Any]) -> None:
        self.progress_bar.hide()
        self._update_status_bar("Export completed.")
        QMessageBox.information(
            self,
            "Export Summary",
            f"Export completed!\n\n"
            f"• Exported: {summary['exported']}\n"
            f"• Skipped: {summary.get('skipped', 0)}\n"
            f"• Destination: {summary['destination']}",
        )

    # -------------------------------------------------------------
    # Dialog Openers
    # -------------------------------------------------------------
    def _open_server_dialog(self) -> None:
        dlg = ServerDialog(self)
        dlg.exec()

    def _open_settings_dialog(self) -> None:
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.settings = Settings.load()
            provider_str = "GPU (Accelerated)" if is_gpu_available() else "CPU"
            self.lbl_model_info.setText(f"Model: {self.settings.model_name} • {provider_str}")

    def _open_diagnostics_dialog(self) -> None:
        dlg = DiagnosticsDialog(self)
        dlg.exec()
