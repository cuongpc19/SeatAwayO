"""What the coached boards actually look like, phone and desktop."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../game.html").resolve().as_uri()
SETTLED = "() => !S || S.phase !== 'play' || (!S.anim.length && !S.boarding)"

with sync_playwright() as pw:
    br = pw.chromium.launch()
    for tag, vp in (("phone", {"width": 420, "height": 860}),
                    ("desk", {"width": 1180, "height": 900})):
        pg = br.new_page(viewport=vp)
        pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
        pg.evaluate("save.unlocked = 2; persist()")
        for lvl in (1, 2):
            pg.evaluate("n => startLevel(n)", lvl)
            pg.wait_for_function(SETTLED, timeout=15000); pg.wait_for_timeout(500)
            pg.screenshot(path="tut_%s_l%d.png" % (tag, lvl))
            print("tut_%s_l%d.png  coach=%s" % (tag, lvl,
                  not pg.evaluate("document.getElementById('coach').hidden")))
        pg.close()
    br.close()
