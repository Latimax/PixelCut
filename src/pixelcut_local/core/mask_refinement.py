"""Manual mask refinement, brush editing, feathering, and undo/redo state."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
from scipy import ndimage

logger = logging.getLogger(__name__)


class MaskEditor:
    """Non-destructive interactive mask refinement manager.

    Maintains the base AI-generated mask and an undo/redo stack of mask states.
    Allows applying brush strokes (keep/remove), feathering, smoothing,
    and expanding/shrinking.
    """

    def __init__(self, original_image: Image.Image, initial_mask: Image.Image, max_history: int = 25):
        self.original_image = original_image.convert("RGBA")
        self.base_mask = initial_mask.convert("L")
        self.current_mask = self.base_mask.copy()
        self.max_history = max_history

        # Undo and Redo stacks store copies of PIL Image ('L')
        self._undo_stack: List[Image.Image] = []
        self._redo_stack: List[Image.Image] = []

    def _push_undo(self) -> None:
        """Save current mask state to undo stack and clear redo stack."""
        self._undo_stack.append(self.current_mask.copy())
        if len(self._undo_stack) > self.max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(self) -> bool:
        """Undo last mask modification."""
        if not self.can_undo:
            return False
        self._redo_stack.append(self.current_mask.copy())
        self.current_mask = self._undo_stack.pop()
        return True

    def redo(self) -> bool:
        """Redo last undone mask modification."""
        if not self.can_redo:
            return False
        self._undo_stack.append(self.current_mask.copy())
        self.current_mask = self._redo_stack.pop()
        return True

    def reset_to_ai(self) -> None:
        """Reset mask to the original AI-generated cutout mask."""
        self._push_undo()
        self.current_mask = self.base_mask.copy()

    def apply_brush_stroke(
        self,
        points: List[Tuple[int, int]],
        radius: int,
        mode: str = "keep",  # "keep" (foreground, 255) or "remove" (background, 0)
    ) -> None:
        """Apply a brush stroke along a sequence of points.

        If mode is 'keep', paints 255 (opaque).
        If mode is 'remove', paints 0 (transparent).
        """
        if not points or radius <= 0:
            return

        self._push_undo()
        draw = ImageDraw.Draw(self.current_mask)
        color = 255 if mode == "keep" else 0

        # Draw circles at each point and lines connecting consecutive points
        for i in range(len(points)):
            x, y = points[i]
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=color,
                outline=color,
            )
            if i > 0:
                px, py = points[i - 1]
                draw.line(
                    [(px, py), (x, y)],
                    fill=color,
                    width=radius * 2,
                )

    def feather_edges(self, radius: float = 2.0) -> None:
        """Apply Gaussian blur to soften mask edges."""
        if radius <= 0:
            return
        self._push_undo()
        self.current_mask = self.current_mask.filter(ImageFilter.GaussianBlur(radius=radius))

    def smooth_edges(self, size: int = 3) -> None:
        """Smooth jagged boundaries using median filtering."""
        if size < 3:
            return
        # Ensure odd size
        if size % 2 == 0:
            size += 1
        self._push_undo()
        self.current_mask = self.current_mask.filter(ImageFilter.MedianFilter(size=size))

    def expand_mask(self, pixels: int = 2) -> None:
        """Dilate the mask outwards by N pixels."""
        if pixels <= 0:
            return
        self._push_undo()
        arr = np.array(self.current_mask)
        # Binary dilation with circular structuring element
        struct = ndimage.generate_binary_structure(2, 1)
        dilated = ndimage.binary_dilation(arr > 128, structure=struct, iterations=pixels)
        # Merge dilated regions preserving soft edges where possible
        out_arr = np.where(dilated, np.maximum(arr, 255), arr)
        self.current_mask = Image.fromarray(out_arr.astype(np.uint8), mode="L")

    def shrink_mask(self, pixels: int = 2) -> None:
        """Erode the mask inwards by N pixels."""
        if pixels <= 0:
            return
        self._push_undo()
        arr = np.array(self.current_mask)
        struct = ndimage.generate_binary_structure(2, 1)
        eroded = ndimage.binary_erosion(arr > 128, structure=struct, iterations=pixels)
        out_arr = np.where(~eroded, np.minimum(arr, 0), arr)
        self.current_mask = Image.fromarray(out_arr.astype(np.uint8), mode="L")

    def get_cutout(self) -> Image.Image:
        """Combine original RGB image with current refined alpha mask."""
        result = self.original_image.copy()
        result.putalpha(self.current_mask)
        return result

    def get_mask_overlay(
        self,
        overlay_color: Tuple[int, int, int] = (255, 60, 60),
        opacity: float = 0.5,
    ) -> Image.Image:
        """Create a visual overlay highlighting the removed/transparent regions in red (rubylith)."""
        mask_arr = np.array(self.current_mask)
        # Transparent areas are where mask < 128
        inv_mask = (255 - mask_arr).astype(np.uint8)

        overlay = Image.new("RGBA", self.original_image.size, (*overlay_color, int(255 * opacity)))
        composite = Image.composite(overlay, self.original_image, Image.fromarray(inv_mask, mode="L"))
        return composite
