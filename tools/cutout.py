#!/usr/bin/env python3
"""Cut a quarter out of its background for the Break down viewer.

  uv run --with "rembg[cpu]" --with scipy tools/cutout.py OUT_DIR name=photo.jpg[@x0,y0,x1,y1 ...] ...

Writes OUT_DIR/<name>.webp (transparent background, cropped to the meat) and prints
the view box for hunt.json: {"img", "box": [x, y, w, h]}. The box is in the
coordinates of the photo shrunk to fit 1500x2000, the same coordinates annotate.py
specs and hunt.json regions use, so outlines drawn on the original photo still line up.
Only the biggest piece (the quarter, plus a hand holding it) is kept; hooks, coolers
and other stray bits are dropped.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from rembg import new_session, remove
from scipy import ndimage

PAD = 24


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
