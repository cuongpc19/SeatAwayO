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
  const X = A[0] + (B[0] - A[0]) * 0.70, Y = A[1] + (B[1] - A[1]) * 0.70;
  return { from: [box.left + A[0]/kx, box.top + A[1]/ky],
           to:   [box.left + X/kx,    box.top + Y/ky],
           home: [b.c, b.r], target: t, len: b.len, dir: b.dir,
           screenGap: Math.hypot(B[0]-A[0], B[1]-A[1]) / kx };
})(%d)
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1400})
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    cv_box = pg.locator("#board")
    cv_box.scroll_into_view_if_needed()
    pg.wait_for_timeout(200)
    pg.evaluate("INSTANT = true")
    shown = 0
    for L in (14, 20, 60, 120):
        n = pg.evaluate("L => { load(L); return S.seats.length; }", L)
        for i in range(n):
            pg.evaluate("L => load(L)", L); pg.wait_for_timeout(20)
            p = pg.evaluate(PT % i)
            if not p: continue
            pg.mouse.move(*p["from"]); pg.mouse.down()
            pg.mouse.move(p["to"][0], p["to"][1], steps=8)
            st = pg.evaluate("""HELD ? {id: HELD.seat.id, moved: HELD.moved, dx: +HELD.dx.toFixed(2),
                                 dz: +HELD.dz.toFixed(2), nt: HELD.targets.length,
                                 at: dropAt().map(v => +v.toFixed(2)), drop: dropCell()} : null""")
            pg.mouse.up(); pg.wait_for_timeout(30)
            now = pg.evaluate("i => [S.seats[i].c, S.seats[i].r]", i)
            if now != p["target"] and shown < 8:
                shown += 1
                print("L%-4d seat%-3d len%d dir%d home%s -> target%s  gap %.0fpx" %
                      (L, i, p["len"], p["dir"], p["home"], p["target"], p["screenGap"]))
                print("        HELD:", st, " landed", now)
    br.close()
