"""Sweep the seated-guest offset and stack the candidates into one comparison sheet."""
import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright

url = pathlib.Path("bench_rush.html").resolve().as_uri()

FILL = """
(async () => {
  S.left = 9999;
  for (let i = 0; i < 6; i++) { const b = hintBench(); if (!b) break; seat(b);
    await new Promise(r => setTimeout(r, 60)); }
  await new Promise(r => setTimeout(r, 600));
})()
"""

CANDS = [(.33, -.05, 1.0), (.33, .04, 1.0), (.36, -.05, .94), (.30, -.05, 1.0)]

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1180, "height": 1180})
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=15000)
    shots = []
    for dx, dz, sc in CANDS:
        pg.evaluate("load(6)")
        pg.wait_for_timeout(150)
        pg.evaluate("([dx,dz,sc]) => { SEAT_DX = dx; SEAT_DZ = dz; SEAT_SC = sc; }", [dx, dz, sc])
        pg.evaluate(FILL)
        pg.wait_for_timeout(900)
        pg.evaluate("draw()")
        name = "sw_%s_%s_%s.png" % (dx, dz, sc)
        pg.locator("canvas").screenshot(path=name)
        shots.append((("dx %.2f dz %.2f sc %.2f" % (dx, dz, sc)), name))
        print("shot", name)
    br.close()

ims = [Image.open(n).convert("RGB") for _, n in shots]
w = 620
tiles = [im.resize((w, int(im.height * w / im.width))) for im in ims]
sheet = Image.new("RGB", (w * len(tiles), tiles[0].height), (240, 244, 250))
for i, t in enumerate(tiles):
    sheet.paste(t, (i * w, 0))
sheet.save("seat_sweep.png")
print("seat_sweep.png", sheet.size, [l for l, _ in shots])
