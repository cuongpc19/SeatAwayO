"""Drag a seat across the board and count how many tiles change colour on the way."""
import pathlib
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
TO_CLIENT = ("([c,r]) => { const [x,y] = P(cellW(c), 0, cellZ(r));"
             " const rect = cv.getBoundingClientRect();"
             " return [rect.left + x/cv.width*rect.width, rect.top + y/cv.height*rect.height]; }")
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=25000)
    pg.evaluate("load(45)")
    pg.wait_for_function("S && !S.boarding && S.anim.length === 0", timeout=20000)
    pg.wait_for_timeout(400)
    print("board settled: seated", pg.evaluate("S.seated"), "of", pg.evaluate("S.total"))
    sid = pg.evaluate("S.seats.findIndex(b=>placements(S,b).length)")
    start = pg.evaluate(TO_CLIENT, pg.evaluate("s=>[S.seats[s].c,S.seats[s].r]", sid))
    pg.mouse.move(start[0], start[1]); pg.mouse.down()
    pg.wait_for_timeout(200)
    pg.locator(".stage").screenshot(path="dg_hold.png")
    frames = []
    for k in range(6):
        pg.mouse.move(start[0] - 30 - k*22, start[1] + k*16)
        pg.wait_for_timeout(90)
        pg.locator(".stage").screenshot(path="dg_%d.png" % k)
        frames.append("dg_%d.png" % k)
    pg.mouse.up()
    diffs = []
    for i in range(1, len(frames)):
        a = Image.open(frames[i-1]).convert("RGB"); b = Image.open(frames[i]).convert("RGB")
        bbox = ImageChops.difference(a, b).getbbox()
        diffs.append(0 if bbox is None else (bbox[2]-bbox[0]) * (bbox[3]-bbox[1]))
    print("changed-pixel area between consecutive drag frames:", diffs)
    print("(0 = the board is completely still while the cursor moves)")
    print("errors:", errs[:3] or "none")
    br.close()
