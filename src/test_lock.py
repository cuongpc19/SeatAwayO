"""While a passenger is walking, their target seat must not budge - and neither
   may another seat be slid across the floor they are crossing."""
import pathlib
from playwright.sync_api import sync_playwright

url = pathlib.Path("../level_player.html").resolve().as_uri()
TO_CLIENT = ("([c,r]) => { const [x,y] = P(cellW(c), 0, cellZ(r));"
             " const rect = cv.getBoundingClientRect();"
             " return [rect.left + x/cv.width*rect.width, rect.top + y/cv.height*rect.height]; }")

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=25000)

    # a board with a long walk, so there is time to interfere
    pg.evaluate("SPEED = 0.5; load(45)")
    pg.wait_for_function("S && S.anim.length > 0", timeout=10000)
    pg.wait_for_timeout(120)

    st = pg.evaluate("""() => {
      const locked = S.seats.filter(b => b.locked).map(b => b.id);
      return { locked, walkCells: S.walkCells ? [...S.walkCells] : null,
               targetPlacements: locked.length ? placements(S, S.seats[locked[0]]).length : -1 };
    }""")
    print("locked seats while walking :", st["locked"])
    print("legal moves for that seat  :", st["targetPlacements"], "(must be 0)")
    print("floor tiles held for the walk:", len(st["walkCells"] or []))

    sid = st["locked"][0]
    before = pg.evaluate("s => [S.seats[s].c, S.seats[s].r]", sid)
    pos = pg.evaluate(TO_CLIENT, before)
    pg.mouse.move(pos[0], pos[1]); pg.mouse.down()
    picked = pg.evaluate("S.sel ? S.sel.id : null")
    pg.mouse.move(pos[0] - 80, pos[1] + 40, steps=5)
    pg.mouse.up()
    after = pg.evaluate("s => [S.seats[s].c, S.seats[s].r]", sid)
    print("\ntried to drag the target seat: picked up =", picked,
          "| position", before, "->", after,
          "|", "HELD" if before == after else "MOVED")

    # once they are seated the same seat is free to move again
    pg.wait_for_function("S && S.anim.length === 0 && !S.boarding", timeout=25000)
    n = pg.evaluate("s => placements(S, S.seats[s]).length", sid)
    lk = pg.evaluate("s => S.seats[s].locked", sid)
    free = pg.evaluate("s => { const b = S.seats[s]; let n = 0;"
                       " for (const [c,r] of cellsOf(b)) for (const [dc,dr] of DIRS)"
                       "   if (isFree(S, c+dc, r+dr)) n++; return n; }", sid)
    print("after they sit: locked =", lk, "| legal moves =", n,
          "| free tiles touching that seat =", free)
    anyseat = pg.evaluate("S.seats.filter(b=>!b.locked && placements(S,b).length).length")
    print("seats that can move at all now :", anyseat, "of", pg.evaluate("S.seats.length"))
    print("walkCells cleared           :", pg.evaluate("S.walkCells === null"))
    print("errors:", errs[:3] or "none")
    br.close()
