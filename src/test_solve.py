"""Is a real campaign board actually beatable? The greedy player in test_auto only
accepts a drag that seats somebody on the spot, which is exactly what a designed
puzzle refuses on move 1. This one searches a few drags deep."""
import pathlib
from playwright.sync_api import sync_playwright

url = pathlib.Path("../level_player.html").resolve().as_uri()

SOLVE = """
(async (depth, maxDrags) => {
  S.left = 1e9;
  const snap = () => S.seats.map(b => [b.c, b.r]);
  const undo = h => S.seats.forEach((b, i) => place(S, b, h[i][0], h[i][1]));
  // how many queued colours could board right now
  // only the head of the queue can board, so that is the only goal that counts
  const score = () => (S.queue.length && pickSeat(S, S.queue[0])) ? 1 : 0;
  // any drag chain up to `depth` that ends with somebody able to board
  const dig = d => {
    for (const b of S.seats) {
      if (b.locked) continue;
      for (const [c, r] of placements(S, b)) {
        const h = snap();
        place(S, b, c, r);
        if (score() > 0) return true;
        if (d > 1 && dig(d - 1)) return true;
        undo(h);
      }
    }
    return false;
  };
  let drags = 0, spin = 0;
  autoBoard(true);
  while (S.phase === "play" && S.queue.length && drags < maxDrags) {
    const before = S.seated;
    if (!dig(depth)) break;
    drags++;
    autoBoard(true);
    if (S.seated === before && ++spin > 40) break; else if (S.seated > before) spin = 0;
  }
  return { phase: S.phase, seated: S.seated, total: S.total, drags };
})(%d, 400)
"""

LEVELS = [8, 10, 14, 20, 30, 45, 60, 90, 120, 180, 250, 320, 353, 400, 480, 550, 600]
DEPTH = 2

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    won = 0
    for L in LEVELS:
        pg.evaluate("INSTANT = true"); pg.evaluate("L => load(L)", L)
        pg.wait_for_timeout(80)
        r = pg.evaluate(SOLVE % DEPTH)
        ok = r["phase"] == "win"; won += ok
        print("%s L%-4s seated %2d/%-2d  drags %3d" % ("WIN " if ok else "STUCK", L,
              r["seated"], r["total"], r["drags"]))
    print("\ndepth-%d search solved %d/%d" % (DEPTH, won, len(LEVELS)))
    print("errors:", errs[:3] or "none")
    br.close()
