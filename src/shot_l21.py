"""Photograph one campaign level as the player meets it, and report what is on it."""
import pathlib, sys
from playwright.sync_api import sync_playwright

LEVEL = int(sys.argv[1]) if len(sys.argv) > 1 else 21
url = pathlib.Path("../index.html").resolve().as_uri()

REPORT = """
() => {
  const cap = {}, want = {};
  for (const b of S.seats) {
    const n = b.colour === 0 ? "grey->" + colName(GREY_TAKES) : colName(b.colour);
    cap[n] = (cap[n] || 0) + b.len;
  }
  for (const c of S.queue) want[colName(c)] = (want[colName(c)] || 0) + 1;
  return { board: S.name, w: S.W, h: S.H, door: S.door, time: S.time,
           queue: S.queue.length, total: S.total, seated: S.seated,
           pieces: S.seats.length, places: S.seats.reduce((a, b) => a + b.len, 0),
           fixed: S.seats.filter(FIXED).length, cap, want };
}
"""

with sync_playwright() as pw:
    br = pw.chromium.launch()
    for tag, vp in (("phone", {"width": 460, "height": 900}),
                    ("desk", {"width": 1180, "height": 900})):
        pg = br.new_page(viewport=vp)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url + "?level=" + str(LEVEL))
        pg.wait_for_function("typeof BOOTED !== 'undefined' && BOOTED", timeout=20000)
        ok = pg.query_selector("#intro-ok")
        if ok and ok.is_visible():
            ok.click()
        pg.wait_for_timeout(2600)
        pg.screenshot(path="l%d_%s.png" % (LEVEL, tag))
        if tag == "phone":
            r = pg.evaluate(REPORT)
            for k, v in r.items():
                print("  %-8s %s" % (k, v))
        print("l%d_%s.png  errors: %s" % (LEVEL, tag, errs or "none"))
        pg.close()
    br.close()
