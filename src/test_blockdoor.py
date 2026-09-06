"""Parking a seat in the doorway must stall boarding and say so, then resume."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1400})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("INSTANT = true; load(129)"); pg.wait_for_timeout(200)
    before = pg.evaluate("S.seated")
    # slide seat 0 straight onto the door cell
    pg.evaluate("place(S, S.seats[0], S.W - 1, S.door); hud(); draw()")
    pg.wait_for_timeout(400)
    print("seat parked on the door cell (%d, %d)" % tuple(pg.evaluate("[S.W-1, S.door]")))
    print("  door free      :", pg.evaluate("isFree(S, S.W - 1, S.door)"))
    print("  reachable tiles:", pg.evaluate("reachRegion(S).reduce((a,v)=>a+v,0)"))
    print("  hint           :", repr(pg.evaluate("document.getElementById('hint').textContent")))
    pg.evaluate("autoBoard(true)"); pg.wait_for_timeout(300)
    print("  seated %d -> %d (must not rise)" % (before, pg.evaluate("S.seated")))
    # drag it clear again
    pg.evaluate("place(S, S.seats[0], 1, 0); hud(); autoBoard(true)"); pg.wait_for_timeout(500)
    print("\ndoor cleared -> reachable %d, seated %d, hint %r"
          % (pg.evaluate("reachRegion(S).reduce((a,v)=>a+v,0)"), pg.evaluate("S.seated"),
             pg.evaluate("document.getElementById('hint').textContent")))
    print("errors:", errs[:3] or "none")
    br.close()
