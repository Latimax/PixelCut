"""
Generate PixelCut App Icons and Splash Logo
"""
import math
import os
from PIL import Image, ImageDraw, ImageFilter

def create_pixelcut_master_icon(size=512, is_round=False):
    # Master image with RGBA
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Base shape
    padding = size * 0.04
    rect = [padding, padding, size - padding, size - padding]
    corner_radius = size * 0.22 if not is_round else size * 0.46

    # Create gradient background
    bg_gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg_gradient)
    
    # Render diagonal gradient from #0F172A to #312E81 to #4F46E5
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2.0 * size)
            # Color stops:
            # 0.0: (15, 23, 42) -> #0F172A
            # 0.5: (49, 46, 129) -> #312E81
            # 1.0: (79, 70, 229) -> #4F46E5
            if t < 0.5:
                sub_t = t * 2.0
                r = int(15 + sub_t * (49 - 15))
                g = int(23 + sub_t * (46 - 23))
                b = int(42 + sub_t * (129 - 42))
            else:
                sub_t = (t - 0.5) * 2.0
                r = int(49 + sub_t * (79 - 49))
                g = int(46 + sub_t * (70 - 46))
                b = int(129 + sub_t * (229 - 129))
            bg_gradient.putpixel((x, y), (r, g, b, 255))

    # Mask for squircle or circle
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(rect, radius=int(corner_radius), fill=255)

    # Apply mask to gradient
    img.paste(bg_gradient, (0, 0), mask)

    # 2. Add subtle checkerboard on the left half (representing background cut)
    checker = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ch_draw = ImageDraw.Draw(checker)
    sq = int(size * 0.05)
    for cx in range(0, size // 2, sq):
        for cy in range(0, size, sq):
            if ((cx // sq) + (cy // sq)) % 2 == 0:
                ch_draw.rectangle([cx, cy, cx + sq, cy + sq], fill=(255, 255, 255, 18))

    # Composite checker onto background with mask
    img.alpha_composite(checker)

    # 3. Add glowing neon outline along the squircle border
    border_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(border_img)
    b_draw.rounded_rectangle(rect, radius=int(corner_radius), outline=(129, 140, 248, 180), width=max(2, int(size * 0.015)))
    img.alpha_composite(border_img)

    # 4. Draw stylized cutting line (dashed diagonal laser / cut line)
    laser = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    l_draw = ImageDraw.Draw(laser)
    
    # Diagonal cut line from top-mid-left to bottom-mid-right
    x1, y1 = size * 0.42, size * 0.18
    x2, y2 = size * 0.58, size * 0.82
    
    # Glow behind cut line
    l_draw.line([(x1, y1), (x2, y2)], fill=(56, 189, 248, 120), width=int(size * 0.035))
    laser = laser.filter(ImageFilter.GaussianBlur(radius=size * 0.015))
    l_draw = ImageDraw.Draw(laser)
    # Crisp laser line
    l_draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 240), width=int(size * 0.012))
    img.alpha_composite(laser)

    # 5. Draw Stylized AI Magic Cut Icon (Scissors + 4-Point Stars)
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)

    # Center coordinates
    cx, cy = size * 0.5, size * 0.5

    # Draw Scissors Blades
    blade_color = (255, 255, 255, 255)
    blade_accent = (99, 102, 241, 255)
    
    # Left blade (slanted)
    # Pivot at (cx, cy)
    # Blade 1 going up-right:
    b1_pts = [
        (cx - size*0.04, cy + size*0.02),
        (cx + size*0.18, cy - size*0.22),
        (cx + size*0.14, cy - size*0.23),
        (cx - size*0.06, cy - size*0.01)
    ]
    o_draw.polygon(b1_pts, fill=blade_color)

    # Blade 2 going down-right:
    b2_pts = [
        (cx - size*0.04, cy - size*0.02),
        (cx + size*0.18, cy + size*0.22),
        (cx + size*0.14, cy + size*0.23),
        (cx - size*0.06, cy + size*0.01)
    ]
    o_draw.polygon(b2_pts, fill=blade_color)

    # Pivot screw
    o_draw.ellipse([cx - size*0.035, cy - size*0.035, cx + size*0.035, cy + size*0.035], fill=(56, 189, 248, 255), outline=(255, 255, 255, 255), width=int(size*0.01))

    # Handles / Finger loops (left side)
    h1_box = [cx - size*0.26, cy - size*0.22, cx - size*0.08, cy - size*0.04]
    o_draw.ellipse(h1_box, outline=blade_color, width=int(size*0.035))
    
    h2_box = [cx - size*0.26, cy + size*0.04, cx - size*0.08, cy + size*0.22]
    o_draw.ellipse(h2_box, outline=blade_color, width=int(size*0.035))

    # Connecting shanks
    o_draw.line([(cx - size*0.12, cy - size*0.08), (cx - size*0.03, cy - size*0.01)], fill=blade_color, width=int(size*0.035))
    o_draw.line([(cx - size*0.12, cy + size*0.08), (cx - size*0.03, cy + size*0.01)], fill=blade_color, width=int(size*0.035))

    # Helper function to draw 4-pointed AI sparkle star
    def draw_sparkle(center_x, center_y, outer_r, inner_r, color):
        pts = []
        for i in range(8):
            angle = i * (math.pi / 4.0)
            r = outer_r if i % 2 == 0 else inner_r
            pts.append((center_x + r * math.cos(angle), center_y + r * math.sin(angle)))
        o_draw.polygon(pts, fill=color)

    # Main vibrant magic sparkle (top right)
    draw_sparkle(cx + size*0.24, cy - size*0.18, size*0.09, size*0.025, (254, 240, 138, 255)) # Soft yellow/gold
    draw_sparkle(cx + size*0.24, cy - size*0.18, size*0.06, size*0.018, (255, 255, 255, 255)) # Bright white core

    # Secondary sparkles (cyan & lavender)
    draw_sparkle(cx + size*0.30, cy + size*0.12, size*0.05, size*0.015, (56, 189, 248, 255)) # Cyan
    draw_sparkle(cx - size*0.22, cy - size*0.28, size*0.045, size*0.012, (192, 132, 252, 255)) # Purple

    # Final composite
    img.alpha_composite(overlay)
    return img

def main():
    res_dir = os.path.abspath(r"c:\Users\Latimax\Desktop\Project\Python\PixelCut\android\app\src\main\res")
    
    # 1. Master app logo for Splash screen and drawables
    print("Generating 512x512 Master Logo...")
    master = create_pixelcut_master_icon(512, is_round=False)
    drawable_dir = os.path.join(res_dir, "drawable")
    os.makedirs(drawable_dir, exist_ok=True)
    master.save(os.path.join(drawable_dir, "app_logo.png"), "PNG")
    print("Saved app_logo.png")

    # 2. Launcher icons for different screen densities
    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }

    for folder, px in densities.items():
        folder_path = os.path.join(res_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # Standard icon
        icon = create_pixelcut_master_icon(px, is_round=False)
        icon.save(os.path.join(folder_path, "ic_launcher.png"), "PNG")
        
        # Round icon
        icon_round = create_pixelcut_master_icon(px, is_round=True)
        icon_round.save(os.path.join(folder_path, "ic_launcher_round.png"), "PNG")
        print(f"Generated {folder} ({px}x{px})")

if __name__ == "__main__":
    main()
