"""Drag every seat on level 129, the way a hand does it: aim at the destination
but release a little short of the cell centre."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()

PT = """
(([id, ti, slop]) => {
  const b = S.seats[id], ts = placements(S, b);
  const t = ts[ti]; if (!t) return null;
  const box = cv.getBoundingClientRect(), kx = cv.width / box.width, ky = cv.height / box.height;
  const n = (b.len - 1) / 2;
  const ctr = (c, r) => b.dir & 1 ? [cellW(c), cellZ(r) + n * SZ] : [cellW(c) + n * SX, cellZ(r)];
  const [ax, az] = ctr(b.c, b.r), [bx, bz] = ctr(t[0], t[1]);
  const A = P(ax, 0, az), B = P(bx, 0, bz);
  const X = A[0] + (B[0] - A[0]) * slop, Y = A[1] + (B[1] - A[1]) * slop;
  return { from: [box.left + A[0]/kx, box.top + A[1]/ky],
           to:   [box.left + X/kx,    box.top + Y/ky],
           home: [b.c, b.r], target: t, locked: b.locked };
})(%s)
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1400})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.locator("#board").scroll_into_view_if_needed(); pg.wait_for_timeout(200)

    ok = fail = skip = 0
    bad = []
    for slop in (0.6, 0.8, 1.0):
        for ti in (0, 1, 2):
            pg.evaluate("INSTANT = true; load(129)"); pg.wait_for_timeout(120)
            n = pg.evaluate("S.seats.length")
            for i in range(n):
                p = pg.evaluate(PT % [i, ti, slop])
                if not p: skip += 1; continue
                pg.mouse.move(*p["from"]); pg.mouse.down()
                pg.mouse.move(p["to"][0], p["to"][1], steps=10); pg.mouse.up()
                pg.wait_for_timeout(30)
                now = pg.evaluate("i => [S.seats[i].c, S.seats[i].r]", i)
                if now == p["target"]: ok += 1
                else:
                    fail += 1
                    if len(bad) < 6: bad.append((slop, i, p["home"], p["target"], now, p["locked"]))
    print("level 129, drags attempted: %d" % (ok + fail))
    print("  landed on the aimed cell : %d" % ok)
    print("  did not move             : %d" % fail)
    print("  seats with no such place : %d (skipped)" % skip)
    for b_ in bad: print("   slop=%.1f seat%d %s -> %s landed %s locked=%s" % b_)
    print("errors:", errs[:3] or "none")
    br.close()
