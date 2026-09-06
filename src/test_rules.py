"""The two rules just reported: grey seats never move, and a walker locks only
the seat they are heading for."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../game.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)

    # --- grey seats, across many boards ---
    r = pg.evaluate("""(() => {
      let grey = 0, greyMovable = 0, other = 0, otherMovable = 0;
      for (let n = 1; n <= 120; n++) {
        INSTANT = true; startLevel(n);
        for (const b of S.seats) {
          const can = placements(S, b).length > 0;
          if (b.colour === 0) { grey++; if (can) greyMovable++; }
          else { other++; if (can) otherMovable++; }
        }
      }
      return { grey, greyMovable, other, otherMovable };
    })()""")
    print("across 120 boards:")
    print("  grey seats            : %d, of which movable %d  (must be 0)" % (r["grey"], r["greyMovable"]))
    print("  other seats           : %d, of which movable %d" % (r["other"], r["otherMovable"]))

    # a real drag on a grey seat must do nothing and say so
    pg.evaluate("INSTANT = false; startLevel(13)"); pg.wait_for_timeout(400)
    g = pg.evaluate("S.seats.findIndex(b => b.colour === 0)")
    if g >= 0:
        p = pg.evaluate("""(id => { const b = S.seats[id], box = cv.getBoundingClientRect();
          const [sx, sz] = seatCentre(b); const [px, py] = P(sx, 0, sz);
          return { home: [b.c, b.r], at: [box.left + px/(cv.width/box.width),
                   box.top + py/(cv.height/box.height)] }; })(%d)""" % g)
        pg.mouse.move(*p["at"]); pg.mouse.down()
        pg.mouse.move(p["at"][0] + 90, p["at"][1], steps=8); pg.mouse.up()
        pg.wait_for_timeout(150)
        now = pg.evaluate("i => [S.seats[i].c, S.seats[i].r]", g)
        print("  dragging a grey seat  : %s -> %s  %s" % (p["home"], now,
              "STAYED (correct)" if now == p["home"] else "MOVED (bug)"))

    # --- a walker locks only its own seat ---
    w = pg.evaluate("""(() => {
      startLevel(30);
      return new Promise(res => setTimeout(() => {
        const walking = S.seats.filter(b => b.locked).length;
        const free = S.seats.filter(b => !b.locked && !FIXED(b) && placements(S, b).length).length;
        const movableIfIdle = S.seats.filter(b => !FIXED(b)).length;
        res({ walkers: S.anim.length, locked: walking, movable: free, colourSeats: movableIfIdle });
      }, 1600));
    })()""")
    print("\nwhile somebody is walking (level 30):")
    print("  walkers on the floor  : %d" % w["walkers"])
    print("  seats locked          : %d  (should equal the walkers)" % w["locked"])
    print("  colour seats movable  : %d of %d" % (w["movable"], w["colourSeats"]))
    print("errors:", errs[:3] or "none")
    br.close()
