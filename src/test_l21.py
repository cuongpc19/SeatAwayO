"""Can level 21 actually be won, and what does the player think they are looking at?

Plays the board with the same greedy rule the coach uses - slide whatever seat
lets the front of the queue sit - and reports where it ends up."""
import pathlib, sys
from playwright.sync_api import sync_playwright

LEVELS = [int(a) for a in sys.argv[1:]] or [21]
url = pathlib.Path("../index.html").resolve().as_uri()

SOLVE = """
async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  for (let guard = 0; guard < 3000 && S.phase === "play"; guard++) {
    if (S.boarding || S.anim.length) { await sleep(20); continue; }
    if (!S.queue.length) { await sleep(20); continue; }
    if (pickSeat(S, S.queue[0])) { autoBoard(); await sleep(20); continue; }
    let best = null;
    for (const b of S.seats) {
      const home = [b.c, b.r];
      for (const [c, r] of placements(S, b)) {
        place(S, b, c, r);
        const fine = !!pickSeat(S, S.queue[0]);
        place(S, b, home[0], home[1]);
        if (fine) { best = { b, c, r }; break; }
      }
      if (best) break;
    }
    if (!best) {
      const left = {};
      for (const c of S.queue) left[colName(c)] = (left[colName(c)] || 0) + 1;
      const open = {};
      for (const b of S.seats) {
        const n = b.colour === 0 ? "grey->" + colName(GREY_TAKES) : colName(b.colour);
        const free = b.occ.filter(x => x == null).length;
        if (free) open[n] = (open[n] || 0) + free;
      }
      return { phase: "STUCK", seated: S.seated, total: S.total, moves: S.moves,
               stillOutside: left, emptyPlaces: open };
    }
    place(S, best.b, best.c, best.r); S.moves++; onSeatMoved(); onHud(); draw(); autoBoard();
    await sleep(20);
  }
  return { phase: S.phase, seated: S.seated, total: S.total, moves: S.moves };
}
"""

with sync_playwright() as pw:
    br = pw.chromium.launch()
    for lvl in LEVELS:
        pg = br.new_page(viewport={"width": 520, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url + "?level=" + str(lvl))
        pg.wait_for_function("typeof BOOTED !== 'undefined' && BOOTED", timeout=20000)
        pg.evaluate("SPEED = 8; S.left = 9999")
        ok = pg.query_selector("#intro-ok")
        if ok and ok.is_visible():
            ok.click()
        pg.wait_for_timeout(300)
        r = pg.evaluate(SOLVE)
        print("level %-4d %s" % (lvl, r))
        if errs:
            print("          errors:", errs)
        pg.close()
    br.close()
