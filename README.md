# Elk Butchering 101

A field guide and freezer log for breaking down big game at home, built while butchering the 2026 GMU 681 bull.

- **Cut guide**: every cut by quarter, where to find it, the steps to remove it, and what to make of it (`data/cuts.json`).
- **Hunt logs**: harvest and handling notes, lessons, annotated photos and the freezer log for each animal (`data/hunts/`).
- **Annotated photos**: cut lines drawn on real photos (`photos/`, made with `tools/annotate.py`).
- **Web app**: `index.html` shows all of it. Runs on Kassandra at http://10.98.1.210:8090.

## Run

```sh
docker compose up -d      # nginx on :8090, serves this folder read-only
```

## Photo guidance (Break down tab)

Pick a quarter, send a photo of the piece on the hook, and Claude names the landmarks and the next cut and draws it on the photo.
`server/guide_api.py` runs as the user service `elk-guide` (127.0.0.1:8091); nginx proxies `/api/` to it. It calls `claude -p`
with read-only tools, using the Claude login on Kassandra. Uploaded photos stay in `uploads/` (not in git).

The elk on the cut map (`img/elk.webp`) was generated locally with RealVisXL (SDXL) on the RTX 4070 (`~/ai/sdxl/gen.py`)
and cut out with rembg. The mask `img/elk-mask.png` trims the cut regions to the animal.

## Install on a phone (https)

nginx serves the app on **https://10.98.1.210:8443** (and still on http :8090). The certificate comes from a
home CA in `~/.local/share/elk-ca` (not in git; `ca.key` is owner-only). The CA is name-constrained to
Kassandra's addresses, so a phone that trusts it trusts nothing else with it. `setup.html` walks a phone
through installing `elk-ca.crt` and adding the app to the home screen. Over https the app gets a service worker
(`sw.js`: opens offline), the manifest (home screen, full screen) and the real Wake Lock.

The server certificate lasts 397 days (until Dec 2027). To renew, from `~/.local/share/elk-ca`:

```sh
openssl x509 -req -in server.csr -CA elk-ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 397 -sha256 -extfile ext.cnf
docker compose restart web   # from the repo
```

## At the carcass (Break down tab)

Pick the piece on the hook. **Next cut** shows that cut zoomed on the piece's photo with big numbered steps;
the bar at the bottom has **Done** (then a sheet to undo or log packages to `freezer-log.csv` via `POST /api/log`)
and **📷 Ask** (camera straight to Claude; the marked-up photo opens full screen). Photos pinch, wheel or
double-tap to zoom. The screen is kept on while a piece is open (Wake Lock needs https, so on this LAN page a
tiny silent looping video, `img/keepawake.mp4`, does it). If the Wi-Fi drops, the page keeps its last data, and
Done and package logs are saved on the phone and sent when it's back. Ask Claude needs the network.

## Quarter photos and outlines

In the app: **Photos → ＋ Add photos** (outside, inside, other, or a 360° set). The server saves the photo,
cuts it out, and for a view has Claude draft the outlines (`POST /api/photo`, progress at `GET /api/job/<id>`).
Drafts show a banner: **Looks right**, **Fix outlines** (tap an outline, drag its corners, change which cut it
is), **Redraw** (with a note for Claude) or **Delete photo** (`POST /api/view`). By hand, as before:

Each physical piece (front shoulder #1, #2, hindquarter #1, #2) is listed under `pieces` in
`data/hunts/<hunt>/hunt.json` with its own `done` and `in_progress` cuts, so the two shoulders are tracked
separately. "Mark done" in the app writes there through `POST /api/done`. A primal with no pieces listed
(backstrap, tenderloin) uses `done_cuts`.

A piece's `views` are cut-out photos with the cuts outlined on them:

```sh
# raw photos go in photos/<hunt>/raw/ (not in git); @x0,y0,x1,y1 erases a box of junk first
uv run --with "rembg[cpu]" --with scipy --with opencv-python-headless tools/cutout.py photos/2026-elk/cut s2-outside=photos/2026-elk/raw/s2-outside.jpg
```

It prints the `img` and `box` for the view. Region points are in the photo shrunk to fit 1500x2000
(the same coordinates as annotate.py), so outlines drawn on the original photo line up:

```json
{"id": "outside", "label": "Outside", "img": "photos/2026-elk/cut/s2-outside.webp", "box": [275, 0, 656, 1862],
 "regions": [{"type": "cut", "cut": "fore-shank", "pts": [[455,40],[580,30],[700,690],[540,780]]},
             {"type": "landmark", "name": "Blade cartilage", "note": "Leave it on.", "pts": [[...]]},
             {"type": "line", "name": "Blade ridge", "note": "Slice along it.", "pts": [[...]]}]}
```

For a 360 view, shoot 12 photos while turning the hanging piece about 30° each time (phone at the same spot),
cut each one out, and list them in order as `"spin": {"frames": ["...webp", ...]}` on the piece.

## Annotate a photo

```sh
python3 tools/annotate.py spec.json
```

```json
{"source": "photos/2026-elk/shoulder_outside.jpg", "output": "photos/2026-elk/clod.jpg",
 "shapes": [{"area": [[400,600],[900,600],[900,1100],[400,1100]], "color": "orange"},
            {"line": [[300,1400],[1100,1450]], "color": "red", "dashed": true},
            {"label": "CUT 4: CLOD", "at": [420, 520]}]}
```

## Roadmap

- Freezer inventory: mark packages as eaten.
- More animals: deer (GMU 511/681 tags), antelope.
