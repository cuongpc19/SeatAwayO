from playwright.sync_api import sync_playwright
JS = """
(() => {
  const g = S, T = .90;
  const A = P(cellW(-.5) - T, 0, cellZ(-.5)), B = P(cellW(g.W - 1 + .5) + T, 0, cellZ(0));
  const L = P(cellW(g.W - 1) + SX * 2.0, 0, cellZ(g.door));
  return { left: A[0]/cv.width, right: B[0]/cv.width, lane: L[0]/cv.width };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1440, "height": 900})
    pg.goto("http://127.0.0.1:8080/game.html?theme=cinema")
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    lo = hi = None
    for n in (1, 10, 30, 96, 200, 353, 500, 600):
        pg.evaluate("n => startLevel(n)", n); pg.wait_for_timeout(70)
        r = pg.evaluate(JS)
        lo = r["left"] if lo is None else min(lo, r["left"])
        hi = r["lane"] if hi is None else max(hi, r["lane"])
        print("level %-4d room %5.1f%% .. %5.1f%%   queue %5.1f%%"
              % (n, r["left"]*100, r["right"]*100, r["lane"]*100))
    print("\nwhole composition spans %.1f%% .. %.1f%% of the window" % (lo*100, hi*100))
    br.close()
