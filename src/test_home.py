"""The two screens ported from Marble Sort: the home screen and the results card.

Both lay out in a 540 x 1160 design box scaled to the frame, so what is worth
checking is not a pixel but a relationship - nothing off the screen, nothing off
the card, and the ladder the feature bar counts down to.
"""
import pathlib
from playwright.sync_api import sync_playwright

url = pathlib.Path("../game.html").resolve().as_uri()
FRAMES = {"phone 430x932": (430, 932), "tall 360x800": (360, 800),
          "desktop 1440x900": (1440, 900), "landscape phone 844x390": (844, 390)}

BOX = """el => { const r = document.getElementById(el).getBoundingClientRect();
   return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; }"""

with sync_playwright() as pw:
    br = pw.chromium.launch()
    errs = []

    for name, (w, h) in FRAMES.items():
        pg = br.new_page(viewport={"width": w, "height": h})
        pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
        pg.evaluate("save.unlocked = 23; save.coins = 1240; save.stars = {1:3,2:2}; refreshHome()")
        pg.wait_for_timeout(200)
        art = pg.evaluate(BOX, "h-cover")
        play, wal = pg.evaluate(BOX, "h-play"), pg.evaluate(BOX, "h-levels")
        onscreen = lambda b: b[0] >= 0 and b[1] >= 0 and b[2] <= w and b[3] <= h
        print("%-22s play %-22s %s" % (name, pg.locator("#h-play").inner_text(),
              "on screen" if onscreen(play) and onscreen(wal) else "OFF SCREEN %s %s" % (play, wal)))
        # A frame taller than the design box leaves a band above and below the
        # art; it is painted with the cover's own ramp, so what matters is that
        # it stays small rather than that it is zero.
        band = max(0, art[1]) + max(0, h - art[3])
        print("%-22s art %s  %d%% of the frame wide, %dpx of ground above and below"
              % ("", art, round(100 * (art[2] - art[0]) / w), round(band)))
        print("%-22s wallet %s  stars %s  gold %s" % ("", pg.evaluate(BOX, "h-stars"),
              pg.locator("#h-stars").inner_text(), pg.locator("#h-coins").inner_text()))
        pg.close()

    # ---- the ladder the bar counts down to ----
    pg = br.new_page(viewport={"width": 430, "height": 932})
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    print("\nwhat the card counts down to:")
    for f in pg.evaluate("featureLevels()"):
        print("   %-14s level %d" % (f["label"], f["at"]))
    print("progress:", ", ".join(
        "%d->%s" % (n, (lambda p: p and "%s %d%%" % (p["id"], round(p["pct"] * 100)))(
            pg.evaluate("n => featureProgress(n)", n)))
        for n in (1, 6, 7, 9, 13, 14)))

    # ---- everything on the card, inside the card ----
    print("\nthe card holds its contents:")
    for label, js in (
        ("win, bar and streak", "save.unlocked=5; save.streak=3; startLevel(5); "
                                "S.left=S.time*.8; S.seated=S.total; S.queue.length=0; finish(true)"),
        ("win, no bar left",    "save.unlocked=20; save.streak=0; startLevel(20); "
                                "S.left=S.time*.8; S.seated=S.total; S.queue.length=0; finish(true)"),
        ("loss",                "save.unlocked=12; startLevel(12); S.left=.01; finish(false)")):
        pg.evaluate(js); pg.wait_for_timeout(4500)
        panel = pg.evaluate("""() => { const r = document.querySelector('#c-card .panel u')
            .getBoundingClientRect(); return [r.top, r.bottom]; }""")
        rows = {i: pg.evaluate(BOX, i) for i in ("c-title", "c-next", "c-home")
                if not pg.evaluate("i => $(i).hidden", i)}
        out = [i for i, b in rows.items() if b[1] < panel[0] - 1 or b[3] > panel[1] + 1]
        print("   %-20s %s  bar %-24s %s" % (
            label, pg.locator("#c-title").inner_text(),
            pg.locator("#c-feat-lab").inner_text() if not pg.evaluate("$('c-feat').hidden") else "-",
            "all inside the panel" if not out else "OUTSIDE: " + ", ".join(out)))
    br.close()
print("\nerrors:", errs[:5] or "none")
