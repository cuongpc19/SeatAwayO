"""Local test server.

The plain http.server hands the browser a cached copy on every reload, which is
how a stale build ends up on screen looking like a bug that was already fixed.
This one forbids caching outright.

⚠ It listens on every interface, not just loopback, so a phone on the same
Wi-Fi can reach it - which is the only way to test what this game is actually
played on. Bound to 127.0.0.1 it answers the machine it runs on and nothing
else, and from the phone that looks exactly like the address being wrong.

⚠ That does mean anything on the LAN can read this directory while it runs.
It is a dev server on a home network, not a deployment; do not run it on one
you do not control.
"""
import http.server, socketserver, os, socket, sys

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

def lan_ip():
    """The address a phone on the same Wi-Fi should type.

    ⚠ Asked of a UDP socket rather than of the hostname: this machine has more
    than one adapter (a VirtualBox host-only one among them) and resolving the
    hostname can hand back whichever of them sorts first. Connecting a datagram
    socket makes the OS pick the interface it would actually route out of. No
    packet is sent."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


with Server(("", PORT), NoCache) as srv:
    print("http://127.0.0.1:%d/            the game     (no-cache)" % PORT, flush=True)
    print("http://127.0.0.1:%d/level_player.html  the editor" % PORT, flush=True)
    ip = lan_ip()
    if ip:
        print("http://%s:%d/            from a phone on the same Wi-Fi" % (ip, PORT), flush=True)
        print("  (if it does not answer, Windows Firewall is blocking the port -", flush=True)
        print("   see the netsh line in CRAZYGAMES.md)", flush=True)
    srv.serve_forever()
