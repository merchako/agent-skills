#!/usr/bin/env python3
"""Compose a Scriptura profile photo: square crop with the face off-center and the
Scriptura mark badge placed in the lightest, calmest background area.

  grid    SRC OUT.png                 downscaled preview with a 10% grid, for locating the face
  compose SRC --face X,Y,W,H OUTDIR   crop + badge + circle preview (face box in SRC pixels)

Requires Pillow and numpy.
"""
import argparse, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

# Scriptura web icon (red disc, spiral-S knocked out), from
# https://www.scriptura.org/wp-content/uploads/2024/09/cropped-Scriptura-WebIcon1-01.png
ICON = Path(__file__).resolve().parent.parent / "assets" / "scriptura-mark.png"
CREAM = (0xF4, 0xEA, 0xDB)  # Scriptura's cream; fills the knockout spiral
OUT = 1024


def load(src):
    return ImageOps.exif_transpose(Image.open(src)).convert("RGB")


def cmd_grid(a):
    im = load(a.src)
    scale = 800 / max(im.size)
    small = im.resize((round(im.width * scale), round(im.height * scale)))
    d = ImageDraw.Draw(small)
    for i in range(1, 10):
        x, y = small.width * i / 10, small.height * i / 10
        d.line([(x, 0), (x, small.height)], fill=(255, 0, 0), width=1)
        d.line([(0, y), (small.width, y)], fill=(255, 0, 0), width=1)
        d.text((x + 2, 2), f"{i*10}%", fill=(255, 0, 0))
        d.text((2, y + 2), f"{i*10}%", fill=(255, 0, 0))
    small.save(a.out)
    print(f"source {im.width}x{im.height}; grid lines every 10% -> {a.out}")


def badge(size):
    icon = Image.open(ICON).convert("RGBA")
    base = Image.new("RGBA", icon.size, (0, 0, 0, 0))
    ImageDraw.Draw(base).ellipse([1, 1, icon.width - 2, icon.height - 2], fill=CREAM + (255,))
    base.alpha_composite(icon)
    return base.resize((size, size), Image.LANCZOS)


def crop_box(im, face, head_frac, face_x):
    fx, fy, fw, fh = face
    side = min(round(fw / head_frac), im.width, im.height)
    cx, eyes = fx + fw / 2, fy + fh * 0.42
    left = round(cx - face_x * side)
    top = round(eyes - 0.34 * side)
    left = max(0, min(left, im.width - side))
    top = max(0, min(top, im.height - side))
    return left, top, side


def place(base, face_out, size):
    """Lightest, least busy spot for a circular badge that stays inside the circle crop
    and clear of the face box (+margin)."""
    g = base.convert("L")
    a = np.asarray(g, float)
    e = np.asarray(g.filter(ImageFilter.FIND_EDGES), float)
    r = size // 2
    yy, xx = np.mgrid[-r:r, -r:r]
    m = xx**2 + yy**2 <= r * r
    fx0, fy0, fx1, fy1 = face_out
    pad = OUT * 0.03
    best = None
    for cy in range(r + 10, OUT - r, 8):
        for cx in range(r + 10, OUT - r, 8):
            if np.hypot(cx - OUT / 2, cy - OUT / 2) + r > OUT / 2 - OUT * 0.05:
                continue  # would be clipped by the circular avatar mask
            nx, ny = min(max(cx, fx0), fx1), min(max(cy, fy0), fy1)
            if np.hypot(cx - nx, cy - ny) < r + pad:
                continue  # overlaps the face
            p, q = a[cy - r:cy + r, cx - r:cx + r][m], e[cy - r:cy + r, cx - r:cx + r][m]
            s = p.mean() - 2 * p.std() - 3 * q.mean()
            if best is None or s > best[0]:
                best = (s, cx, cy, p.mean())
    if best is None:
        sys.exit("no badge spot clear of the face; lower --badge or --head")
    return best


def cmd_compose(a):
    im = load(a.src)
    face = [float(v) for v in a.face.split(",")]
    left, top, side = crop_box(im, face, a.head, a.face_x)
    k = OUT / side
    base = im.crop((left, top, left + side, top + side)).resize((OUT, OUT), Image.LANCZOS)
    fx, fy, fw, fh = face
    face_out = ((fx - left) * k, (fy - top) * k, (fx + fw - left) * k, (fy + fh - top) * k)
    size = round(OUT * a.badge)
    if a.at:
        cx, cy = (round(float(v) * OUT) for v in a.at.split(","))
        lum = None
    else:
        _, cx, cy, lum = place(base, face_out, size)
    out = base.convert("RGBA")
    out.alpha_composite(badge(size), (cx - size // 2, cy - size // 2))
    out = out.convert("RGB")
    d = Path(a.outdir); d.mkdir(parents=True, exist_ok=True)
    photo = d / a.name
    out.save(photo, quality=92)
    mask = Image.new("L", (OUT, OUT), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, OUT - 1, OUT - 1], fill=255)
    circ = Image.new("RGB", (OUT, OUT), "white"); circ.paste(out, mask=mask)
    prev = Image.new("RGB", (2 * 400 + 30, 400), "white")
    prev.paste(out.resize((400, 400)), (0, 0)); prev.paste(circ.resize((400, 400)), (430, 0))
    prev.save(d / "preview.png")
    print(f"crop {side}px at ({left},{top}); badge {size}px centered at "
          f"({cx/OUT:.2f},{cy/OUT:.2f})" + (f", bg luminance {lum:.0f}" if lum else ""))
    print(f"photo   -> {photo}\npreview -> {d / 'preview.png'}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grid"); g.add_argument("src"); g.add_argument("out"); g.set_defaults(fn=cmd_grid)
    c = sub.add_parser("compose")
    c.add_argument("src"); c.add_argument("outdir")
    c.add_argument("--face", required=True, help="X,Y,W,H of the head (ear to ear, crown to chin) in SRC pixels")
    c.add_argument("--head", type=float, default=0.38, help="head width as fraction of frame (default 0.38)")
    c.add_argument("--face-x", type=float, default=0.38, help="head center x as fraction of frame (default 0.38 = left of center)")
    c.add_argument("--badge", type=float, default=0.25, help="badge diameter as fraction of frame (default 0.25)")
    c.add_argument("--at", help="force badge center as FX,FY fractions, e.g. 0.74,0.53")
    c.add_argument("--name", default="profile-scriptura.jpg")
    c.set_defaults(fn=cmd_compose)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
