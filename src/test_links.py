"""?level= and ?reset on the live server: do they land where they say?"""
from playwright.sync_api import sync_playwright
BASE = "http://127.0.0.1:8080/game.html"
READY = "typeof ready !== 'undefined' && ready"

def state(pg):
    return pg.evaluate("""() => ({
      screen: ['home','levels','play'].find(id => document.getElementById(id).classList.contains('on')),
      level: CUR, unlocked: save.unlocked, coins: save.coins,
      stars: JSON.stringify(save.stars), url: location.search })""")

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 420, "height": 860})

    pg.goto(BASE); pg.wait_for_function(READY, timeout=20000)
    pg.evaluate("save.unlocked = 30; save.coins = 4200; save.stars = {1:3,2:2}; persist()")
    print("planted a save   :", state(pg))

    for q in ("?level=1", "?level=200", "?level=abc", "?level=0"):
        pg.goto(BASE + q); pg.wait_for_function(READY, timeout=20000); pg.wait_for_timeout(400)
        s = state(pg)
        print("%-14s -> screen %-6s level %-4s unlocked %s" % (q, s["screen"], s["level"], s["unlocked"]))

    print("\n-- reset --")
    pg.goto(BASE); pg.wait_for_function(READY, timeout=20000)
    print("before           :", state(pg))
    pg.goto(BASE + "?reset"); pg.wait_for_function(READY, timeout=20000); pg.wait_for_timeout(300)
    print("?reset           :", state(pg))
    pg.goto(BASE + "?reset&level=1"); pg.wait_for_function(READY, timeout=20000); pg.wait_for_timeout(600)
    print("?reset&level=1   :", state(pg))
    print("  coach          :", pg.evaluate("document.getElementById('coach-title').textContent"),
          "| shown:", not pg.evaluate("document.getElementById('coach').hidden"))

    # the flag must not survive, or every refresh wipes the run
    pg.evaluate("save.coins = 999; persist()")
    pg.reload(); pg.wait_for_function(READY, timeout=20000); pg.wait_for_timeout(300)
    s = state(pg)
    print("after a refresh  :", s, "  coins kept:", s["coins"] == 999)
    br.close()
