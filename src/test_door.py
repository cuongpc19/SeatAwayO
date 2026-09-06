"""How much room did the reserved doorway cost? And can seat 0 on level 129 now
reach the cell the player was aiming at?"""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
STATS = """
(() => {
  const per = S.seats.map(b => placements(S, b).length);
  return { seats: S.seats.length, frozen: per.filter(n => !n).length,
           places: per.reduce((a,b)=>a+b,0), per0: placements(S, S.seats[0]) };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1400})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    print("%-7s %-6s %-8s %-8s %s" % ("level", "seats", "frozen", "places", "seat0 can reach"))
    for L in (129, 1, 14, 20, 60, 120, 250, 388, 480, 600):
        pg.evaluate("INSTANT = true"); pg.evaluate("L => load(L)", L); pg.wait_for_timeout(80)
        r = pg.evaluate(STATS)
        print("%-7d %-6d %-8d %-8d %s" % (L, r["seats"], r["frozen"], r["places"],
              r["per0"][:8] if L == 129 else ""))
    # the exact gesture from the log: grab seat 0, drop around cell (3, 2)
    pg.evaluate("INSTANT = true; load(129)"); pg.wait_for_timeout(120)
    pg.locator("#board").scroll_into_view_if_needed(); pg.wait_for_timeout(200)
    p = pg.evaluate("""(() => {
      const b = S.seats[0], box = cv.getBoundingClientRect();
      const kx = cv.width / box.width, ky = cv.height / box.height;
      const A = P(cellW(b.c), 0, cellZ(b.r));
      const B = P(cellW(3) + SX * 0.01, 0, cellZ(2) - SZ * 0.14);   // hover=[3.01,1.86]
      return { from: [box.left+A[0]/kx, box.top+A[1]/ky],
               to:   [box.left+B[0]/kx, box.top+B[1]/ky], home: [b.c, b.r] }; })()""")
    pg.mouse.move(*p["from"]); pg.mouse.down()
    pg.mouse.move(p["to"][0], p["to"][1], steps=12); pg.mouse.up(); pg.wait_for_timeout(60)
    print("\nreplay of your gesture: seat0 %s -> %s   %s"
          % (p["home"], pg.evaluate("[S.seats[0].c, S.seats[0].r]"),
             "MOVED" if pg.evaluate("[S.seats[0].c, S.seats[0].r]") != p["home"] else "STILL STUCK"))
    print("errors:", errs[:3] or "none")
    br.close()
