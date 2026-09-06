"""Two ways a seat used to stay stuck to the cursor:
   1. the hit box was far taller than the sprite, so pressing the seat behind
      grabbed the seat in front;
   2. a pointerup delivered off-canvas was never heard, so the seat kept
      following a cursor with no button held down."""
import pathlib
from playwright.sync_api import sync_playwright

url = pathlib.Path("../level_player.html").resolve().as_uri()

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1200, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("INSTANT = true; load(120)")
    pg.wait_for_timeout(200)
    print("alpha map:", pg.evaluate("ALPHA ? ALPHA.w + 'x' + ALPHA.h : 'MISSING'"))

    # --- 1. every seat: pressing its own centre must pick that same seat ---
    CENTRES = """
    (() => {
      const box = cv.getBoundingClientRect();
      return S.seats.map(b => {
        const [sx, sz] = seatCentre(b);
        const [px, py] = P(sx, 0, sz);
        return { id: b.id, x: box.left + px / (cv.width / box.width),
                            y: box.top  + py / (cv.height / box.height) };
      });
    })()
    """
    pts = pg.evaluate(CENTRES)
    wrong = []
    for p in pts:
        got = pg.evaluate("([x,y]) => { const b = pickSeatAt(x,y); return b ? b.id : null; }",
                          [p["x"], p["y"]])
        if got != p["id"]:
            wrong.append((p["id"], got))
    print("seats whose own centre picks a different seat: %d / %d" % (len(wrong), len(pts)), wrong[:6])

    # --- 2. release off-canvas, then move the mouse: nothing may follow it ---
    p0 = pts[0]
    pg.mouse.move(p0["x"], p0["y"]); pg.mouse.down()
    pg.mouse.move(p0["x"] + 60, p0["y"] + 40, steps=6)
    held_mid = pg.evaluate("HELD ? HELD.seat.id : null")
    pg.mouse.move(5, 5, steps=4)          # off the board
    pg.mouse.up()                         # released outside the canvas
    pg.mouse.move(p0["x"] + 200, p0["y"], steps=6)
    held_after = pg.evaluate("HELD ? HELD.seat.id : null")
    print("held while dragging: %s   held after off-canvas release + move: %s"
          % (held_mid, held_after))

    # --- 3. press seat A, release, press seat B: B must be the one in hand ---
    a, b = pts[0], pts[len(pts) // 2]
    pg.mouse.move(a["x"], a["y"]); pg.mouse.down()
    pg.mouse.move(a["x"] + 30, a["y"], steps=4); pg.mouse.up()
    pg.mouse.move(b["x"], b["y"]); pg.mouse.down()
    now = pg.evaluate("HELD ? HELD.seat.id : null")
    pg.mouse.up()
    print("pressed seat %s after having dragged seat %s -> in hand: %s  %s"
          % (b["id"], a["id"], now, "OK" if now == b["id"] else "WRONG"))

    print("errors:", errs[:3] or "none")
    br.close()
