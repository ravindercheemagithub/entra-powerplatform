#!/usr/bin/env bash
# Export every page of both .drawio files to PNG (needs the draw.io desktop app).
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-png}"; mkdir -p "$OUT"
DRAWIO=/Applications/draw.io.app/Contents/MacOS/draw.io
for f in entra-powerplatform entra-powerplatform-future; do
  n=$(grep -c '<diagram ' "$f.drawio")
  for i in $(seq 1 "$n"); do "$DRAWIO" -x -f png -p "$i" -s 1.5 -o "$OUT/$f-$i.png" "$f.drawio" >/dev/null 2>&1; done
  echo "exported $n pages of $f to $OUT/"
done
