"""The two ported screens, on a phone and on a desktop frame.

  python shot_home.py            -> home_phone.png, home_desk.png, card_*.png
"""
import pathlib, sys
from playwright.sync_api import sync_playwright

url = pathlib.Path("../game.html").resolve().as_uri()
FRAMES = {"phone": (430, 932), "desk": (1440, 900)}


def open_card(pg, level, stars=3, won=True):
    """Put the game on a level and finish it, so the card is the real one."""
    pg.evaluate("""([lvl, frac, won]) => {
        save.unlocked = lvl; save.coins = 1240; save.streak = 3;
        startLevel(lvl);
        S.left = won ? S.time * frac : 0.01;
        if (won) { S.seated = S.total; S.queue.length = 0; finish(true); }
        else finish(false);
    }""", [level, {3: .8, 2: .4, 1: .1}[stars], won])
    # the board can finish itself as the level loads and again on the line
    # above, so wait out both cards' animations rather than the first's
    pg.wait_for_timeout(4500)


with sync_playwright() as pw:
    br = pw.chromium.launch()
    errs = []
    for name, size in FRAMES.items():
        pg = br.new_page(viewport={"width": size[0], "height": size[1]})
        pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(url)
        pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
        pg.wait_for_timeout(500)
        pg.screenshot(path="home_%s.png" % name)

        # a first win, where the bar is counting down to the grey seat
        open_card(pg, 5)
        pg.screenshot(path="card_%s.png" % name)
        pg.close()

    # the card in its other states, on a phone
    pg = br.new_page(viewport={"width": 430, "height": 932})
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    open_card(pg, 6)                       # the level that opens the grey seat
    pg.screenshot(path="card_unlock.png")
    open_card(pg, 20, stars=1)
    pg.screenshot(path="card_late.png")
    open_card(pg, 12, won=False)
    pg.screenshot(path="card_lose.png")
    pg.close()
    br.close()
print("errors:", errs[:6] or "none")
