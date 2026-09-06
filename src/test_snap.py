"""Drag every movable seat on several boards a short, sloppy distance toward a
legal cell and check it actually lands there."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()

PT = """
(id => {
  const b = S.seats[id], t = placements(S, b)[0];
  if (!t) return null;
  const box = cv.getBoundingClientRect(), kx = cv.width / box.width, ky = cv.height / box.height;
  const n = (b.len - 1) / 2;
  const ctr = (c, r) => b.dir & 1 ? [cellW(c), cellZ(r) + n * SZ] : [cellW(c) + n * SX, cellZ(r)];
  const [ax, az] = ctr(b.c, b.r), [bx, bz] = ctr(t[0], t[1]);
  const A = P(ax, 0, az), B = P(bx, 0, bz);
  // deliberately stop well short of the destination - a sloppy human drag
  const X = A[0] + (B[0] - A[0]) * 0.70, Y = A[1] + (B[1] - A[1]) * 0.70;
  return { from: [box.left + A[0]/kx, box.top + A[1]/ky],
           to:   [box.left + X/kx,    box.top + Y/ky],
           home: [b.c, b.r], target: t };
})(%d)
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1400})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    cv_box = pg.locator("#board")
    cv_box.scroll_into_view_if_needed()
    pg.wait_for_timeout(200)
    tried = landed = short = 0
    for L in (14, 20, 60, 120, 250, 388, 480, 600):
        pg.evaluate("INSTANT = true"); pg.evaluate("L => load(L)", L); pg.wait_for_timeout(60)
        n = pg.evaluate("S.seats.length")
        for i in range(n):
            pg.evaluate("L => load(L)", L); pg.wait_for_timeout(20)   # fresh board each time
            p = pg.evaluate(PT % i)
            if not p: continue
            tried += 1
            pg.mouse.move(*p["from"]); pg.mouse.down()
            pg.mouse.move(p["to"][0], p["to"][1], steps=8); pg.mouse.up()
            pg.wait_for_timeout(40)
            now = pg.evaluate("i => [S.seats[i].c, S.seats[i].r]", i)
            if now == p["target"]: landed += 1
            elif now == p["home"]: short += 1
    print("sloppy drags (released 30%% short of the cell): %d" % tried)
    print("  landed on the intended cell : %d" % landed)
    print("  snapped back home           : %d" % short)
    print("  landed somewhere else       : %d" % (tried - landed - short))

    # a boxed-in seat must say so rather than silently do nothing
    pg.evaluate("load(250)"); pg.wait_for_timeout(80)
    frozen = pg.evaluate("S.seats.findIndex(b => placements(S, b).length === 0)")
    if frozen >= 0:
        p = pg.evaluate("""(id => { const b = S.seats[id], box = cv.getBoundingClientRect();
          const [sx, sz] = seatCentre(b); const [px, py] = P(sx, 0, sz);
          return [box.left + px/(cv.width/box.width), box.top + py/(cv.height/box.height)]; })(%d)""" % frozen)
        pg.mouse.move(*p); pg.mouse.down(); pg.mouse.up()
        print("\nboxed-in seat %d -> hint: %r" % (frozen, pg.evaluate("document.getElementById('hint').textContent")))
    print("errors:", errs[:3] or "none")
    br.close()
