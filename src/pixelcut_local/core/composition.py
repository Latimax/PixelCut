"""Image composition: backgrounds, foreground transforms, effects, and canvas sizing."""

from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple, Union
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps
import numpy as np

logger = logging.getLogger(__name__)


def create_checkerboard_pattern(
    width: int,
    height: int,
    grid_size: int = 16,
    color1: Tuple[int, int, int] = (240, 240, 240),
    color2: Tuple[int, int, int] = (205, 205, 205),
) -> Image.Image:
    """Create a high-contrast checkerboard image for transparency previewing."""
    if width <= 0 or height <= 0:
        width, height = max(1, width), max(1, height)

    img = Image.new("RGBA", (width, height), (*color1, 255))
    tile_w = grid_size * 2
    tile_h = grid_size * 2

    tile = Image.new("RGBA", (tile_w, tile_h), (*color1, 255))
    tile_draw = Image.new("RGBA", (grid_size, grid_size), (*color2, 255))
    tile.paste(tile_draw, (0, 0))
    tile.paste(tile_draw, (grid_size, grid_size))

    # Paste tiled checkerboard
    for y in range(0, height, tile_h):
        for x in range(0, width, tile_w):
            img.paste(tile, (x, y))

    return img


def create_solid_background(width: int, height: int, hex_or_rgb: Union[str, Tuple[int, int, int]]) -> Image.Image:
    """Create a solid color RGBA background."""
    if isinstance(hex_or_rgb, str):
        color = hex_or_rgb.strip().lstrip("#")
        if len(color) == 6:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            rgb = (r, g, b)
        elif len(color) == 3:
            r = int(color[0] * 2, 16)
            g = int(color[1] * 2, 16)
            b = int(color[2] * 2, 16)
            rgb = (r, g, b)
        else:
            rgb = (255, 255, 255)
    else:
        rgb = hex_or_rgb[:3]

    return Image.new("RGBA", (width, height), (*rgb, 255))


def create_gradient_background(
    width: int,
    height: int,
    color1: Tuple[int, int, int],
    color2: Tuple[int, int, int],
    angle_degrees: float = 0.0,
) -> Image.Image:
    """Create a 2-color linear gradient at a specified angle (0° = top-to-bottom, 90° = left-to-right)."""
    if width <= 0 or height <= 0:
        width, height = max(1, width), max(1, height)

    angle_rad = math.radians(angle_degrees)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Coordinate grid
    x = np.linspace(-0.5, 0.5, width)
    y = np.linspace(-0.5, 0.5, height)
    xv, yv = np.meshgrid(x, y)

    # Projection along angle vector
    proj = xv * sin_a + yv * cos_a
    min_p, max_p = proj.min(), proj.max()
    denom = max_p - min_p if (max_p - min_p) > 1e-6 else 1.0
    t = (proj - min_p) / denom  # normalized 0.0 to 1.0

    r1, g1, b1 = color1[:3]
    r2, g2, b2 = color2[:3]

    r = (r1 + t * (r2 - r1)).astype(np.uint8)
    g = (g1 + t * (g2 - g1)).astype(np.uint8)
    b = (b1 + t * (b2 - b1)).astype(np.uint8)
    a = np.full((height, width), 255, dtype=np.uint8)

    rgba = np.stack([r, g, b, a], axis=-1)
    return Image.fromarray(rgba, mode="RGBA")


def fit_background_image(
    bg_image: Image.Image,
    target_width: int,
    target_height: int,
    fit_mode: str = "cover",
    blur_radius: float = 0.0,
    brightness: float = 1.0,
) -> Image.Image:
    """Resize/fit an uploaded background image to canvas dimensions and apply optional effects."""
    bg = bg_image.convert("RGBA")
    src_w, src_h = bg.size

    if fit_mode == "stretch":
        resized = bg.resize((target_width, target_height), Image.Resampling.LANCZOS)
    elif fit_mode == "contain":
        scale = min(target_width / src_w, target_height / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        fitted = bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
        resized = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
        offset_x = (target_width - new_w) // 2
        offset_y = (target_height - new_h) // 2
        resized.paste(fitted, (offset_x, offset_y))
    else:  # "cover" default
        scale = max(target_width / src_w, target_height / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        fitted = bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
        offset_x = (new_w - target_width) // 2
        offset_y = (new_h - target_height) // 2
        resized = fitted.crop((offset_x, offset_y, offset_x + target_width, offset_y + target_height))

    # Apply blur if configured
    if blur_radius > 0:
        resized = resized.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Apply brightness if configured
    if abs(brightness - 1.0) > 0.01:
        # Separate RGB and A to adjust brightness without degrading alpha
        r, g, b, a = resized.split()
        rgb = Image.merge("RGB", (r, g, b))
        enhancer = ImageEnhance.Brightness(rgb)
        rgb_bright = enhancer.enhance(brightness)
        br, bg_c, bb = rgb_bright.split()
        resized = Image.merge("RGBA", (br, bg_c, bb, a))

    return resized


def compute_canvas_dimensions(
    original_size: Tuple[int, int],
    preset: str = "original",
    custom_size: Optional[Tuple[int, int]] = None,
) -> Tuple[int, int]:
    """Compute target canvas dimensions according to selected preset or custom size."""
    orig_w, orig_h = original_size

    if custom_size and custom_size[0] > 0 and custom_size[1] > 0:
        return custom_size

    if preset == "1:1 (Square)":
        dim = max(orig_w, orig_h)
        return (dim, dim)
    elif preset == "4:5 (Portrait)":
        # Height is 5/4 of width or width is 4/5 of height
        if orig_w / 4 > orig_h / 5:
            return (orig_w, int(orig_w * 5 / 4))
        else:
            return (int(orig_h * 4 / 5), orig_h)
    elif preset == "3:4 (Portrait)":
        if orig_w / 3 > orig_h / 4:
            return (orig_w, int(orig_w * 4 / 3))
        else:
            return (int(orig_h * 3 / 4), orig_h)
    elif preset == "9:16 (Story/Reel)":
        if orig_w / 9 > orig_h / 16:
            return (orig_w, int(orig_w * 16 / 9))
        else:
            return (int(orig_h * 9 / 16), orig_h)
    elif preset == "16:9 (Landscape)":
        if orig_w / 16 > orig_h / 9:
            return (orig_w, int(orig_w * 9 / 16))
        else:
            return (int(orig_h * 16 / 9), orig_h)
    elif preset == "4:3 (Landscape)":
        if orig_w / 4 > orig_h / 3:
            return (orig_w, int(orig_w * 3 / 4))
        else:
            return (int(orig_h * 4 / 3), orig_h)

    # "original"
    return (orig_w, orig_h)


def generate_outline(
    cutout: Image.Image,
    outline_color: Tuple[int, int, int] = (255, 255, 255),
    outline_width: int = 4,
) -> Image.Image:
    """Generate an outline / sticker stroke around the non-transparent subject."""
    if outline_width <= 0:
        return cutout

    alpha = cutout.split()[3]
    arr = np.array(alpha)
    # Dilation by outline_width
    struct = ndimage.generate_binary_structure(2, 1)
    dilated = ndimage.binary_dilation(arr > 20, structure=struct, iterations=outline_width)
    
    # Create outline image
    outline_img = Image.new("RGBA", cutout.size, (*outline_color, 255))
    outline_mask = Image.fromarray((dilated.astype(np.uint8) * 255), mode="L")
    outline_layer = Image.new("RGBA", cutout.size, (0, 0, 0, 0))
    outline_layer.paste(outline_img, (0, 0), outline_mask)

    # Composite subject on top of outline
    outline_layer.alpha_composite(cutout)
    return outline_layer


def generate_drop_shadow(
    cutout: Image.Image,
    offset: Tuple[int, int] = (10, 15),
    blur_radius: float = 12.0,
    opacity: float = 0.5,
    shadow_color: Tuple[int, int, int] = (0, 0, 0),
) -> Image.Image:
    """Generate a realistic soft drop shadow layer under the cutout."""
    if opacity <= 0.01:
        return cutout

    w, h = cutout.size
    alpha = cutout.split()[3]
    
    # Shadow mask
    shadow_mask = alpha.point(lambda p: int(p * opacity))
    shadow_color_img = Image.new("RGBA", (w, h), (*shadow_color, 255))

    shadow_base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_base.paste(shadow_color_img, offset, shadow_mask)

    if blur_radius > 0:
        shadow_base = shadow_base.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Composite cutout over shadow
    shadow_base.alpha_composite(cutout)
    return shadow_base


def composite_image(
    cutout: Image.Image,
    bg_mode: str = "transparent",
    solid_color: str = "#ffffff",
    gradient_colors: Tuple[Tuple[int, int, int], Tuple[int, int, int]] = ((240, 240, 250), (180, 200, 240)),
    gradient_angle: float = 45.0,
    bg_image: Optional[Image.Image] = None,
    bg_fit_mode: str = "cover",
    bg_blur: float = 0.0,
    bg_brightness: float = 1.0,
    canvas_preset: str = "original",
    custom_canvas_size: Optional[Tuple[int, int]] = None,
    scale: float = 1.0,
    offset_x: int = 0,
    offset_y: int = 0,
    rotation: float = 0.0,
    padding: int = 0,
    enable_shadow: bool = False,
    shadow_intensity: float = 0.5,
    enable_outline: bool = False,
    outline_color: Tuple[int, int, int] = (255, 255, 255),
    outline_width: int = 0,
) -> Image.Image:
    """Full composition pipeline placing the foreground cutout over the requested background.

    Returns the resulting RGBA composite image.
    """
    orig_w, orig_h = cutout.size
    target_w, target_h = compute_canvas_dimensions(
        (orig_w, orig_h),
        preset=canvas_preset,
        custom_size=custom_canvas_size,
    )

    # 1. Prepare Background Layer
    if bg_mode == "transparent":
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    elif bg_mode == "solid":
        canvas = create_solid_background(target_w, target_h, solid_color)
    elif bg_mode == "gradient":
        c1, c2 = gradient_colors
        canvas = create_gradient_background(target_w, target_h, c1, c2, angle_degrees=gradient_angle)
    elif bg_mode == "image" and bg_image is not None:
        canvas = fit_background_image(
            bg_image,
            target_w,
            target_h,
            fit_mode=bg_fit_mode,
            blur_radius=bg_blur,
            brightness=bg_brightness,
        )
    else:
        # Fallback to transparent
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    # 2. Process Foreground Effects (Outline, then Shadow)
    fg = cutout.copy()

    if enable_outline and outline_width > 0:
        fg = generate_outline(fg, outline_color=outline_color, outline_width=outline_width)

    if enable_shadow and shadow_intensity > 0.05:
        fg = generate_drop_shadow(
            fg,
            offset=(int(8 * scale), int(12 * scale)),
            blur_radius=10.0 * scale,
            opacity=shadow_intensity,
        )

    # 3. Apply Transformations: Scale, Rotation, Positioning
    if abs(rotation) > 0.1:
        # Rotate with transparent expansion
        fg = fg.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)

    # Apply padding & user scale
    effective_scale = max(0.05, min(5.0, scale))
    if padding > 0:
        # Reduce scale slightly to accommodate padding
        pad_scale = max(0.1, 1.0 - (padding * 2.0 / max(target_w, target_h)))
        effective_scale *= pad_scale

    new_fg_w = max(1, int(fg.width * effective_scale))
    new_fg_h = max(1, int(fg.height * effective_scale))
    if (new_fg_w, new_fg_h) != fg.size:
        fg = fg.resize((new_fg_w, new_fg_h), Image.Resampling.LANCZOS)

    # Calculate center placement + user offset
    pos_x = (target_w - new_fg_w) // 2 + offset_x
    pos_y = (target_h - new_fg_h) // 2 + offset_y

    # 4. Composite Foreground onto Background
    canvas.alpha_composite(fg, (pos_x, pos_y))

    return canvas
