"""Serve the local DYA trial independently of Windows registry MIME mappings."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class DyaHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".css": "text/css",
        ".svg": "image/svg+xml",
        ".json": "application/json",
        ".wasm": "application/wasm",
    }

    def send_head(self):
        # Do not reuse the prior server's cached text/plain module response.
        for header in ("If-Modified-Since", "If-None-Match"):
            if header in self.headers:
                del self.headers[header]
        return super().send_head()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    root = args.directory.resolve(strict=True)
    if not (root / "index.html").is_file():
        parser.error("DYA index.html not found")
    with ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(DyaHandler, directory=str(root))
    ) as server:
        server.serve_forever()
