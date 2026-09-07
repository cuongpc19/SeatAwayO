from PIL import Image
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:8080/?theme=cinema")
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("save.unlocked = 60; save.coins = 5000; save.hearts = 4; startLevel(60)")
    pg.wait_for_timeout(1400)
    pg.screenshot(path="boost_idle.png")
    pg.click("#b-jump"); pg.wait_for_timeout(400)
    pg.screenshot(path="boost_armed.png")
    print("errors:", errs[:3] or "none")
    br.close()
a = Image.open("boost_idle.png"); b = Image.open("boost_armed.png")
k = .40
A = a.resize((int(a.width*k), int(a.height*k))); B = b.resize((int(b.width*k), int(b.height*k)))
sh = Image.new("RGB", (A.width, A.height + B.height + 6), (8, 8, 11))
sh.paste(A, (0, 0)); sh.paste(B, (0, A.height + 6)); sh.save("boost_cmp.png"); print(sh.size)
