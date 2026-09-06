"""How much of the board does a walker freeze while they are en route?"""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
JS = """
(() => {
  const withWalk = S.seats.map(b => placements(S, b).length);
  const save = S.walkCells; S.walkCells = null;              // pretend nobody is walking
  const noWalk = S.seats.map((b, i) => {
    const lk = b.locked; b.locked = false;
    const n = placements(S, b).length; b.locked = lk; return n; });
  S.walkCells = save;
  return { walkers: S.anim.length,
           blockedCells: S.walkCells ? S.walkCells.size : 0,
           lockedSeats: S.seats.filter(b => b.locked).length,
           movableNow: withWalk.filter(n => n).length,
           movableIfIdle: noWalk.filter(n => n).length,
           placesNow: withWalk.reduce((a,b)=>a+b,0),
           placesIfIdle: noWalk.reduce((a,b)=>a+b,0),
           seats: S.seats.length };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1400})
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("load(129)")
    print("%-6s %-8s %-8s %-8s %-12s %-14s %-11s %s"
          % ("t(ms)", "walkers", "frozen", "locked", "movable now", "movable idle", "places now", "places idle"))
    busy = tot = 0
    for t in range(0, 9000, 500):
        pg.wait_for_timeout(500)
        r = pg.evaluate(JS)
        tot += 1; busy += 1 if r["walkers"] else 0
        print("%-6d %-8d %-8d %-8d %-12d %-14d %-11d %d"
              % (t, r["walkers"], r["blockedCells"], r["lockedSeats"],
                 r["movableNow"], r["movableIfIdle"], r["placesNow"], r["placesIfIdle"]))
    print("\nsamples with a walker on the floor: %d / %d" % (busy, tot))
    br.close()
