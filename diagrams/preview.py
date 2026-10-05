#!/usr/bin/env python3
"""
preview.py -- render a .drawio file in a browser so you can SEE it before
shipping it.

    python3 preview.py out.drawio            # writes HTML, starts a server, prints the URL
    python3 preview.py out.drawio --port 8899
    python3 preview.py out.drawio --no-serve # just write the HTML next to the file

The XML is inlined into the page, so there is no fetch and no CORS problem.
The page loads diagrams.net's official embed viewer, which renders exactly what
draw.io will render -- including the Azure icons, which a generic XML or SVG
renderer will not resolve.

Open the printed URL with a browser tool, screenshot each page, and look for
the things a generator cannot detect: labels on top of shapes, edges through
container headings, text clipped at a page edge.

The viewer needs a few seconds to boot -- wait ~20s before the first
screenshot. If it opens at 1% zoom and a blank canvas, the browser pane had no
size when the viewer initialised: reload the URL and it fits correctly.
"""
import argparse
import http.server
import json
import os
import socketserver
import threading
from pathlib import Path

TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<title>%(title)s</title>
<style>html,body{margin:0;height:100%%}iframe{border:0;width:100vw;height:100vh}</style>
<iframe id="f" src="https://embed.diagrams.net/?embed=1&proto=json&ui=min&spin=1&libraries=1&noSaveBtn=1&noExitBtn=1"></iframe>
<script>
const XML = %(xml)s;
window.addEventListener('message', (e) => {
  if (typeof e.data !== 'string') return;
  let m; try { m = JSON.parse(e.data); } catch { return; }
  if (m.event === 'init') {
    document.getElementById('f').contentWindow.postMessage(
      JSON.stringify({ action: 'load', xml: XML }), '*');
  }
});
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("drawio")
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--no-serve", action="store_true")
    args = ap.parse_args()

    src = Path(args.drawio).resolve()
    html = TEMPLATE % {"title": src.stem, "xml": json.dumps(src.read_text(encoding="utf-8"))}
    out = src.with_suffix(".preview.html")
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}")

    if args.no_serve:
        print(f"open file://{out}")
        return

    os.chdir(out.parent)
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", args.port), handler)
    print(f"serving http://localhost:{args.port}/{out.name}   (ctrl-c to stop)")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
