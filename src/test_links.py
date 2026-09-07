"""The address bar: ?level, ?reset, ?win - do they land where they say?

Needs the local server: `python serve.py` from the repo root, then this. The
built page is loaded over http rather than file:// because ?reset has to prove it
edits a real address bar, and history.replaceState throws on a file URL.
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080/"
READY = "typeof BOOTED !== 'undefined' && BOOTED"
KEY = "seatmatch.save.v1"
OLD = "takeaseat.save.v1"           # the name before the game was called Seat Match

errs = []


def check(ok, msg):
    if not ok:
        errs.append(msg)
    print("  %s %s" % ("ok  " if ok else "FAIL", msg))


def state(pg):
    return pg.evaluate("""() => ({
      screen: ['home','levels','play'].find(id => document.getElementById(id).classList.contains('on')),
      level: CUR, unlocked: save.unlocked, coins: save.coins,
      stars: save.stars, search: location.search,
      keys: Object.keys(localStorage).filter(k => k.indexOf('save.v') > 0).sort() })""")


def open_at(pg, query="", wait=400):
    pg.goto(BASE + query)
    pg.wait_for_function(READY, timeout=20000)
    pg.wait_for_timeout(wait)
    return state(pg)


with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 420, "height": 860})

    print("-- ?level=N --")
    open_at(pg)
    pg.evaluate("save.unlocked = 30; save.coins = 4200; save.stars = {1:3,2:2}; persist()")

    s = open_at(pg, "?level=1")
    check(s["screen"] == "play" and s["level"] == 1, "?level=1 opens board 1: %s / %s"
          % (s["screen"], s["level"]))
    # past the unlock gate: the picker only lists what has been earned, and 200 has not been
    s = open_at(pg, "?level=200")
    check(s["screen"] == "play" and s["level"] == 200, "?level=200 opens a locked board: %s / %s"
          % (s["screen"], s["level"]))
    check(s["unlocked"] == 30, "and does not unlock it: unlocked %s" % s["unlocked"])
    for q in ("?level=abc", "?level=0", "?level=-3"):
        s = open_at(pg, q)
        check(s["screen"] == "home", "%s falls back to the home screen: %s" % (q, s["screen"]))

    print("\n-- ?win=1 --")
    s = open_at(pg, "?level=3&win=1", wait=2200)   # past the 1.2s celebration beat
    card = pg.evaluate("document.getElementById('card').classList.contains('on')")
    check(card, "?win=1 puts the result card up without a board being solved")
    check(s["stars"].get("3") == 3, "and it is the three-star card: stars %s" % s["stars"])
    # kept in the address bar on purpose: refreshing to see it again is the whole use
    check(s["search"] == "?level=3&win=1", "win survives in the address bar: %r" % s["search"])
    s = open_at(pg, "?level=3&win=0", wait=800)
    check(not pg.evaluate("document.getElementById('card').classList.contains('on')"),
          "?win=0 writes the flag off")

    print("\n-- ?reset --")
    for q in ("?reset=1", "?reset"):
        open_at(pg)
        pg.evaluate("save.coins = 4200; save.unlocked = 30; persist()")
        s = open_at(pg, q)
        check(s["coins"] == 0 and s["unlocked"] == 1, "%s wipes the save: coins %s unlocked %s"
              % (q, s["coins"], s["unlocked"]))
        check(s["search"] == "", "%s leaves the address bar: %r" % (q, s["search"]))

    open_at(pg)
    pg.evaluate("save.coins = 4200; persist()")
    s = open_at(pg, "?reset=0")
    check(s["coins"] == 4200, "?reset=0 keeps it: coins %s" % s["coins"])

    s = open_at(pg, "?reset=1&level=1", wait=700)
    check(s["screen"] == "play" and s["level"] == 1 and s["coins"] == 0,
          "?reset=1&level=1 is a clean run from the top: %s / %s / %s coins"
          % (s["screen"], s["level"], s["coins"]))
    check(s["search"] == "?level=1", "and only reset is stripped: %r" % s["search"])

    # the flag must not survive, or every refresh wipes the run
    pg.evaluate("save.coins = 999; persist()")
    pg.reload(); pg.wait_for_function(READY, timeout=20000); pg.wait_for_timeout(300)
    check(state(pg)["coins"] == 999, "a refresh after a reset keeps what was earned since")

    print("\n-- the save key follows the name --")
    open_at(pg, "?reset=1")
    pg.evaluate("localStorage.setItem('%s', JSON.stringify({unlocked: 12, coins: 77}))" % OLD)
    s = open_at(pg)
    check(s["unlocked"] == 12 and s["coins"] == 77,
          "a save left under %s is picked up: unlocked %s coins %s" % (OLD, s["unlocked"], s["coins"]))
    check(KEY in s["keys"], "and adopted under %s: %s" % (KEY, s["keys"]))

    # a reset that left an old key standing would resurrect the save it was asked to destroy
    s = open_at(pg, "?reset=1")
    check(s["keys"] == [] or s["keys"] == [KEY], "a reset clears the old names too: %s" % s["keys"])
    s = open_at(pg)
    check(s["unlocked"] == 1 and s["coins"] == 0,
          "and the next load stays blank: unlocked %s coins %s" % (s["unlocked"], s["coins"]))

    print("\n-- the room and the plate --")
    s = open_at(pg, "?level=4&theme=cinema")
    check(pg.evaluate("THEME") == "cinema", "?theme=cinema pins the room: %s" % pg.evaluate("THEME"))

    br.close()

print("\nerrors:", "; ".join(errs) if errs else "none")
assert not errs, errs
