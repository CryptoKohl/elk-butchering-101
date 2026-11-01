#!/usr/bin/env bash
# Rebuild the public copy and push it to GitHub Pages (repo CryptoKohl/elk-101, public).
# Run again after adding photos or changing the guide; people's phones pick it up on the next open.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd); OUT=${OUT:-$ROOT/../elk-101-public}
uv run --with pillow python3 "$ROOT/tools/build_public.py" "$OUT"
cd "$OUT"
[ -d .git ] || { git init -q -b main; git remote add origin https://github.com/CryptoKohl/elk-101.git; git config user.name Lance; git config user.email "$(gh api user --jq .id)+CryptoKohl@users.noreply.github.com"; }
git add -A
git diff --cached --quiet && { echo "nothing changed"; exit 0; }
git commit -qm "Publish $(date +%F) from elk-butchering-101 $(git -C "$ROOT" rev-parse --short HEAD)"
git push -q origin main
echo "pushed: https://cryptokohl.github.io/elk-101/"
