"""QThread background worker threads to keep desktop UI fluid and responsive."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image
from PySide6.QtCore import QThread, Signal

from pixelcut_local.core.background_removal import (
    get_inference_session,
    remove_background,
)
from pixelcut_local.core.composition import composite_image
from pixelcut_local.core.export import (
    export_image,
    export_images_to_zip,
    generate_safe_output_path,
)
from pixelcut_local.core.image_io import load_image
from pixelcut_local.core.validation import ImageValidationError, validate_image_file

logger = logging.getLogger(__name__)


class InferenceWorker(QThread):
    """Worker thread for single-image background removal."""

    progress_signal = Signal(int, str)  # (percent, status_message)
    finished_signal = Signal(object, object)  # (cutout_PIL, mask_PIL)
    error_signal = Signal(str)

    def __init__(
        self,
        image_source: Any,
        model_name: str = "u2netp",
        use_alpha_matting: bool = False,
        prefer_gpu: bool = False,
        parent: Optional[Any] = None,
    ):
        super().__init__(parent)
        self.image_source = image_source
        self.model_name = model_name
        self.use_alpha_matting = use_alpha_matting
        self.prefer_gpu = prefer_gpu

    def run(self) -> None:
        try:
            self.progress_signal.emit(10, "Validating and loading image...")
            if isinstance(self.image_source, (str, Path)):
                img = load_image(self.image_source, ensure_rgba=True)
            elif isinstance(self.image_source, Image.Image):
                img = self.image_source.convert("RGBA")
            else:
                raise ValueError("Unsupported image source.")

            self.progress_signal.emit(30, f"Initializing AI session ({self.model_name})...")
            session = get_inference_session(
                model_name=self.model_name,
                prefer_gpu=self.prefer_gpu,
            )

            self.progress_signal.emit(60, "Removing background...")
            cutout, mask = remove_background(
                img,
                model_name=self.model_name,
                use_alpha_matting=self.use_alpha_matting,
                prefer_gpu=self.prefer_gpu,
                session=session,
            )

            self.progress_signal.emit(100, "Background removal complete.")
            self.finished_signal.emit(cutout, mask)
        except Exception as exc:
            logger.error("Inference worker error: %s", exc)
            self.error_signal.emit(str(exc))


class BatchWorker(QThread):
    """Worker thread for batch processing multiple queued images with session reuse."""

    item_started = Signal(int, str)  # (index, filename)
    item_progress = Signal(int, int)  # (index, percent)
    item_finished = Signal(int, bool, str, object, object)  # (index, success, message, cutout, mask)
    all_finished = Signal(dict)  # summary: {total, success, failed, skipped}

    def __init__(
        self,
        queue_items: List[Dict[str, Any]],
        model_name: str = "u2netp",
        use_alpha_matting: bool = False,
        prefer_gpu: bool = False,
        parent: Optional[Any] = None,
    ):
        super().__init__(parent)
        self.queue_items = queue_items
        self.model_name = model_name
        self.use_alpha_matting = use_alpha_matting
        self.prefer_gpu = prefer_gpu
        self._is_cancelled: bool = False
        self._is_paused: bool = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def set_paused(self, paused: bool) -> None:
        self._is_paused = paused

    def run(self) -> None:
        summary = {"total": len(self.queue_items), "success": 0, "failed": 0, "cancelled": 0}

        try:
            # Pre-load/acquire session once for the entire batch
            session = get_inference_session(
                model_name=self.model_name,
                prefer_gpu=self.prefer_gpu,
            )
        except Exception as exc:
            for idx in range(len(self.queue_items)):
                self.item_finished.emit(idx, False, f"Model initialization failed: {exc}", None, None)
            summary["failed"] = len(self.queue_items)
            self.all_finished.emit(summary)
            return

        for idx, item in enumerate(self.queue_items):
            if self._is_cancelled:
                summary["cancelled"] += 1
                self.item_finished.emit(idx, False, "Cancelled by user.", None, None)
                continue

            # Handle pause
            while self._is_paused and not self._is_cancelled:
                self.msleep(100)

            file_path = item["path"]
            filename = Path(file_path).name
            self.item_started.emit(idx, filename)
            self.item_progress.emit(idx, 10)

            try:
                # Load and process
                img = load_image(file_path, ensure_rgba=True)
                self.item_progress.emit(idx, 40)

                cutout, mask = remove_background(
                    img,
                    model_name=self.model_name,
                    use_alpha_matting=self.use_alpha_matting,
                    prefer_gpu=self.prefer_gpu,
                    session=session,
                )
                self.item_progress.emit(idx, 100)
                summary["success"] += 1
                self.item_finished.emit(idx, True, "Complete", cutout, mask)

            except Exception as exc:
                logger.warning("Batch processing failed for %s: %s", filename, exc)
                summary["failed"] += 1
                self.item_finished.emit(idx, False, str(exc), None, None)

        self.all_finished.emit(summary)


class ExportWorker(QThread):
    """Worker thread for batch exporting multiple images to disk or ZIP."""

    progress_signal = Signal(int, str)  # (percent, message)
    finished_signal = Signal(dict)  # summary: {exported, skipped, failed, destination}
    error_signal = Signal(str)

    def __init__(
        self,
        export_tasks: List[Dict[str, Any]],
        output_dir: str,
        export_format: str = "PNG",
        export_quality: int = 95,
        as_zip: bool = False,
        zip_filename: str = "pixelcut_export.zip",
        naming_template: str = "{original_name}_cutout",
        overwrite_policy: str = "auto_number",
        parent: Optional[Any] = None,
    ):
        super().__init__(parent)
        self.export_tasks = export_tasks
        self.output_dir = output_dir
        self.export_format = export_format
        self.export_quality = export_quality
        self.as_zip = as_zip
        self.zip_filename = zip_filename
        self.naming_template = naming_template
        self.overwrite_policy = overwrite_policy

    def run(self) -> None:
        summary = {"exported": 0, "skipped": 0, "failed": 0, "destination": self.output_dir}
        total = len(self.export_tasks)

        if total == 0:
            self.finished_signal.emit(summary)
            return

        try:
            if self.as_zip:
                images_for_zip: List[Tuple[Image.Image, str]] = []
                for idx, task in enumerate(self.export_tasks):
                    img = task["composite_image"]
                    name = task["original_filename"]
                    images_for_zip.append((img, name))
                    self.progress_signal.emit(int((idx / total) * 80), f"Packaging {name}...")

                zip_dest = Path(self.output_dir) / self.zip_filename
                export_images_to_zip(
                    images_for_zip,
                    zip_destination=zip_dest,
                    format_name=self.export_format,
                    quality=self.export_quality,
                )
                summary["exported"] = total
                summary["destination"] = str(zip_dest)
                self.progress_signal.emit(100, "ZIP export complete.")
            else:
                ext = ".jpg" if self.export_format.upper() in ("JPEG", "JPG") else f".{self.export_format.lower()}"
                for idx, task in enumerate(self.export_tasks):
                    img = task["composite_image"]
                    name = task["original_filename"]

                    target_path, is_skipped = generate_safe_output_path(
                        output_dir=self.output_dir,
                        original_filename=name,
                        naming_template=self.naming_template,
                        extension=ext,
                        overwrite_policy=self.overwrite_policy,
                    )

                    if is_skipped:
                        summary["skipped"] += 1
                        continue

                    if not target_path:
                        summary["failed"] += 1
                        continue

                    export_image(
                        image=img,
                        destination_path=target_path,
                        format_name=self.export_format,
                        quality=self.export_quality,
                    )
                    summary["exported"] += 1
                    pct = int(((idx + 1) / total) * 100)
                    self.progress_signal.emit(pct, f"Exported {target_path.name}")

            self.finished_signal.emit(summary)
        except Exception as exc:
            logger.error("Export worker failed: %s", exc)
            self.error_signal.emit(str(exc))
