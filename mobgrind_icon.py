#!/usr/bin/env python3
"""One source of truth for the MobGrind icon, drawn with Pillow.

- sword_icon(size, color): a flat single-color sword silhouette on a transparent
  background, rotated 45° — used for the tray icon (tinted by state).
- app_icon(size): the full-color sword on a rounded gradient tile — used for the
  .app / .exe bundle icon and the website favicon.

Run `python mobgrind_icon.py` to (re)generate the files in assets/ and docs/.
Everything is rendered at 4x and downsampled with LANCZOS for clean edges.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

_HERE = os.path.dirname(os.path.abspath(__file__))

# Full-color palette for the bundle icon.
PAL = {
    "blade": (214, 219, 226), "edge": (245, 247, 250), "fuller": (150, 157, 168),
    "guard": (201, 157, 63), "pommel": (201, 157, 63), "grip": (74, 48, 30), "wrap": (52, 33, 20),
}
TILE_TOP, TILE_BOTTOM = (64, 92, 52), (20, 34, 22)   # gradient tile background


def _draw_sword(S, pal):
    """Draw an upright sword on an SxS transparent canvas (rendered hi-res)."""
    hi = S * 4
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = hi / 2
    tip, taper, guard_y, bw = 0.10 * hi, 0.12 * hi, 0.60 * hi, 0.060 * hi
    lw = max(1, int(0.013 * hi))

    d.polygon([(cx, tip), (cx - bw, tip + taper), (cx - bw, guard_y),
               (cx + bw, guard_y), (cx + bw, tip + taper)], fill=pal["blade"])
    d.line([(cx, tip + taper), (cx, guard_y)], fill=pal["fuller"], width=lw)          # fuller groove
    d.line([(cx - bw, tip + taper), (cx - bw, guard_y)], fill=pal["edge"], width=lw)  # bright edge

    d.rounded_rectangle([0.28 * hi, 0.585 * hi, 0.72 * hi, 0.645 * hi],
                        radius=0.03 * hi, fill=pal["guard"])                          # crossguard
    grip_top, grip_bot = 0.645 * hi, 0.85 * hi
    d.rounded_rectangle([0.455 * hi, grip_top, 0.545 * hi, grip_bot],
                        radius=0.02 * hi, fill=pal["grip"])                           # grip
    for t in range(1, 5):                                                            # grip wraps
        y = grip_top + (grip_bot - grip_top) * t / 5
        d.line([(0.455 * hi, y), (0.545 * hi, y)], fill=pal["wrap"], width=max(1, int(0.009 * hi)))
    pr = 0.052 * hi
    d.ellipse([cx - pr, grip_bot - pr, cx + pr, grip_bot + pr], fill=pal["pommel"])   # pommel

    return img.resize((S, S), Image.LANCZOS)


def _rotated(sword, size, scale):
    """Rotate a sword layer 45° and center it on a size×size transparent canvas."""
    r = sword.rotate(45, expand=True, resample=Image.BICUBIC)
    side = int(size * scale)
    r = r.resize((side, side), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(r, ((size - side) // 2, (size - side) // 2), r)
    return out


def sword_icon(size, color):
    """Flat single-color sword silhouette (for the tray, tinted by state)."""
    flat = {k: color for k in PAL}
    return _rotated(_draw_sword(size, flat), size, 1.0)


def _tile(size):
    """Rounded-rectangle tile with a vertical gradient."""
    grad = Image.new("RGBA", (size, size))
    px = grad.load()
    for y in range(size):
        t = y / (size - 1)
        px_row = tuple(int(a + (b - a) * t) for a, b in zip(TILE_TOP, TILE_BOTTOM)) + (255,)
        for x in range(size):
            px[x, y] = px_row
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(0.22 * size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return out


def app_icon(size):
    """Full-color sword on a gradient tile (bundle icon / favicon)."""
    out = _tile(size)
    sword = _rotated(_draw_sword(int(size * 0.90), PAL), size, 0.90)
    # soft drop shadow
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sh = sword.split()[3].point(lambda a: a * 110 // 255)
    shadow.paste((0, 0, 0, 255), (int(size * 0.02), int(size * 0.03)), sh)
    out.alpha_composite(shadow)
    out.alpha_composite(sword)
    return out


def _generate():
    assets = os.path.join(_HERE, "assets")
    docs = os.path.join(_HERE, "docs")
    os.makedirs(assets, exist_ok=True)

    master = app_icon(1024)
    master.save(os.path.join(assets, "icon.png"))
    master.save(os.path.join(docs, "icon-512.png"))               # website / apple-touch
    master.resize((64, 64), Image.LANCZOS).save(os.path.join(docs, "favicon.png"))

    # Windows .ico (multi-size)
    master.save(os.path.join(assets, "icon.ico"),
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    # macOS .icns via iconutil (Mac only; the build runner is macOS)
    if sys.platform == "darwin":
        iconset = os.path.join(assets, "icon.iconset")
        os.makedirs(iconset, exist_ok=True)
        for s in (16, 32, 128, 256, 512):
            master.resize((s, s), Image.LANCZOS).save(os.path.join(iconset, f"icon_{s}x{s}.png"))
            master.resize((s * 2, s * 2), Image.LANCZOS).save(os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", iconset,
                        "-o", os.path.join(assets, "icon.icns")], check=True)
    print("icons written to assets/ and docs/")


if __name__ == "__main__":
    _generate()
