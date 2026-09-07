"""The portrait screenshots CrazyGames asks for, taken from the real build.

    python store_shots.py   ->  ../store/crazygames/shot-<n>-<name>.png

Nine-by-sixteen, 1080 x 1920, which is the shape a portrait game is shown in on
their mobile placements. They are photographs of the game and not artwork: the
page is loaded, a board is opened, and the shutter goes at a moment when the
room has people in it. Nothing is drawn here that a player could not see.

⚠ Every shot waits before it fires. A board photographed on the frame it opens
is an empty room - the queue has not moved yet - and one photographed too late
is a full one with nobody walking. The waits below put the shutter in the middle
of the boarding, which is the only part of this game that moves.

⚠ The save is set up before the level is opened, not after. Reaching a level by
`?level=` leaves the walkthroughs owing, and one of them would be sitting over
the board in every picture.
"""
import os
import pathlib
from playwright.sync_api import sync_playwright

GAME = pathlib.Path(__file__).resolve().parent.parent / "index.html"
OUT = pathlib.Path(__file__).resolve().parent.parent / "store" / "crazygames"
W, H = 1080, 1920

# Nothing owed, a plausible purse, and the whole campaign reachable - the state
# of somebody who has been playing for a while, which is who the store page is
# describing.
SETUP = ("save.seenBoosters = ['grey', 'jump', 'twin', 'time'];"
         "save.coins = 2450; save.unlocked = 600; save.jumps = 2; save.freeTime = 0;"
         "save.stars = {}; persist();")

# ⚠ Home is the one shot the save shows through. `unlocked = 600` there would
# put LEVEL 600 on the button and 0 stars beside it - a player who has finished
# the game and never earned anything. This is somebody twenty-odd levels in.
HOME = ("save.seenBoosters = ['grey', 'jump', 'twin', 'time'];"
        "save.coins = 2450; save.unlocked = 24; save.jumps = 2;"
        "save.stars = {}; for (let n = 1; n < 24; n++) save.stars[n] = n % 5 ? 3 : 2;"
        "persist();")

#     file name          theme        level  wait   what it is for
SHOTS = [
    ("1-classroom", "classroom", 33,  2600, "the first room, mid-boarding"),
    ("2-station",   "station",   64,  3000, "a fuller board, walkers on the floor"),
    ("3-stadium",   "stadium",   142, 3000, "a wide board in the biggest room"),
    ("4-concert",   "concert",   173, 2800, "colour, and a long queue at the door"),
    ("5-cinema",    "cinema",    296, 2800, "the darkest room, for contrast"),
]

os.makedirs(OUT, exist_ok=True)


def shoot(pg, name, js_after=None, wait=0):
    if js_after:
        pg.evaluate(js_after)
    if wait:
        pg.wait_for_timeout(wait)
    path = OUT / ("shot-%s.png" % name)
    pg.screenshot(path=str(path))
    print("%-26s %d x %d  %.0f KB" % (path.name, W, H, path.stat().st_size / 1024))


with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1,
                     is_mobile=True, has_touch=True)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)

    def open_game(query):
        pg.goto(GAME.as_uri() + query)
        pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=30000)
        # the seats are an inlined image and the room is drawn without them
        # until it has decoded, which is a screenshot of an empty floor
        pg.wait_for_function("atlas.complete && atlas.naturalWidth > 0", timeout=30000)
        pg.wait_for_function("walkAtlas.complete && walkAtlas.naturalWidth > 0", timeout=30000)

    # ---- the home screen, which is the first thing anybody sees ----
    open_game("?reset=1")
    pg.evaluate(HOME + "show('home'); onHud();")
    shoot(pg, "0-home", wait=900)

    # ---- one board per room ----
    for name, theme, level, wait, _why in SHOTS:
        open_game("?theme=%s&level=%d" % (theme, level))
        shoot(pg, name, SETUP + "startLevel(%d);" % level, wait)

    # ---- the end of a board, won ----
    open_game("?theme=stadium&level=96")
    pg.evaluate(SETUP + "startLevel(96);")
    pg.wait_for_timeout(1500)
    # a clean finish rather than a played-out one: the card is the subject here
    pg.evaluate("S.left = S.time * 0.72; S.seated = S.total; S.queue = []; finish(true);")
    shoot(pg, "6-win", wait=2200)

    print("errors:", errs[:4] or "none")
    br.close()
