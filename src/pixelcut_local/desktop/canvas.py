"""Interactive canvas widget with zoom, pan, checkerboard background, and mask brush tool."""

from __future__ import annotations

import io
import logging
from typing import List, Optional, Tuple
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

logger = logging.getLogger(__name__)


def pil_to_qimage(pil_img: Image.Image) -> QImage:
    """Convert a PIL Image to a QImage without data loss."""
    if pil_img.mode != "RGBA":
        img = pil_img.convert("RGBA")
    else:
        img = pil_img
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
    return qimg.copy()


def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Convert a PIL Image to a QPixmap."""
    return QPixmap.fromImage(pil_to_qimage(pil_img))


class InteractiveCanvas(QGraphicsView):
    """Zoomable, pannable canvas supporting checkerboard background and interactive mask painting."""

    stroke_finished = Signal(list, int, str)  # (points_list, radius, mode)
    zoom_changed = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Rendering options
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMouseTracking(True)

        # Background Checkerboard Brush
        self._setup_checkerboard_brush()

        # Canvas items
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)

        # State
        self._zoom_factor = 1.0
        self._is_panning = False
        self._pan_start_pos = QPointF()

        # Brush mode: "none", "keep", "remove"
        self.brush_mode: str = "none"
        self.brush_radius: int = 20
        self._current_stroke_points: List[Tuple[int, int]] = []
        self._mouse_pos: Optional[QPointF] = None

        # Display images (PIL)
        self._current_pil_image: Optional[Image.Image] = None
        self._original_pil_image: Optional[Image.Image] = None
        self._showing_original: bool = False

    def _setup_checkerboard_brush(self) -> None:
        """Create a repeating 16x16 checkerboard brush for transparency."""
        size = 16
        pix = QPixmap(size * 2, size * 2)
        c1 = QColor(245, 245, 247)
        c2 = QColor(215, 218, 224)
        painter = QPainter(pix)
        painter.fillRect(0, 0, size, size, c1)
        painter.fillRect(size, 0, size, size, c2)
        painter.fillRect(0, size, size, size, c2)
        painter.fillRect(size, size, size, size, c1)
        painter.end()
        self.setBackgroundBrush(QBrush(pix))

    def set_display_image(self, image: Optional[Image.Image]) -> None:
        """Set the active composite or cutout image to display."""
        self._current_pil_image = image
        if not self._showing_original:
            self._update_scene_pixmap()

    def set_original_image(self, image: Optional[Image.Image]) -> None:
        """Store the original unedited image for before/after comparison."""
        self._original_pil_image = image

    def toggle_before_after(self, show_original: bool) -> None:
        """Switch view between original and current cutout/composite."""
        self._showing_original = show_original
        self._update_scene_pixmap()

    def _update_scene_pixmap(self) -> None:
        """Render the chosen image to scene pixmap item."""
        target_img = self._original_pil_image if self._showing_original else self._current_pil_image
        if target_img:
            qpix = pil_to_qpixmap(target_img)
            self._pixmap_item.setPixmap(qpix)
            self._scene.setSceneRect(QRectF(qpix.rect()))
        else:
            self._pixmap_item.setPixmap(QPixmap())
            self._scene.setSceneRect(QRectF())

    def reset_view(self) -> None:
        """Reset zoom to 100%."""
        self.resetTransform()
        self._zoom_factor = 1.0
        self.zoom_changed.emit(self._zoom_factor)

    def fit_to_screen(self) -> None:
        """Fit entire image within viewport."""
        if not self._pixmap_item.pixmap().isNull():
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            # Update zoom factor from transform
            self._zoom_factor = self.transform().m11()
            self.zoom_changed.emit(self._zoom_factor)

    def zoom_in(self) -> None:
        self._apply_zoom(1.25)

    def zoom_out(self) -> None:
        self._apply_zoom(0.8)

    def _apply_zoom(self, factor: float) -> None:
        new_zoom = self._zoom_factor * factor
        if 0.05 <= new_zoom <= 20.0:
            self.scale(factor, factor)
            self._zoom_factor = new_zoom
            self.zoom_changed.emit(self._zoom_factor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom with mouse wheel."""
        delta = event.angleDelta().y()
        if delta > 0:
            self._apply_zoom(1.15)
        elif delta < 0:
            self._apply_zoom(1 / 1.15)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Middle click or Space+Left click: Pan
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._is_panning = True
            self._pan_start_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        # Brush mode active
        if event.button() == Qt.MouseButton.LeftButton and self.brush_mode in ("keep", "remove"):
            scene_pos = self.mapToScene(event.pos())
            ix, iy = int(scene_pos.x()), int(scene_pos.y())
            self._current_stroke_points = [(ix, iy)]
            self.viewport().update()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._mouse_pos = event.position()

        if self._is_panning:
            delta = event.position() - self._pan_start_pos
            self._pan_start_pos = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return

        if self.brush_mode in ("keep", "remove"):
            if event.buttons() & Qt.MouseButton.LeftButton and self._current_stroke_points:
                scene_pos = self.mapToScene(event.pos())
                ix, iy = int(scene_pos.x()), int(scene_pos.y())
                self._current_stroke_points.append((ix, iy))
            self.viewport().update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._is_panning and (
            event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.LeftButton
        ):
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self.brush_mode in ("keep", "remove"):
            if self._current_stroke_points:
                self.stroke_finished.emit(
                    self._current_stroke_points.copy(),
                    self.brush_radius,
                    self.brush_mode,
                )
                self._current_stroke_points.clear()
                self.viewport().update()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        """Custom paint event to draw the brush cursor and active brush stroke overlay."""
        super().paintEvent(event)

        # Draw brush cursor outline if brush mode is active
        if self.brush_mode in ("keep", "remove") and self._mouse_pos:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # Calculate screen radius
            screen_radius = self.brush_radius * self._zoom_factor
            color = QColor(16, 185, 129, 220) if self.brush_mode == "keep" else QColor(239, 68, 68, 220)
            pen = QPen(color, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            painter.drawEllipse(
                self._mouse_pos.toPoint(),
                int(screen_radius),
                int(screen_radius),
            )
            painter.end()
