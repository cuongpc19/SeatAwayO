"""Can a seat actually be dragged, and how many seats on a board can move at all?"""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()

STATS = """
(() => {
  const per = S.seats.map(b => placements(S, b).length);
  const free = S.W * S.H - S.hole.reduce((a,v)=>a+v,0) - S.seats.reduce((a,b)=>a+b.len,0);
  return { seats: S.seats.length, free,
           movable: per.filter(n => n > 0).length,
           frozen: per.filter(n => n === 0).length,
           moves: per.reduce((a,b)=>a+b,0) };
})()
"""
PT = """
(id => {
  const b = S.seats[id], box = cv.getBoundingClientRect();
  const [sx, sz] = seatCentre(b);
  const [px, py] = P(sx, 0, sz);
  const t = placements(S, b)[0];
  if (!t) return null;
  const [tx, tz] = (() => { const s = { ...b, c: t[0], r: t[1] }; 
    const n = (b.len - 1) / 2;
    return b.dir & 1 ? [cellW(t[0]), cellZ(t[1]) + n * SZ] : [cellW(t[0]) + n * SX, cellZ(t[1])]; })();
  const [qx, qy] = P(tx, 0, tz);
  const kx = cv.width / box.width, ky = cv.height / box.height;
  return { from: [box.left + px/kx, box.top + py/ky],
           to:   [box.left + qx/kx, box.top + qy/ky],
           home: [b.c, b.r], target: t };
})(%d)
"""

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1000})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)

    print("%-6s %-5s %-5s %-8s %-7s %s" % ("level", "seats", "free", "movable", "frozen", "legal moves"))
    for L in (1, 14, 20, 60, 120, 250, 388, 480, 600):
        pg.evaluate("INSTANT = true"); pg.evaluate("L => load(L)", L); pg.wait_for_timeout(60)
        s = pg.evaluate(STATS)
        print("%-6d %-5d %-5d %-8d %-7d %d" % (L, s["seats"], s["free"], s["movable"], s["frozen"], s["moves"]))

    # a real drag with real mouse events, on the first seat that can move
    pg.evaluate("INSTANT = true"); pg.evaluate("load(120)"); pg.wait_for_timeout(80)
    n = pg.evaluate("S.seats.length")
    done = False
    for i in range(n):
        p = pg.evaluate(PT % i)
        if not p: continue
        pg.mouse.move(*p["from"]); pg.mouse.down()
        pg.mouse.move(p["to"][0], p["to"][1], steps=12)
        pg.mouse.up(); pg.wait_for_timeout(120)
        now = pg.evaluate("i => [S.seats[i].c, S.seats[i].r]", i)
        print("\ndrag seat %d  %s -> aimed %s  landed %s   %s"
              % (i, p["home"], p["target"], now, "MOVED" if now != p["home"] else "DID NOT MOVE"))
        done = True
        break
    if not done: print("\nno seat on this board had a legal placement")
    print("errors:", errs[:3] or "none")
    br.close()
