"""The upload bundle: does it boot with no SDK reachable, does it keep the save,
does the host's mute outrank the in-game switch, does it draw in its own faces?"""
import functools, http.server, pathlib, threading
from playwright.sync_api import sync_playwright


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


# ⚠ Served, not opened from disk. The bundle is a folder now - a page, its
# scripts, its fonts - and a page opened as a file is an origin of its own that
# Chromium will not let load fonts from beside it. Over http it is fetched the
# way the host fetches it.
srv = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(Quiet, directory=str(pathlib.Path("../dist").resolve())))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d/index.html" % srv.server_address[1]
READY = "typeof BOOTED !== 'undefined' && BOOTED"

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 420, "height": 860})
    errs, sdk_tries, google = [], [], []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("request", lambda r: google.append(r.url) if "fonts.g" in r.url else None)
    # exactly the adblocker case: the request never answers and never errors
    pg.route("**/sdk.crazygames.com/**", lambda r: (sdk_tries.append(r.request.url), r.abort()))

    pg.goto(URL); pg.wait_for_function(READY, timeout=20000)
    # ⚠ load(), not check(): a face is only fetched once text on screen needs
    # it, and the home screen sets nothing in Baloo 2 or Nunito - check() said
    # false for two faces that were there and fine.
    print("own faces           :", pg.evaluate("""async () => (await Promise.all(
        ['Lilita One', 'Baloo 2', 'Nunito'].map(async f => f + ' ' + (await document.fonts.load('700 30px "' + f + '"', 'Ab1')).length)
      )).join(', ')"""), "faces loaded | Google Fonts requests:", len(google))
    pg.wait_for_function("document.getElementById('home').classList.contains('on')", timeout=15000)
    print("SDK fetch attempted :", len(sdk_tries), sdk_tries[:1])
    print("booted anyway       :", pg.evaluate("PLATFORM.name"), "| home shown, title", repr(pg.title()))

    # progress still round-trips through the dual store
    pg.evaluate("save.unlocked = 4; save.coins = 55; persist()")
    print("wrote through door  :", pg.evaluate("JSON.parse(localStorage.getItem(SAVE_KEY))"))

    # the host's mute must silence the game even with the in-game switch on
    print("in-game sound on    :", pg.evaluate("!!save.sound"), "| host muted:", pg.evaluate("PLATFORM.hostMuted()"))
    pg.goto(URL + "?muteAudio=true"); pg.wait_for_function(READY, timeout=20000)
    pg.wait_for_function("document.getElementById('home').classList.contains('on')", timeout=15000)
    print("?muteAudio=true     : host muted:", pg.evaluate("PLATFORM.hostMuted()"),
          "| in-game switch still", pg.evaluate("!!save.sound"))

    # and it still plays
    # ⚠ boot() now waits on the host, and with the SDK blocked that wait runs the
    # full timeout - so the level is not up the instant `ready` flips.
    import time as _t
    t0 = _t.time()
    pg.goto(URL + "?level=1"); pg.wait_for_function(READY, timeout=20000)
    pg.wait_for_function("document.getElementById('play').classList.contains('on')", timeout=20000)
    # ⚠ Not "no walkers" - that is true before the board has started. The board
    # opens on a still beat and the free boarding runs after it; waiting on the
    # coach mark itself is the honest signal that the level is up and going.
    pg.wait_for_function("() => !document.getElementById('coach').hidden || S.phase !== 'play'",
                         timeout=20000)
    print("boot with no SDK    : %.1fs to the board (init timeout is 2.5s)" % (_t.time() - t0))
    print("level 1 in bundle   : level", pg.evaluate("CUR"),
          "| coach:", repr(pg.evaluate("document.getElementById('coach-title').textContent")))
    pg.screenshot(path="dist_level1.png")
    # the aborted SDK request is this test's own doing, not a fault in the page
    real = [e for e in errs if "ERR_FAILED" not in e]
    print("errors:", real or "none (the blocked SDK fetch is the test's own)")
    br.close()
