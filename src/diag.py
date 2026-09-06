import pathlib, json
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
JS = """
(() => {
  const ci = S.queue[0];
  const reg = reachRegion(S);
  let acc = 0, touch = 0, entries = 0, reach = 0;
  for (let i = 0; i < reg.length; i++) reach += reg[i];
  for (const b of S.seats) {
    if (!accepts(b, ci)) continue;
    acc++;
    const e = entryCells(S, b); entries += e.length;
    if (touches(S, b, reg)) touch++;
  }
  const grid = [];
  for (let r = 0; r < S.H; r++) {
    let row = "";
    for (let c = 0; c < S.W; c++) {
      const id = S.occ[idx(S, c, r)];
      row += S.hole[idx(S,c,r)] ? "#" : id >= 0 ? String(S.seats[id].dir) : (reg[idx(S,c,r)] ? "+" : ".");
    }
    grid.push(row);
  }
  return { id: S.id, W: S.W, H: S.H, door: S.door, queue0: ci, seats: S.seats.length,
           accepting: acc, touching: touch, entryCells: entries, reachable: reach,
           doorFree: isFree(S, S.W - 1, S.door), grid };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page()
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    for L in (10, 20, 90, 250, 14):
        pg.evaluate("INSTANT = true"); pg.evaluate("L => load(L)", L); pg.wait_for_timeout(60)
        r = pg.evaluate(JS)
        print("--- load(%d) %s  %dx%d door=%d doorFree=%s queue0=%s" %
              (L, r["id"], r["W"], r["H"], r["door"], r["doorFree"], r["queue0"]))
        print("    seats %d, accepting colour %s: %d, of those touching reachable floor: %d; reachable tiles %d"
              % (r["seats"], r["queue0"], r["accepting"], r["touching"], r["reachable"]))
        for row in r["grid"]: print("      " + row)
    br.close()
