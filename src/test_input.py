"""Drive the page with real mouse events, aiming where a person would aim:
   the seat itself, and the head of the passenger sitting on it."""
import pathlib
from playwright.sync_api import sync_playwright

url = pathlib.Path("../level_player.html").resolve().as_uri()

PROBE = """
(sid) => {
  const b = S.seats[sid];
  const [c, r] = cellsOf(b)[0];
  const [px, py] = P(cellW(c), 0, cellZ(r));
  const rect = cv.getBoundingClientRect();
  const toClient = (x, y) => [rect.left + x / cv.width * rect.width,
                              rect.top + y / cv.height * rect.height];
  return { tile: toClient(px, py),
           seat: toClient(px, py - SX * 0.34 * LAY.s),
           head: toClient(px, py - SX * 0.92 * LAY.s),
           occupied: b.occ.length > 0,
           targets: placements(S, b).length };
}
"""
TO_CLIENT = ("([c,r]) => { const [x,y] = P(cellW(c), 0, cellZ(r));"
             " const rect = cv.getBoundingClientRect();"
             " return [rect.left + x/cv.width*rect.width, rect.top + y/cv.height*rect.height]; }")

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("load(14)")
    pg.wait_for_timeout(1400)

    ids = pg.evaluate("({occ: S.seats.findIndex(b=>b.occ.length), free: S.seats.findIndex(b=>!b.occ.length)})")
    print("seat with rider:", ids["occ"], "  empty seat:", ids["free"])

    for label, sid in (("empty seat", ids["free"]), ("seat with rider", ids["occ"])):
        for aim in ("tile", "seat", "head"):
            pg.evaluate("clearSel()")
            info = pg.evaluate(PROBE, sid)
            if aim == "head" and not info["occupied"]:
                continue
            x, y = info[aim]
            pg.mouse.move(x, y); pg.mouse.down()
            picked = pg.evaluate("S.sel ? S.sel.id : null")
            pg.mouse.up()
            print("  %-16s aim at %-5s -> picked %s   targets %d"
                  % (label, aim, picked, info["targets"]))

    pg.evaluate("clearSel()")
    sid = ids["occ"]
    info = pg.evaluate(PROBE, sid)
    before = pg.evaluate("s => [S.seats[s].c, S.seats[s].r]", sid)
    tgt = pg.evaluate("s => placements(S, S.seats[s])[0]", sid)
    dest = pg.evaluate(TO_CLIENT, tgt)
    pg.mouse.move(info["head"][0], info["head"][1]); pg.mouse.down()
    pg.mouse.move(dest[0], dest[1], steps=8); pg.mouse.up()
    after = pg.evaluate("s => [S.seats[s].c, S.seats[s].r]", sid)
    print("\ndrag grabbing the rider's head : %s -> %s  (target %s)  moves=%s"
          % (before, after, tgt, pg.evaluate("S.moves")))

    pg.evaluate("clearSel()")
    sid = ids["free"]
    b4 = pg.evaluate("s => [S.seats[s].c, S.seats[s].r]", sid)
    info = pg.evaluate(PROBE, sid)
    pg.mouse.click(info["seat"][0], info["seat"][1])
    sel = pg.evaluate("S.sel ? S.sel.id : null")
    t2 = pg.evaluate("s => placements(S, S.seats[s])[0]", sid)
    d2 = pg.evaluate(TO_CLIENT, t2)
    pg.mouse.click(d2[0], d2[1])
    a2 = pg.evaluate("s => [S.seats[s].c, S.seats[s].r]", sid)
    print("tap seat then tap tile        : selected %s, %s -> %s  (target %s)" % (sel, b4, a2, t2))

    pg.evaluate("clearSel(); load(30)")
    pg.wait_for_timeout(1200)
    pg.evaluate("selectSeat(S.seats[0])")
    pg.wait_for_timeout(150)
    pg.locator(".stage").screenshot(path="input_sel.png")
    print("errors:", errs[:3] or "none")
    br.close()
