"""Auto-play a spread of the 1.63.1 campaign and report what the engine makes of it.

test_real.py calls sendTo(), which the engine no longer has, so this drives the
current API instead: boarding happens by itself through autoBoard(), and the
player's only move is sliding a seat somewhere the queue can reach.
"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright

url = pathlib.Path("../level_player.html").resolve().as_uri()

SOLVE = """
(async (maxSteps) => {
  S.left = 1e9;                       // solvability, not speed
  let slides = 0, guard = 0, stuck = 0;
  const settle = async () => { autoBoard(true); await new Promise(r => setTimeout(r, 0)); };
  await settle();
  while (S.phase === "play" && S.queue.length && guard++ < maxSteps) {
    const before = S.queue.length;
    await settle();
    if (S.queue.length < before) { stuck = 0; continue; }
    // nobody could board: open a path with one slide
    const ci = S.queue[0];
    let done = false;
    for (const b of S.seats) {
      if (!accepts(b, ci)) continue;
      for (const [c, r] of placements(S, b)) {
        const home = [b.c, b.r];
        place(S, b, c, r);
        if (touches(S, b, reachRegion(S))) { slides++; done = true; break; }
        place(S, b, home[0], home[1]);
      }
      if (done) break;
    }
    if (!done) for (const other of S.seats) {          // or shove anything aside
      for (const [c, r] of placements(S, other)) {
        const home = [other.c, other.r];
        place(S, other, c, r);
        if (S.seats.some(b => canSeat(S, b, ci, reachRegion(S)))) { slides++; done = true; break; }
        place(S, other, home[0], home[1]);
      }
      if (done) break;
    }
    if (!done && ++stuck > 1) break;
  }
  await new Promise(r => setTimeout(r, 40));
  return { phase: S.phase, seated: S.seated, total: S.total, left: S.queue.length, slides };
})(400)
"""

boards = json.load(open("lv/boards_163.json", encoding="utf-8"))
n = len(boards)
step = max(1, n // int(sys.argv[1] if len(sys.argv) > 1 else 60))
picks = list(range(1, n + 1, step))

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=30000)
    pg.evaluate("INSTANT = true")
    print("boards in page:", pg.evaluate("LEVELS.length"), "expected:", n)

    won = seated_all = 0
    fails = []
    for L in picks:
        pg.evaluate("L => load(L)", L)
        pg.wait_for_timeout(60)
        r = pg.evaluate(SOLVE)
        if r["phase"] == "win":
            won += 1
        else:
            fails.append((L, r["seated"], r["total"], r["left"]))
        if r["seated"] == r["total"]:
            seated_all += 1
    print("levels played  :", len(picks))
    print("won outright   :", won)
    print("everyone seated:", seated_all)
    if fails:
        print("did not finish : %d, first few %s" % (len(fails), fails[:8]))
    print("page errors    :", len(errs), errs[:3])
    br.close()
