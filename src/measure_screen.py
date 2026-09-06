"""Does the sheet stay fully on screen for every board size?"""
import json
from playwright.sync_api import sync_playwright
JS = """
(() => {
  const g = S, T = .90;
  const x0 = cellW(-.5), x1 = cellW(g.W - 1 + .5), z0 = cellZ(-.5);
  const sz1 = z0 - T * .95, sz0 = sz1 - SZ * 2.15;
  const a = P(x0 + SX * .10, .02, sz0), b = P(x1 - SX * .10, .02, sz1);
  return { W: g.W, H: g.H, top: a[1] / cv.height, bot: b[1] / cv.height,
           left: a[0] / cv.width, right: b[0] / cv.width };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch()
    B = [b for b in json.load(open("lv/boards_campaign.json")) if b["variant"] == 0]
    firsts, seen, n = [], set(), 0
    for b in B:
        n += 1
        if (b["w"], b["h"]) in seen: continue
        seen.add((b["w"], b["h"])); firsts.append((n, b["w"], b["h"]))
    for tag, vp in (("phone", {"width": 430, "height": 860}), ("desk", {"width": 1440, "height": 900})):
        pg = br.new_page(viewport=vp)
        pg.goto("http://127.0.0.1:8080/game.html?theme=cinema")
        pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
        worst = None
        for n, w, h in firsts:
            pg.evaluate("n => startLevel(n)", n); pg.wait_for_timeout(60)
            r = pg.evaluate(JS)
            if worst is None or r["top"] < worst["top"]: worst = r
        print("%-6s worst top edge of the sheet: %5.1f%% of the canvas  (board %dx%d)  %s"
              % (tag, worst["top"] * 100, worst["W"], worst["H"],
                 "OK" if worst["top"] > .01 else "CLIPPED"))
        pg.close()
    br.close()
