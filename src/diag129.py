import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
JS = """
(() => {
  const rows = S.seats.map(b => ({ id: b.id, at: [b.c, b.r], len: b.len, dir: b.dir,
      colour: b.colour, locked: b.locked, occ: b.occ.slice(),
      n: placements(S, b).length, to: placements(S, b).slice(0, 6) }));
  let grid = [];
  for (let r = 0; r < S.H; r++) { let s = "";
    for (let c = 0; c < S.W; c++) { const id = S.occ[idx(S,c,r)];
      s += S.hole[idx(S,c,r)] ? "#" : id >= 0 ? String.fromCharCode(65+id) : "."; }
    grid.push(s); }
  return { name: S.name, W: S.W, H: S.H, door: S.door, queue: S.queue.length,
           seated: S.seated, total: S.total, phase: S.phase,
           walkCells: S.walkCells ? [...S.walkCells] : null,
           anim: S.anim.length, rows, grid };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1400})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("load(129)")
    for wait, tag in ((150, "right after load"), (4000, "after 4s of boarding")):
        pg.wait_for_timeout(wait)
        r = pg.evaluate(JS)
        print("=== %s  %s  %dx%d door=%d  seated %d/%d  queue %d  walkers %d"
              % (tag, r["name"], r["W"], r["H"], r["door"], r["seated"], r["total"], r["queue"], r["anim"]))
        for g in r["grid"]: print("     " + g)
        print("     walkCells:", r["walkCells"])
        for x in r["rows"]:
            print("     %s at%s len%d occ%s locked=%s -> %d places %s"
                  % (chr(65+x["id"]), x["at"], x["len"], x["occ"], x["locked"], x["n"], x["to"]))
        print()
    print("errors:", errs[:3] or "none")
    br.close()
