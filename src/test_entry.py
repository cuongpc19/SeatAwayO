"""Nobody may take a seat by stepping in from directly behind it."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=25000)
    pg.evaluate("INSTANT = true")

    bad = checked = 0
    for L in range(1, 121):
        pg.evaluate("L => load(L)", L)
        r = pg.evaluate("""() => {
          let behind = 0, cells = 0;
          for (const b of S.seats) {
            const e = entryCells(S, b);
            cells += e.length;
            const own = new Set(cellsOf(b).map(([c,r]) => c+","+r));
            for (const [c, r] of cellsOf(b)) {
              const k = c + "," + (r + 1);
              if (!own.has(k) && e.some(([x,y]) => x === c && y === r + 1)) behind++;
            }
          }
          return { behind, cells, seats: S.seats.length };
        }""")
        checked += 1
        bad += r["behind"]
    print("levels checked            :", checked)
    print("entry tiles behind a seat :", bad, "(must be 0)")

    # what it costs: how many riders can still board with no drag at all
    pg.evaluate("load(45)")
    n = pg.evaluate("""() => { let k = 0; while (S.queue.length) { const s = pickSeat(S, S.queue[0]);
      if (!s) break; sendToSeat ? 0 : 0; S.queue.shift(); s.occ.push(0); k++; } return k; }""")
    print("riders reachable on L45 without moving anything:", n)
    print("errors:", errs[:3] or "none")
    br.close()
