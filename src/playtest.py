"""Drive the prototype in a real browser: screenshot, then auto-play a few levels."""
import pathlib, sys
from playwright.sync_api import sync_playwright

url = pathlib.Path("bench_rush.html").resolve().as_uri()

AUTOPLAY = """
(async (maxMoves) => {
  const log = [];
  for (let i = 0; i < maxMoves; i++) {
    if (S.phase !== "play") break;
    if (!S.queue.length) break;
    const c = S.queue[0];
    const b = S.benches.find(b => legal(b, c));
    if (!b) { log.push("stuck at seated=" + S.seated); break; }
    seat(b);
    await new Promise(r => setTimeout(r, 60));
  }
  return { phase: S.phase, seated: S.seated, total: S.total, left: Math.round(S.left),
           queue: S.queue.length, log };
})(400)
"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1180, "height": 1100})
    errs = []
    pg.on("console", lambda m: errs.append(m.type + ": " + m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=15000)
    pg.wait_for_timeout(600)
    pg.screenshot(path="game_l1.png")
    print("errors after load:", errs or "none")

    for lvl in (1, 12, 40, 120, 400):
        pg.evaluate("L => load(L)", lvl)
        pg.wait_for_timeout(350)
        p = pg.evaluate("({w:S.W,h:S.H,benches:S.benches.length,total:S.total,"
                        "colours:S.colours,time:S.time,"
                        "grey:S.benches.filter(b=>b.colour==='grey').length,"
                        "wide:S.benches.filter(b=>b.w>1).length})")
        print("L%-4d %dx%d  benches %2d  seats %2d  colours %d  grey %2d  wide %2d  %ds"
              % (lvl, p["w"], p["h"], p["benches"], p["total"], p["colours"],
                 p["grey"], p["wide"], p["time"]))
        if lvl == 40:
            pg.screenshot(path="game_l40.png")
        res = pg.evaluate(AUTOPLAY)
        print("      autoplay ->", res)

    pg.evaluate("load(40)")
    pg.wait_for_timeout(400)
    pg.screenshot(path="game_l40.png")
    print("errors total:", errs or "none")
    b.close()
