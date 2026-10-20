"""Image export service: formats, flattening, naming templates, overwrite safety, and ZIP packaging."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import zipfile
from PIL import Image

logger = logging.getLogger(__name__)


def generate_safe_output_path(
    output_dir: Union[str, Path],
    original_filename: str,
    naming_template: str = "{original_name}_cutout",
    extension: str = ".png",
    overwrite_policy: str = "auto_number",  # "auto_number", "overwrite", "skip"
) -> Tuple[Optional[Path], bool]:
    """Calculate target destination path obeying naming template and overwrite policy.

    Returns:
        (target_path, is_skipped)
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_stem = Path(original_filename).stem
    # Clean template variables
    formatted_name = naming_template.replace("{original_name}", base_stem)
    # Sanitize filename (remove path traversal or illegal characters)
    safe_name = "".join(c for c in formatted_name if c.isalnum() or c in ("-", "_", " ")).strip()
    if not safe_name:
        safe_name = f"{base_stem}_cutout"

    ext = extension if extension.startswith(".") else f".{extension}"
    target = out_dir / f"{safe_name}{ext}"

    if not target.exists():
        return target, False

    if overwrite_policy == "overwrite":
        return target, False
    elif overwrite_policy == "skip":
        return target, True
    else:  # "auto_number"
        counter = 1
        while True:
            candidate = out_dir / f"{safe_name}_{counter}{ext}"
            if not candidate.exists():
                return candidate, False
            counter += 1


def export_image(
    image: Image.Image,
    destination_path: Union[str, Path],
    format_name: str = "PNG",
    quality: int = 95,
    resize_dimensions: Optional[Tuple[int, int]] = None,
    matte_color: Tuple[int, int, int] = (255, 255, 255),
    strip_metadata: bool = True,
) -> Path:
    """Export a composite image to disk in PNG, JPEG, or WEBP format.

    Handles flattening transparency for JPEG against matte_color.
    """
    dest = Path(destination_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    img = image.copy()
    if resize_dimensions and resize_dimensions[0] > 0 and resize_dimensions[1] > 0:
        img = img.resize(resize_dimensions, Image.Resampling.LANCZOS)

    fmt = format_name.upper()

    if fmt in ("JPEG", "JPG"):
        # JPEG does not support alpha channel: flatten against matte color
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            background = Image.new("RGB", img.size, matte_color)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            background.paste(img, (0, 0), img)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        save_kwargs = {"format": "JPEG", "quality": quality, "optimize": True}
        if strip_metadata:
            save_kwargs["exif"] = b""
        img.save(dest, **save_kwargs)

    elif fmt == "WEBP":
        # WEBP supports both lossy/lossless and alpha
        save_kwargs = {"format": "WEBP", "quality": quality}
        img.save(dest, **save_kwargs)

    else:  # PNG default
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        img.save(dest, format="PNG", optimize=True)

    logger.debug("Exported image to %s (%s)", dest, fmt)
    return dest


def export_images_to_zip(
    images_with_names: List[Tuple[Image.Image, str]],
    zip_destination: Union[str, Path],
    format_name: str = "PNG",
    quality: int = 95,
) -> Path:
    """Bundle a list of images into a single ZIP archive."""
    zip_path = Path(zip_destination)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    ext = f".{format_name.lower()}"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for img, name in images_with_names:
            buf = io.BytesIO()
            stem = Path(name).stem
            archive_filename = f"{stem}{ext}"

            if format_name.upper() in ("JPEG", "JPG"):
                if img.mode == "RGBA":
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, (0, 0), img)
                    bg.save(buf, format="JPEG", quality=quality)
                else:
                    img.convert("RGB").save(buf, format="JPEG", quality=quality)
            elif format_name.upper() == "WEBP":
                img.save(buf, format="WEBP", quality=quality)
            else:
                img.save(buf, format="PNG")

            zf.writestr(archive_filename, buf.getvalue())

    logger.info("Created export ZIP archive at %s with %d images", zip_path, len(images_with_names))
    return zip_path
