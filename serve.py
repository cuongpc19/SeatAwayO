"""Local test server.

The plain http.server hands the browser a cached copy on every reload, which is
how a stale build ends up on screen looking like a bug that was already fixed.
This one forbids caching outright.
"""
import http.server, socketserver, os, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
os.chdir(os.path.dirname(os.path.abspath(__file__)))

LOG = "gesture.log"

class NoCache(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        """The page posts one line per gesture so a real mouse can be debugged."""
        if self.path != "/log":
            return self.send_error(404)
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", "replace")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(" ".join(body.split()) + "\n")   # one gesture per line
        self.send_response(204); self.end_headers()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()
    def send_header(self, key, value):
        if key.lower() in ("last-modified", "etag"): return   # nothing to revalidate against
        # Without a charset the browser falls back to the system codepage and every
        # dash and middot in the page turns to mojibake.
        if key.lower() == "content-type" and value.startswith("text/") and "charset" not in value:
            value += "; charset=utf-8"
        super().send_header(key, value)
    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % a))

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

with Server(("127.0.0.1", PORT), NoCache) as srv:
    print("http://127.0.0.1:%d/            the game     (no-cache)" % PORT, flush=True)
    print("http://127.0.0.1:%d/level_player.html  the editor" % PORT, flush=True)
    srv.serve_forever()
