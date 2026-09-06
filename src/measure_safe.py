"""Where the seat grid actually lands on a painted plate, across every board size
and both screen shapes."""
import json
from playwright.sync_api import sync_playwright
JS = """
(() => {
  const g = S;
  const A = P(cellW(-.5), 0, cellZ(-.5)), B = P(cellW(g.W - 1 + .5), 0, cellZ(g.H - 1 + .5));
  const L = P(cellW(g.W - 1) + SX * 2.0, 0, cellZ(g.door));
  return { W: g.W, H: g.H, l: A[0]/cv.width, r: B[0]/cv.width,
           t: A[1]/cv.height, b: B[1]/cv.height, lane: L[0]/cv.width };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch()
    B = json.load(open("lv/boards_campaign.json"))
    firsts, seen = [], set()
    n = 0
    for b in B:
        if b["variant"]: continue
        n += 1
        if (b["w"], b["h"]) in seen: continue
        seen.add((b["w"], b["h"])); firsts.append((n, b["w"], b["h"]))
    for tag, vp in (("phone 430x860", {"width": 430, "height": 860}),
                    ("desk 1440x900", {"width": 1440, "height": 900})):
        pg = br.new_page(viewport=vp)
        pg.goto("http://127.0.0.1:8080/game.html")
        pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
        rows = []
        for n, w, h in firsts:
            pg.evaluate("n => startLevel(n)", n); pg.wait_for_timeout(70)
            rows.append(pg.evaluate(JS))
        print("== %s ==" % tag)
        for k, lab in (("l", "grid left"), ("r", "grid right"), ("lane", "queue lane"),
                       ("t", "grid top"), ("b", "grid bottom")):
            v = [x[k] for x in rows]
            print("  %-11s %5.1f%% .. %5.1f%%   (spread %.1f pts)"
                  % (lab, min(v)*100, max(v)*100, (max(v)-min(v))*100))
        pg.close()
    br.close()
