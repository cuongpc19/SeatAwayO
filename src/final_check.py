import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright

url = pathlib.Path("bench_rush.html").resolve().as_uri()

WIN = """
(async () => {
  S.left = 9999;
  let g = 0;
  while (S.phase === "play" && S.queue.length && g++ < 400) {
    const b = hintBench(); if (!b) break;
    seat(b); await new Promise(r => setTimeout(r, 45));
  }
  await new Promise(r => setTimeout(r, 900));
  return S.phase;
})()
"""

with sync_playwright() as pw:
    br = pw.chromium.launch()
    errs = []
    for mode in ("light", "dark"):
        pg = br.new_page(viewport={"width": 1180, "height": 1250}, color_scheme=mode)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(url)
        pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=15000)
        pg.evaluate("load(90)")
        pg.wait_for_timeout(300)
        pg.evaluate("(async()=>{S.left=9999;for(let i=0;i<7;i++){const b=hintBench();if(!b)break;seat(b);"
                    "await new Promise(r=>setTimeout(r,60));}})()")
        pg.wait_for_timeout(1000)
        pg.screenshot(path="final_%s.png" % mode, full_page=True)
        print(mode, "shot; body scrollWidth", pg.evaluate("document.body.scrollWidth"))
        pg.close()

    # win overlay
    pg = br.new_page(viewport={"width": 1180, "height": 1000})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=15000)
    pg.evaluate("load(5)")
    pg.wait_for_timeout(200)
    print("win result:", pg.evaluate(WIN))
    pg.wait_for_timeout(400)
    pg.locator(".stage").screenshot(path="final_win.png")

    # lose-by-timeout
    pg.evaluate("load(30); S.left = 1.2;")
    pg.wait_for_timeout(2200)
    print("timeout phase:", pg.evaluate("S.phase"), "|", pg.evaluate("document.getElementById('ov-text').textContent"))

    # mobile width
    m = br.new_page(viewport={"width": 390, "height": 844})
    m.goto(url)
    m.wait_for_function("typeof ready !== 'undefined' && ready", timeout=15000)
    m.wait_for_timeout(500)
    m.screenshot(path="final_mobile.png", full_page=True)
    print("mobile scrollWidth", m.evaluate("document.body.scrollWidth"), "(viewport 390)")
    print("errors:", errs or "none")
    br.close()

a = Image.open("final_light.png")
a.crop((0, 0, 1180, 340)).save("fin_top.png")
Image.open("final_win.png").save("fin_win.png")
print("done")
