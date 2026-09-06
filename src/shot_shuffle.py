"""The line stepping up, five frames across one shuffle.

Run in slow motion (SPEED scales every walking time in the engine, launches
included) because a step at full pace is 300 ms and a screenshot is not much
quicker than that, so at 1x the strip would be five pictures of one moment.
"""
import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright
url = pathlib.Path("../game.html").resolve().as_uri()
SLOW, SHOTS, EVERY = 0.22, 5, 480

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 460, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=25000)
    pg.evaluate("SPEED = %r" % SLOW)
    pg.evaluate("startLevel(7)")
    pg.wait_for_function("S && S.qstep", timeout=20000)      # the first place has opened
    frames = []
    for i in range(SHOTS):
        f = "shuffle_%d.png" % i
        pg.locator("#board").screenshot(path=f)
        frames.append((f, pg.evaluate("S.qstep ? S.qstep.map(s => +placesBack(s, performance.now()).toFixed(2)) : null")))
        pg.wait_for_timeout(EVERY)
    print("errors:", errs[:3] or "none")
    br.close()

# The lane at the stop is the right-hand third; strip them left to right.
crops = []
for f, back in frames:
    im = Image.open(f).convert("RGB")
    crops.append(im.crop((int(im.width * .52), 0, im.width, int(im.height * .72))))
    print("%-14s places still to walk: %s" % (f, back))
w, h = crops[0].size
strip = Image.new("RGB", (w * len(crops), h), (20, 24, 50))
for i, c in enumerate(crops):
    strip.paste(c, (i * w, 0))
strip.save("shuffle_strip.png")
print("shuffle_strip.png", strip.size)
