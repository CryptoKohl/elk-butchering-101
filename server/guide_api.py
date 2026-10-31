#!/usr/bin/env python3
"""Photo guidance API for Elk Butchering 101.

POST /api/guide  JSON {primal, side?, message?, image? (data URL), thread?}
  Saves the photo under uploads/<thread>/, asks Claude (claude -p, read-only tools)
  for the next cut on that quarter, draws the cut on the photo with tools/annotate.py,
  and returns the guidance plus the annotated image URL. A thread keeps one Claude
  session, so follow-up photos ("done, what next?") have the earlier context.

Listens on 127.0.0.1:8091; nginx proxies /api/ to it. One Claude run at a time.
"""
import base64
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "uploads"
CLAUDE = os.environ.get("CLAUDE_BIN", str(Path.home() / ".local/bin/claude"))
MODEL = os.environ.get("GUIDE_MODEL", "opus")
MAX_SIDE = 1200
MAX_BODY = 20 * 1024 * 1024
LOCK = threading.Lock()

sys.path.insert(0, str(ROOT / "tools"))
import annotate  # noqa: E402

PT = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
SCHEMA = {
    "type": "object",
    "properties": {
        "sees": {"type": "string", "description": "One or two sentences: what part this is, its orientation, and the landmarks you can see."},
        "next_cut_id": {"type": "string", "description": "id from the cut list of the cut to make now, or empty if unclear"},
        "steps": {"type": "array", "items": {"type": "string"}, "description": "Tight, numbered, one-action steps for the next cut only"},
        "caution": {"type": "string", "description": "A mistake to avoid right now, or empty"},
        "need": {"type": "string", "description": "If the photo is unclear, the photo you need instead; else empty"},
        "lines": {"type": "array", "items": {"type": "object", "properties": {
            "points": {"type": "array", "items": PT, "minItems": 2}, "color": {"type": "string"}, "dashed": {"type": "boolean"}},
            "required": ["points"]}},
        "areas": {"type": "array", "items": {"type": "object", "properties": {
            "points": {"type": "array", "items": PT, "minItems": 3}, "color": {"type": "string"}}, "required": ["points"]}},
        "labels": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "at": PT}, "required": ["text", "at"]}},
    },
    "required": ["sees", "next_cut_id", "steps", "caution", "need", "lines", "areas", "labels"],
}


def load(rel):
    return json.loads((ROOT / rel).read_text())


def context(primal_id, side):
    cuts, hunt = load("data/cuts.json"), load("data/hunts/2026-elk/hunt.json")
    primal = next((p for p in cuts["primals"] if p["id"] == primal_id), None)
    if not primal:
        raise ValueError("unknown primal")
    by_id = {c["id"]: c for c in cuts["cuts"]}
    order = [by_id[i] for i in primal["order"] if i in by_id]
    return primal, (
        f"Lance is breaking down an elk {primal['name'].lower()}{f' ({side})' if side else ''}.\n"
        f"Primal guide: {json.dumps({k: primal[k] for k in ('name', 'summary', 'landmarks')})}\n"
        f"Cuts in cutting order: {json.dumps(order)}\n"
        f"Cuts already done on the 2026 elk (any side): {json.dumps(hunt.get('done_cuts', []))}\n"
        f"Lessons learned: {json.dumps(hunt.get('lessons', []))}\n"
    )


RULES = (
    "You are guiding Lance at the hanging carcass. Lance uses they/them.\n"
    "1. Identify landmarks first (blade ridge, cartilage, elbow, femur, knee, seams), then name the next cut.\n"
    "2. Steps: tight, numbered, one action each. No extra 'why'. Never mention pixel coordinates in text; say 'top', 'left edge' and so on.\n"
    "3. Draw on the photo: 'lines' are knife paths (red, dashed for 'follow this seam'), 'areas' outline the cut "
    "to remove (orange), 'labels' name it in 24 characters or fewer (e.g. 'CUT 3: CLOD'). Coordinates are pixels in THIS image, "
    "origin top-left. Draw only what you can place with confidence.\n"
    "4. If the photo is too unclear to place a cut, say what photo you need in 'need' and leave drawings empty.\n"
    "Known mistake: on a shoulder hung by the shank, the pale rubbery edge at the bottom is blade cartilage, not a brisket flap.\n"
)


def save_image(data_url, dest):
    raw = base64.b64decode(data_url.split(",", 1)[-1])
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    img.save(dest, quality=88)
    return img.size


def ask_claude(workdir, prompt, session):
    cmd = [CLAUDE, "-p", "--restricted", "--strict-mcp-config", "--tools", "Read", "--model", MODEL,
           "--output-format", "json", "--json-schema", json.dumps(SCHEMA)]
    if session:
        cmd += ["--resume", session]
    with LOCK:
        out = subprocess.run(cmd + [prompt], cwd=workdir, capture_output=True, text=True, timeout=300)
    res = json.loads(out.stdout or "{}")
    if out.returncode or res.get("is_error") or not res.get("structured_output"):
        raise RuntimeError((res.get("result") or out.stderr or "Claude did not answer")[:400])
    return res["structured_output"], res.get("session_id")


def draw(src, size, g, dest):
    shapes = [{"area": a["points"], "color": a.get("color", "orange"), "alpha": 80} for a in g.get("areas", [])]
    shapes += [{"line": l["points"], "color": l.get("color", "red"), "dashed": bool(l.get("dashed")), "width": max(4, size[0] // 150)} for l in g.get("lines", [])]
    fs = max(18, size[0] // 32)
    for l in g.get("labels", []):  # keep labels short and inside the frame
        text = l["text"][:28]
        x = max(12, min(l["at"][0], size[0] - int(len(text) * fs * 0.62) - 24))
        y = max(12, min(l["at"][1], size[1] - fs - 24))
        shapes.append({"label": text, "at": [x, y]})
    if not shapes:
        return False
    spec = dest.with_suffix(".json")
    spec.write_text(json.dumps({"source": str(src), "output": str(dest), "size": list(size), "font_size": fs, "shapes": shapes}))
    annotate.main(str(spec))
    return True


def guide(body):
    thread = body.get("thread") or uuid.uuid4().hex
    if not re.fullmatch(r"[0-9a-f]{32}", thread):
        raise ValueError("bad thread")
    workdir = UPLOADS / thread
    workdir.mkdir(parents=True, exist_ok=True)
    meta_path = workdir / "thread.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"primal": body.get("primal"), "session": None, "n": 0}
    primal, ctx = context(meta["primal"] or body.get("primal"), (body.get("side") or "").strip()[:40])
    meta["n"] += 1
    n, msg = meta["n"], (body.get("message") or "").strip()[:1000]
    photo, size = None, None
    if body.get("image"):
        photo = workdir / f"in-{n}.jpg"
        size = save_image(body["image"], photo)
    if not photo and not msg:
        raise ValueError("send a photo or a message")
    parts = [] if meta["session"] else [RULES, ctx]
    if photo:
        parts.append(f"Read ./{photo.name} (a new photo, {size[0]}x{size[1]} px).")
    parts.append(f"Lance says: {msg}" if msg else "What is the next cut here?")
    if not photo:
        parts.append("No new photo: leave lines, areas and labels empty.")
    g, session = ask_claude(workdir, "\n".join(parts), meta["session"])
    meta["session"] = session or meta["session"]
    meta_path.write_text(json.dumps(meta))
    out = workdir / f"out-{n}.jpg"
    drawn = bool(photo) and draw(photo, size, g, out)
    url = lambda p: f"/uploads/{thread}/{p.name}?t={int(time.time())}"
    return {"thread": thread, "primal": primal["id"], **g,
            "photo": url(photo) if photo else None, "annotated": url(out) if drawn else None}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"ok": True}) if self.path == "/api/health" else self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/guide":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY:
            return self._send(413, {"error": "photo too large"})
        try:
            self._send(200, guide(json.loads(self.rfile.read(length))))
        except (ValueError, KeyError) as e:
            self._send(400, {"error": str(e)})
        except subprocess.TimeoutExpired:
            self._send(504, {"error": "Claude took too long. Try again."})
        except Exception as e:  # noqa: BLE001
            self._send(502, {"error": str(e)})


if __name__ == "__main__":
    UPLOADS.mkdir(exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", 8091), Handler).serve_forever()
