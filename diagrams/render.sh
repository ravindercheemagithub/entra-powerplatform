#!/usr/bin/env bash
# Export every page of the .drawio to PNG (needs the draw.io desktop app).
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-png}"; mkdir -p "$OUT"
DRAWIO=/Applications/draw.io.app/Contents/MacOS/draw.io
n=$(grep -c '<diagram ' entra-powerplatform.drawio)
for i in $(seq 1 "$n"); do "$DRAWIO" -x -f png -p "$i" -s 1.5 -o "$OUT/page-$i.png" entra-powerplatform.drawio >/dev/null 2>&1; done
echo "exported $n pages to $OUT/"
