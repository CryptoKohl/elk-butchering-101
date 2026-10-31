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

- Upload a photo in the app and have a vision model (local Ollama on Kassandra or Claude) name the cut and draw the next line.
- Freezer inventory: mark packages as eaten.
- More animals: deer (GMU 511/681 tags), antelope.
