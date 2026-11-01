#!/usr/bin/env python3
"""Cut a quarter out of its background for the Break down viewer.

  uv run --with "rembg[cpu]" --with scipy --with opencv-python-headless tools/cutout.py OUT_DIR name=photo.jpg[@x0,y0,x1,y1 ...] ...

Writes OUT_DIR/<name>.webp (transparent background, cropped to the meat) and prints
the view box for hunt.json: {"img", "box": [x, y, w, h]}. The box is in the
coordinates of the photo shrunk to fit 1500x2000, the same coordinates annotate.py
specs and hunt.json regions use, so outlines drawn on the original photo still line up.
Only the biggest piece (the quarter, plus a hand holding it) is kept; hooks, coolers
and other stray bits are dropped, and glare from the shop light is toned down.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
from rembg import new_session, remove
from scipy import ndimage

PAD = 24


def deglare(rgb, alpha):
    """Tame shop-light glare on the meat: pull washed-out, too-bright patches back toward the
    meat's own brightness and color, then add a little local contrast. Background is ignored."""
    m = alpha > 128
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    L, a, b = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    c = np.hypot(a, b)
    lo, hi = np.percentile(L[m], [50, 99.5]); cmed = np.median(c[m]); am, bm = np.median(a[m]), np.median(b[m])
    bright = np.clip((L - lo) / (hi - lo), 0, 1) ** 1.3
    washed = np.clip((L - np.percentile(L[m], 35)) / 40, 0, 1) * np.clip((cmed - c) / (cmed * .55), 0, 1)
    w = np.maximum(bright, washed) * m                       # 0 on normal meat, 1 in the worst glare
    w = cv2.GaussianBlur(w.astype(np.float32), (0, 0), 8)
    L2 = L - w * np.maximum(L - lo, 0) * 0.8
    k = 1 + w * 0.6
    a2 = a * k * (1 - w * .55) + am * w * .55                # wash the color back toward the meat's own
    b2 = b * k * (1 - w * .55) + bm * w * .55
    out = np.dstack([L2, a2 + 128, b2 + 128]).clip(0, 255).astype(np.uint8)
    out = cv2.cvtColor(out, cv2.COLOR_LAB2RGB)
    lab = cv2.cvtColor(out, cv2.COLOR_RGB2LAB)
    lab[..., 0] = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(6, 6)).apply(lab[..., 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def cut(session, src, dest, erase=()):
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im.thumbnail((1500, 2000))
    rgba = remove(im, session=session, post_process_mask=True)
    a = np.array(rgba)
    alpha = a[..., 3] > 40
    for x0, y0, x1, y1 in erase:  # boxes the caller marked as junk (a cooler edge, a hand)
        alpha[y0:y1, x0:x1] = False
    solid = ndimage.binary_opening(alpha, iterations=6)  # breaks thin straps, strings and hooks off
    lab, n = ndimage.label(solid)
    if n:
        sizes = ndimage.sum(solid, lab, range(1, n + 1))
        keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= sizes.max() * 0.15])
        keep = ndimage.binary_fill_holes(ndimage.binary_dilation(keep, iterations=8) & alpha)
        a[..., 3] = np.where(keep, a[..., 3], 0)
    a[..., :3] = deglare(np.ascontiguousarray(a[..., :3]), a[..., 3])
    ys, xs = np.nonzero(a[..., 3] > 40)
    x0, y0 = max(0, xs.min() - PAD), max(0, ys.min() - PAD)
    x1, y1 = min(im.width, xs.max() + PAD), min(im.height, ys.max() + PAD)
    Image.fromarray(a).crop((x0, y0, x1, y1)).save(dest, quality=82, method=6)
    return [int(x0), int(y0), int(x1 - x0), int(y1 - y0)]


def main(argv):
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    session = new_session("isnet-general-use")
    for arg in argv[1:]:
        name, src = arg.split("=", 1)
        src, *boxes = src.split("@")  # name=photo.jpg@x0,y0,x1,y1 erases that box first
        dest = out / f"{name}.webp"
        erase = [tuple(int(v) for v in b.split(",")) for b in boxes]
        print(json.dumps({"name": name, "img": str(dest), "box": cut(session, src, dest, erase)}))


if __name__ == "__main__":
    main(sys.argv[1:])
