import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright
url = pathlib.Path("../index.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("startLevel(10)"); pg.wait_for_timeout(900)
    shots = []
    for i in range(4):
        pg.evaluate("t => { NOW = t; draw(); }", 2.0 + i * 2.4)
        pg.wait_for_timeout(120)
        n = "bird_%d.png" % i
        pg.locator(".stage").screenshot(path=n)
        shots.append(n)
    pg.screenshot(path="birds_full.png")
    print("errors:", errs[:3] or "none")
    br.close()
# a strip of just the band, to see the motion
ims = [Image.open(n) for n in shots]
band = [im.crop((0, 0, im.width, int(im.height * 0.24))) for im in ims]
k = 0.5
band = [b.resize((int(b.width * k), int(b.height * k))) for b in band]
sh = Image.new("RGB", (band[0].width, sum(b.height for b in band) + 3 * 4), (15, 18, 24))
y = 0
for b in band: sh.paste(b, (0, y)); y += b.height + 4
sh.save("birds_strip.png"); print("birds_strip.png", sh.size)
