"""Queue panel widget managing multi-image batch queue, statuses, and drag-and-drop."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pixelcut_local.core.constants import SUPPORTED_INPUT_EXTENSIONS
from pixelcut_local.core.image_io import create_thumbnail
from pixelcut_local.core.mask_refinement import MaskEditor
from pixelcut_local.core.validation import ImageValidationError, validate_image_file
from pixelcut_local.desktop.canvas import pil_to_qpixmap

logger = logging.getLogger(__name__)


class QueueItemData:
    """Data holder for a queued image file."""

    def __init__(self, file_path: str):
        self.path: str = str(Path(file_path).resolve())
        self.filename: str = Path(self.path).name
        self.status: str = "Pending"
        self.dimensions: tuple[int, int] = (0, 0)
        self.size_mb: float = 0.0
        self.error_message: Optional[str] = None
        self.thumbnail: Optional[QPixmap] = None

        # Processed Results
        self.cutout: Optional[Image.Image] = None
        self.mask: Optional[Image.Image] = None
        self.mask_editor: Optional[MaskEditor] = None
        self.composite: Optional[Image.Image] = None


class QueuePanel(QWidget):
    """Batch queue sidebar supporting file drag & drop and queue controls."""

    item_selected = Signal(int)  # index of selected item
    request_start_batch = Signal()
    request_cancel_batch = Signal()
    request_clear_queue = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.items: List[QueueItemData] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header with Add buttons
        header_layout = QHBoxLayout()
        title_label = QLabel("Batch Queue")
        title_label.setStyleSheet("font-weight: 700; font-size: 14px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.btn_add_files = QPushButton("+ Files")
        self.btn_add_files.setToolTip("Add image files (Ctrl+O)")
        self.btn_add_files.clicked.connect(self._on_add_files_clicked)
        header_layout.addWidget(self.btn_add_files)

        self.btn_add_folder = QPushButton("+ Folder")
        self.btn_add_folder.setToolTip("Add entire folder of images (Ctrl+Shift+O)")
        self.btn_add_folder.clicked.connect(self._on_add_folder_clicked)
        header_layout.addWidget(self.btn_add_folder)

        layout.addLayout(header_layout)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(48, 48))
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.list_widget)

        # Queue Action Buttons
        actions_layout = QHBoxLayout()
        self.btn_remove = QPushButton("Remove")
        self.btn_remove.clicked.connect(self._on_remove_selected)
        actions_layout.addWidget(self.btn_remove)

        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.clicked.connect(self._on_clear_all)
        actions_layout.addWidget(self.btn_clear)
        layout.addLayout(actions_layout)

        # Batch Processing Controls
        batch_ctrl_layout = QHBoxLayout()
        self.btn_process_all = QPushButton("⚡ Process Queue")
        self.btn_process_all.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #4f46e5); "
            "color: white; font-weight: 600; padding: 8px; border-radius: 6px;"
        )
        self.btn_process_all.clicked.connect(self.request_start_batch.emit)
        batch_ctrl_layout.addWidget(self.btn_process_all)

        self.btn_cancel = QPushButton("Stop")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.request_cancel_batch.emit)
        batch_ctrl_layout.addWidget(self.btn_cancel)
        layout.addLayout(batch_ctrl_layout)

    def add_files(self, file_paths: List[str]) -> int:
        """Validate and append files to the queue."""
        added = 0
        for p_str in file_paths:
            path = Path(p_str)
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
                continue

            # Avoid immediate duplicate paths
            if any(it.path == str(path.resolve()) for it in self.items):
                continue

            try:
                w, h, _ = validate_image_file(path)
                item_data = QueueItemData(str(path))
                item_data.dimensions = (w, h)
                item_data.size_mb = path.stat().st_size / (1024 * 1024)

                # Generate thumbnail
                with Image.open(path) as raw_img:
                    thumb_pil = create_thumbnail(raw_img, (96, 96)).convert("RGBA")
                    item_data.thumbnail = pil_to_qpixmap(thumb_pil)

                self.items.append(item_data)
                added += 1

                # Add to QListWidget
                list_item = QListWidgetItem()
                list_item.setText(f"{item_data.filename}\n{w}x{h} • {item_data.size_mb:.1f}MB • Pending")
                if item_data.thumbnail:
                    list_item.setIcon(QIcon(item_data.thumbnail))
                self.list_widget.addItem(list_item)

            except Exception as exc:
                logger.warning("Skipped invalid file %s: %s", path.name, exc)

        if added > 0 and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

        return added

    def update_item_status(self, index: int, status: str, error_msg: Optional[str] = None) -> None:
        """Update display status text for a queue item."""
        if 0 <= index < len(self.items):
            item = self.items[index]
            item.status = status
            item.error_message = error_msg
            list_item = self.list_widget.item(index)
            if list_item:
                w, h = item.dimensions
                status_display = status
                if error_msg:
                    status_display = f"Failed ({error_msg[:24]}...)"
                list_item.setText(f"{item.filename}\n{w}x{h} • {item.size_mb:.1f}MB • {status_display}")

    def update_item_result(
        self,
        index: int,
        cutout: Image.Image,
        mask: Image.Image,
        composite: Optional[Image.Image] = None,
    ) -> None:
        """Attach processed cutout and mask to queue item."""
        if 0 <= index < len(self.items):
            item = self.items[index]
            item.cutout = cutout
            item.mask = mask
            item.mask_editor = MaskEditor(Image.open(item.path), mask)
            item.composite = composite or cutout
            self.update_item_status(index, "Completed")

    def get_current_item(self) -> Optional[QueueItemData]:
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.items):
            return self.items[row]
        return None

    def _on_row_changed(self, row: int) -> None:
        if 0 <= row < len(self.items):
            self.item_selected.emit(row)

    def _on_add_files_clicked(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Image Files (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)",
        )
        if files:
            self.add_files(files)

    def _on_add_folder_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder of Images")
        if folder:
            dir_path = Path(folder)
            candidates = [str(p) for p in dir_path.iterdir() if p.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS]
            self.add_files(candidates)

    def _on_remove_selected(self) -> None:
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.items):
            self.items.pop(row)
            self.list_widget.takeItem(row)
            if self.items:
                next_row = min(row, len(self.items) - 1)
                self.list_widget.setCurrentRow(next_row)

    def _on_clear_all(self) -> None:
        self.items.clear()
        self.list_widget.clear()
        self.request_clear_queue.emit()

    # Drag & Drop Handlers
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = []
        for url in event.mimeData().urls():
            local_path = Path(url.toLocalFile())
            if local_path.is_file():
                paths.append(str(local_path))
            elif local_path.is_dir():
                for p in local_path.iterdir():
                    if p.is_file() and p.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS:
                        paths.append(str(p))
        if paths:
            self.add_files(paths)
        event.acceptProposedAction()
