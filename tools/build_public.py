#!/usr/bin/env python3
"""Build the public copy of the app: the one you can hand out by link.

  python3 tools/build_public.py [OUT_DIR]      (default: ../elk-101-public)

Static files only, no server: the cut guide, field dressing, and Break down with the example
photos and their outlines from hunt.json. Each person's done cuts and freezer log stay in
their own browser. Left out: Ask Claude, adding photos, the 2026 hunt diary, the freezer
log CSV, raw photos, setup.html and the home CA. Photos are re-saved without EXIF (no GPS).
"""
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "elk-101-public").resolve()


def photo(rel):
    """Copy a photo with its metadata stripped. Returns the path the page uses."""
    src, dest = ROOT / rel, OUT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    im = ImageOps.exif_transpose(Image.open(src))  # bake in the rotation before the EXIF goes
    fmt = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}[src.suffix.lower()]
    opts = {"JPEG": {"quality": 85}, "WEBP": {"quality": 82, "method": 6}, "PNG": {}}[fmt]
    (im.convert("RGB") if fmt == "JPEG" else im).save(dest, fmt, **opts)  # no exif= : metadata dropped
    return rel


def main():
    if OUT == ROOT or ROOT in OUT.parents:
        sys.exit("OUT_DIR must be outside the repo")
    for p in OUT.iterdir() if OUT.exists() else []:  # keep .git so the folder can be pushed
        if p.name != ".git":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    OUT.mkdir(parents=True, exist_ok=True)

    page = (ROOT / "index.html").read_text()
    assert page.count("<script>\n") == 1
    page = page.replace("<script>\n", "<script>window.ELK_PUBLIC = 1</script>\n<script>\n")
    (OUT / "index.html").write_text(page)
    for f in ["manifest.webmanifest", "sw.js", "data/cuts.json", "data/field.json",
              "img/elk.webp", "img/elk-mask.png", "img/keepawake.mp4", "img/icon-192.png",
              "img/icon-512.png", "img/icon-maskable-512.png", "img/apple-touch-icon.png"]:
        (OUT / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, OUT / f)

    hunt = json.loads((ROOT / "data/hunts/2026-elk/hunt.json").read_text())
    pieces = []
    for p in hunt["pieces"]:
        views = [{k: v[k] for k in ("id", "label", "img", "box", "caption", "regions") if k in v} | {"img": photo(v["img"])}
                 for v in p.get("views", []) if not v.get("draft")]
        pieces.append({"id": p["id"], "primal": p["primal"], "name": p["name"], "done": [], "in_progress": [], "views": views})
    example = {
        "title": "Example elk",
        "pieces": pieces,
        "lessons": hunt["lessons"],
        "photos": [{**ph, "file": photo(ph["file"])} for ph in hunt["photos"] if ph.get("cuts")],
        "done_cuts": [],
    }
    (OUT / "data/example.json").write_text(json.dumps(example, indent=1))
    (OUT / ".nojekyll").write_text("")
    n = sum(1 for _ in OUT.rglob("*") if _.is_file() and ".git" not in _.parts)
    print(f"built {OUT} ({n} files)")


if __name__ == "__main__":
    main()
