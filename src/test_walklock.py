"""Sample repeatedly through a boarding sequence: exactly one seat should be
locked while somebody walks, and every other seat should keep its moves."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../index.html").resolve().as_uri()
JS = """
(() => {
  const locked = S.seats.filter(b => b.locked).map(b => b.id);
  const movable = S.seats.filter(b => !FIXED(b) && placements(S, b).length).length;
  // what the same board would allow with nobody walking
  const save = S.anim; S.anim = [];
  const flags = S.seats.map(b => b.locked); S.seats.forEach(b => b.locked = false);
  const idle = S.seats.filter(b => !FIXED(b) && placements(S, b).length).length;
  S.seats.forEach((b, i) => b.locked = flags[i]); S.anim = save;
  return { walkers: S.anim.length, locked, movable, idle };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("startLevel(30)"); pg.wait_for_timeout(300)
    print("%-7s %-8s %-10s %-9s %s" % ("t(ms)", "walkers", "locked", "movable", "if nobody walked"))
    samples = 0; bad = 0; cost = 0; cost = 0
    for t in range(0, 6000, 250):
        pg.wait_for_timeout(250)
        r = pg.evaluate(JS)
        if r["walkers"]:
            samples += 1
            if len(r["locked"]) != r["walkers"]: bad += 1
            if r["movable"] != r["idle"]: cost += 1
        print("%-7d %-8d %-10s %-9d %d" % (t, r["walkers"], r["locked"], r["movable"], r["idle"]))
    print("\nsamples with somebody walking: %d" % samples)
    print("samples where more than one seat was locked : %d  (must be 0)" % bad)
    print("a person on a seat cost it its last move : %d" % cost)
    print("errors:", errs[:3] or "none")
    br.close()
