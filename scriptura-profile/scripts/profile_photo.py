#!/usr/bin/env python3
"""Compose a Scriptura profile photo: square crop with the face off-center and the
Scriptura mark badge centered in the biggest calm background area that contrasts
with it. Works on light or dark backgrounds: the brand red is used when it has
enough contrast, otherwise a monochrome light or dark mark.

  grid    SRC OUT.png                 downscaled preview with a 10% grid, for locating the face
  compose SRC --face X,Y,W,H OUTDIR   crop + badge + circle preview (face box in SRC pixels)

Requires Pillow and numpy.
"""
import argparse, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

# Scriptura web icon (red disc, spiral-S knocked out), from
# https://www.scriptura.org/wp-content/uploads/2024/09/cropped-Scriptura-WebIcon1-01.png
ICON = Path(__file__).resolve().parent.parent / "assets" / "scriptura-mark.png"
RED = (0x9A, 0x39, 0x3B)
CREAM = (0xF4, 0xEA, 0xDB)
INK = (0x23, 0x1F, 0x20)
# disc color, spiral color (None = knocked out, background shows through)
VARIANTS = {"red": (RED, CREAM), "light": (CREAM, None), "dark": (INK, None)}
OUT = 1024
GRID = 256  # analysis resolution
MIN_CONTRAST = 3.0  # WCAG ratio between disc and background (graphics threshold)


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


def badge(size, variant):
    disc, spiral = VARIANTS[variant]
    alpha = Image.open(ICON).convert("RGBA").getchannel("A")  # disc minus spiral
    w = alpha.width
    out = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    if spiral:
        ImageDraw.Draw(out).ellipse([1, 1, w - 2, w - 2], fill=spiral + (255,))
    out.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (w, w), disc).split(), alpha)))
    return out.resize((size, size), Image.LANCZOS)


def crop_box(im, face, head_frac, face_x):
    fx, fy, fw, fh = face
    side = min(round(fw / head_frac), im.width, im.height)
    cx, eyes = fx + fw / 2, fy + fh * 0.42
    left = round(cx - face_x * side)
    top = round(eyes - 0.34 * side)
    left = max(0, min(left, im.width - side))
    top = max(0, min(top, im.height - side))
    return left, top, side


def luminance(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return c @ [0.2126, 0.7152, 0.0722]


def box_mean(a, w):
    """Mean over a (2w+1)^2 window, edge-padded, via an integral image."""
    p = np.pad(a, w + 1, mode="edge").cumsum(0).cumsum(1)
    n = 2 * w + 1
    s = p[n:, n:] - p[:-n, n:] - p[n:, :-n] + p[:-n, :-n]
    return s[: a.shape[0], : a.shape[1]] / n**2


def depth(valid):
    """Approximate Euclidean distance (in cells) to the nearest invalid cell or edge:
    iterated erosion alternating 4- and 8-neighbourhoods (octagonal metric)."""
    d = np.zeros(valid.shape)
    cur = np.pad(valid, 1)
    for i in range(1, max(valid.shape)):
        nb = [cur[1:-1, :-2], cur[1:-1, 2:], cur[:-2, 1:-1], cur[2:, 1:-1]]
        if i % 2 == 0:
            nb += [cur[:-2, :-2], cur[:-2, 2:], cur[2:, :-2], cur[2:, 2:]]
        core = cur[1:-1, 1:-1] & np.logical_and.reduce(nb)
        if not core.any():
            break
        d[core] = i
        cur = np.pad(core, 1)
    return d * 1.04  # octagonal erosion slightly underestimates Euclidean depth


def subject_mask(face_out, n):
    """Face box plus a widening trapezoid below the chin for neck and shoulders."""
    fx0, fy0, fx1, fy1 = (v * n / OUT for v in face_out)
    fw, fh = fx1 - fx0, fy1 - fy0
    yy, xx = np.mgrid[0:n, 0:n]
    pad = 0.12 * fw
    face = (xx > fx0 - pad) & (xx < fx1 + pad) & (yy > fy0 - pad) & (yy < fy1 + pad)
    cx = (fx0 + fx1) / 2
    half = fw * (0.55 + 1.3 * np.clip((yy - fy1) / fh, 0, 1)) + pad
    body = (yy >= fy1 - 0.2 * fh) & (np.abs(xx - cx) < half)
    return face | body


def place(base, face_out, want, calm, only=None):
    """For each badge color, find the biggest calm region whose background contrasts
    with the disc, and its center. Prefer brand red; fall back to monochrome."""
    n, k = GRID, OUT / GRID
    rgb = np.asarray(base.resize((n, n), Image.LANCZOS), float)
    lum = luminance(rgb)
    w = 3  # ~28px window at 1024
    mean = box_mean(lum, w)
    # perceptual calmness on the gamma-encoded scale (0-255 like a grayscale view)
    g = rgb @ [0.299, 0.587, 0.114]
    gm = box_mean(g, w)
    gstd = np.sqrt(np.maximum(box_mean(g**2, w) - gm**2, 0))
    blocked = subject_mask(face_out, n)
    yy, xx = np.mgrid[0:n, 0:n] + 0.5
    edge_room = (n / 2) * 0.95 - np.hypot(xx - n / 2, yy - n / 2)  # stay inside circle crop
    results = {}
    for name in (only,) if only else VARIANTS:
        L = luminance(VARIANTS[name][0])
        ratio = (np.maximum(mean, L) + 0.05) / (np.minimum(mean, L) + 0.05)
        valid = (gstd < calm) & (ratio >= MIN_CONTRAST) & ~blocked
        room = np.minimum(depth(valid), edge_room)
        room[~valid] = 0
        score = room + 0.5 * np.minimum(ratio, 10)  # ties go to stronger contrast
        iy, ix = np.unravel_index(np.argmax(score), score.shape)
        r = room[iy, ix] * k
        results[name] = dict(cx=round((ix + 0.5) * k), cy=round((iy + 0.5) * k),
                             radius=r, contrast=ratio[iy, ix])
    min_r = OUT * 0.16 / 2
    fits = {n_: v for n_, v in results.items() if v["radius"] >= min_r}
    if not fits:
        best = max(results.items(), key=lambda kv: kv[1]["radius"])
        sys.exit(f"no calm, contrasting area big enough for the badge (best: {best[0]} "
                 f"r={best[1]['radius']:.0f}px); try --calm 20, --head lower, or --at")
    if "red" in fits:
        name = "red"
    else:
        name = max(fits, key=lambda n_: (fits[n_]["radius"], fits[n_]["contrast"]))
    v = fits[name]
    size = int(min(want, 2 * v["radius"] * 0.92))
    return name, v["cx"], v["cy"], size, v["contrast"], results


def cmd_compose(a):
    im = load(a.src)
    face = [float(v) for v in a.face.split(",")]
    left, top, side = crop_box(im, face, a.head, a.face_x)
    k = OUT / side
    base = im.crop((left, top, left + side, top + side)).resize((OUT, OUT), Image.LANCZOS)
    fx, fy, fw, fh = face
    face_out = ((fx - left) * k, (fy - top) * k, (fx + fw - left) * k, (fy + fh - top) * k)
    want = round(OUT * a.badge)
    if a.at:
        cx, cy = (round(float(v) * OUT) for v in a.at.split(","))
        variant, size, info = a.color or "red", want, ""
    else:
        variant, cx, cy, size, ratio, results = place(base, face_out, want, a.calm, a.color)
        info = f", {variant} on bg contrast {ratio:.1f}:1  [" + "  ".join(
            f"{n}: r={v['radius']:.0f}px {v['contrast']:.1f}:1" for n, v in results.items()) + "]"
    out = base.convert("RGBA")
    out.alpha_composite(badge(size, variant), (cx - size // 2, cy - size // 2))
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
          f"({cx/OUT:.2f},{cy/OUT:.2f}){info}")
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
    c.add_argument("--badge", type=float, default=0.25, help="max badge diameter as fraction of frame (default 0.25)")
    c.add_argument("--color", choices=list(VARIANTS), help="force badge color (default: red if it fits, else best monochrome)")
    c.add_argument("--calm", type=float, default=12, help="max local grayscale std-dev counted as calm (default 12)")
    c.add_argument("--at", help="force badge center as FX,FY fractions, e.g. 0.74,0.53")
    c.add_argument("--name", default="profile-scriptura.jpg")
    c.set_defaults(fn=cmd_compose)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
