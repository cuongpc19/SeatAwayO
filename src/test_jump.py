"""A real drag with the jump booster armed: a seat with nowhere to slide should
land across the board, and exactly one charge should go."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../game.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("save.unlocked = 60; save.coins = 5000; startLevel(60)"); pg.wait_for_timeout(600)

    stuck = pg.evaluate("""(() => {
      for (const b of S.seats) {
        if (FIXED(b) || b.locked) continue;
        if (placements(S, b).length) continue;
        JUMP = true; const n = placements(S, b).length; JUMP = false;
        if (n) return { id: b.id, at: [b.c, b.r], jumpTargets: n };
      }
      return null;
    })()""")
    if not stuck:
        print("no boxed-in seat on this board to demonstrate with"); br.close(); raise SystemExit
    print("seat %d at %s: 0 places to slide, %d to jump to"
          % (stuck["id"], stuck["at"], stuck["jumpTargets"]))

    g0 = pg.evaluate("save.coins")
    pg.click("#b-jump"); pg.wait_for_timeout(200)
    print("armed %s, charges %d, gold %d -> %d"
          % (pg.evaluate("JUMP"), pg.evaluate("save.jumps"), g0, pg.evaluate("save.coins")))

    p = pg.evaluate("""(id => {
      const b = S.seats[id], t = placements(S, b)[0];
      const box = cv.getBoundingClientRect(), kx = cv.width/box.width, ky = cv.height/box.height;
      const n = (b.len - 1) / 2;
      const ctr = (c, r) => b.dir & 1 ? [cellW(c), cellZ(r) + n*SZ] : [cellW(c) + n*SX, cellZ(r)];
      const [ax, az] = ctr(b.c, b.r), [bx, bz] = ctr(t[0], t[1]);
      const A = P(ax, 0, az), B = P(bx, 0, bz);
      return { target: t, from: [box.left+A[0]/kx, box.top+A[1]/ky],
               to: [box.left+B[0]/kx, box.top+B[1]/ky] };
    })(%d)""" % stuck["id"])
    pg.mouse.move(*p["from"]); pg.mouse.down()
    pg.mouse.move(p["to"][0], p["to"][1], steps=12); pg.mouse.up()
    pg.wait_for_timeout(250)
    now = pg.evaluate("i => [S.seats[i].c, S.seats[i].r]", stuck["id"])
    print("dragged %s -> aimed %s, landed %s   %s"
          % (stuck["at"], p["target"], now, "JUMPED" if now == p["target"] else "FAILED"))
    print("after the move: armed %s, charges %d  (one spent, arming cleared)"
          % (pg.evaluate("JUMP"), pg.evaluate("save.jumps")))
    print("errors:", errs[:3] or "none")
    br.close()
