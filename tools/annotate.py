#!/usr/bin/env python3
"""Draw cut lines and labels on a butchering photo.

Usage: annotate.py SPEC.json
The spec names the source photo, the output, and the shapes. Coordinates are in
the oriented, resized image (default 1500x2000 portrait). Shapes:
  {"line": [[x,y],[x,y],...], "color": "red", "width": 10, "dashed": false}
  {"area": [[x,y],...], "color": "orange", "alpha": 90}      shaded polygon
  {"label": "CUT 4: CLOD", "at": [x,y], "color": "white"}     boxed text
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]


def font(size):
    for p in FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def dashed(draw, pts, color, width, dash=40):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        length = max(1, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        n = int(length // dash)
        for i in range(0, n, 2):
            a, b = i / n, min(1, (i + 1) / n)
            draw.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a), (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)], fill=color, width=width)


def main(spec_path):
    spec = json.load(open(spec_path))
    img = ImageOps.exif_transpose(Image.open(spec["source"])).convert("RGBA")
    img = ImageOps.fit(img, tuple(spec.get("size", [1500, 2000])))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for s in spec["shapes"]:
        if "area" in s:
            rgb = Image.new("RGB", (1, 1), s.get("color", "orange")).getpixel((0, 0))
            od.polygon([tuple(p) for p in s["area"]], fill=rgb + (s.get("alpha", 90),))
    img = Image.alpha_composite(img, overlay)
    d = ImageDraw.Draw(img)
    f = font(spec.get("font_size", 56))
    for s in spec["shapes"]:
        if "line" in s:
            pts = [tuple(p) for p in s["line"]]
            if s.get("dashed"):
                dashed(d, pts, s.get("color", "red"), s.get("width", 10))
            else:
                d.line(pts, fill=s.get("color", "red"), width=s.get("width", 10), joint="curve")
        elif "label" in s:
            x, y = s["at"]
            box = d.textbbox((x, y), s["label"], font=f)
            d.rectangle((box[0] - 12, box[1] - 8, box[2] + 12, box[3] + 8), fill=(0, 0, 0, 200))
            d.text((x, y), s["label"], font=f, fill=s.get("color", "white"))
    img.convert("RGB").save(spec["output"], quality=88)
    print(spec["output"])


if __name__ == "__main__":
    main(sys.argv[1])
