"""The clock: the seconds the marked boards carry, and when it starts running.

  - HARD boards get +15s and SUPER HARD +45s, on both the clock and the budget
    the stars are scored against.
  - Nothing counts down until a passenger steps off the stop, or - where nobody
    can move - until the player commits their first seat."""
import json, pathlib
from playwright.sync_api import sync_playwright

url = pathlib.Path("../index.html").resolve().as_uri()
RAW = json.load(open("lv/boards_campaign.json", encoding="utf-8"))
CAMP = [b for b in RAW if b.get("variant") == 0]
BONUS = {0: 0, 1: 15, 2: 45}
# ⚠ Read out of build.py, not written down again. Every clock in the game is
# already lifted by EXTRA_SECONDS at build time - a second copy of that number
# here would pass today and quietly lie the day it is retuned.
import re
EXTRA = int(re.search(r"^EXTRA_SECONDS\s*=\s*(\d+)", open("build.py", encoding="utf-8").read(),
                      re.M).group(1))
print("build.py adds %ds to every clock; the grades add %s on top" % (EXTRA, BONUS))
print()

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 460, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    pg.wait_for_function("typeof BOOTED !== 'undefined' && BOOTED", timeout=20000)
    pg.evaluate("save.unlocked = 60; persist()")

    print("=== the extra seconds ===")
    bad = 0
    for n in (8, 9, 15, 18, 19, 21, 25, 29, 35, 39):
        want = CAMP[n - 1]["time"] + EXTRA + BONUS[CAMP[n - 1].get("diff", 0)]
        pg.evaluate("n => startLevel(n)", n)
        pg.wait_for_timeout(120)
        got = pg.evaluate("({time: S.time, left: Math.round(S.left)})")
        ok = got["time"] == want and got["left"] == want
        bad += not ok
        print("  level %-3d %-6s apk %4ds +%2d build +%2d grade -> %4ds   got %4d/%4d  %s" % (
            n, {0: ".", 1: "HARD", 2: "SUPER"}[CAMP[n - 1].get("diff", 0)],
            CAMP[n - 1]["time"], EXTRA, BONUS[CAMP[n - 1].get("diff", 0)], want,
            got["left"], got["time"], "ok" if ok else "WRONG"))

    print("=== the clock holds until something moves ===")
    # A board the queue can walk straight into: the clock starts on its own.
    pg.evaluate("startLevel(3)")
    pg.wait_for_timeout(120)
    t0 = pg.evaluate("({run: RUNNING, left: S.left})")
    pg.wait_for_timeout(2600)
    t1 = pg.evaluate("({run: RUNNING, left: S.left, moving: S.anim.length > 0 || S.seated > 0})")
    print("  open board  : running %s -> %s   spent %.1fs   somebody moved: %s" % (
        t0["run"], t1["run"], t0["left"] - t1["left"], t1["moving"]))

    # A board nobody can leave the stop on: it must sit still until a seat moves.
    HELDBOARD = """() => {
      startLevel(3);
      // wall the doorway in, so no passenger can reach a seat at all
      S.queue.length = 0; S.boarding = false; S.anim.length = 0;
      RUNNING = false;
      return S.left;
    }"""
    before = pg.evaluate(HELDBOARD)
    pg.wait_for_timeout(2000)
    still = pg.evaluate("({run: RUNNING, left: S.left})")
    pg.evaluate("S.moves = 1")            # the player commits a seat
    pg.wait_for_timeout(1200)
    after = pg.evaluate("({run: RUNNING, left: S.left})")
    print("  nobody moving: held %.2fs of clock (running %s)" % (before - still["left"], still["run"]))
    print("  after a seat : running %s, spent %.1fs" % (after["run"], still["left"] - after["left"]))

    print("errors:", errs or "none")
    print("RESULT:", "ok" if not bad and not errs else "PROBLEMS")
    br.close()
