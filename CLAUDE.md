# Elk Butchering 101 — notes for Claude

This repo is Lance's butchering playbook and log. When Lance is breaking down an animal:

1. Find the quarter and the next cut in `data/cuts.json` (`primals[].order` is the cutting order).
2. Lance sends a photo. Identify the landmarks first (blade ridge, cartilage, elbow, femur, knee), say which cut is next, and **show it**: draw the cut on Lance's own photo with `tools/annotate.py` (spec JSON: source, output, shapes) and send the image.
3. Give tight, numbered, one-action-at-a-time steps. No extra "why" unless asked.
4. Lance can log packages in the app (Done → sheet), which appends to `freezer-log.csv`. When Lance reports packages to you instead, add a row to `data/hunts/<hunt>/freezer-log.csv` and to the matching Dremur document (2026: "Elk 2026 Freezer Log"), then commit.
5. Track cuts per piece in `pieces` in `hunt.json` (shoulder #1 and #2 separately). New photos of a piece: cut them out with `tools/cutout.py` and add them as `views` with outlined regions (see README).
6. Anything learned the hard way goes in `lessons` in `data/hunts/<hunt>/hunt.json`.

Tracking lives in Dremur project **Elk Butchering 101** (app build) and task "Part out and butcher the elk" in Hunting 2026 (the 2026 animal).

Hosting: Kassandra (10.98.1.210), served by nginx at http://10.98.1.210:8090 from `~/projects/elk-butchering-101` (see `compose.yaml`).

Known mistakes to avoid: the pale rubbery edge at the bottom of a front shoulder hung by the shank is the blade cartilage, not a brisket flap.
