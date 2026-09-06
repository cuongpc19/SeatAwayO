"""How much does the composition move between board sizes? If the carriage lands
in roughly the same screen rect every time, one background plate is enough."""
import pathlib, collections, json
from playwright.sync_api import sync_playwright
url = pathlib.Path("../game.html").resolve().as_uri()

JS = """
(() => {
  const g = S, T = .90;
  const x0 = cellW(-.5) - T, x1 = cellW(g.W - 1 + .5) + T;
  const z0 = cellZ(-.5) - T, z1 = cellZ(g.H - 1 + .5) + T;
  const A = P(x0, 0, z0), B = P(x1, 0, z1);
  const laneX = cellW(g.W - 1) + SX * 2.0;
  const L = P(laneX, 0, cellZ(g.door));
  return { W: g.W, H: g.H,
           left: A[0] / cv.width, right: B[0] / cv.width,
           top: A[1] / cv.height, bot: B[1] / cv.height,
           lane: L[0] / cv.width,
           scale: +LAY.s.toFixed(2),
           cw: cv.width, ch: cv.height };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 440, "height": 880})
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    B = json.load(open("lv/boards_campaign.json"))
    seen, rows = set(), []
    for i, b in enumerate(B):
        if b["variant"]: continue
        key = (b["w"], b["h"])
        if key in seen: continue
        seen.add(key)
        pg.evaluate("n => startLevel(n)", len([x for x in B[:i+1] if not x["variant"]]))
        pg.wait_for_timeout(90)
        rows.append(pg.evaluate(JS))
    rows.sort(key=lambda r: (r["W"], r["H"]))
    print("canvas %dx%d css px\n" % (rows[0]["cw"], rows[0]["ch"]))
    print("%-7s %-8s %-8s %-8s %-8s %-8s %s" % ("board", "left", "right", "top", "bottom", "lane", "scale"))
    for r in rows:
        print("%dx%-5d %-8.3f %-8.3f %-8.3f %-8.3f %-8.3f %.1f"
              % (r["W"], r["H"], r["left"], r["right"], r["top"], r["bot"], r["lane"], r["scale"]))
    for k in ("left", "right", "top", "bot", "lane"):
        v = [r[k] for r in rows]
        print("%-6s spread %.3f  (min %.3f  max %.3f)" % (k, max(v) - min(v), min(v), max(v)))
    sc = [r["scale"] for r in rows]
    print("scale  ratio  %.2fx  (min %.1f  max %.1f)" % (max(sc) / min(sc), min(sc), max(sc)))
    br.close()
