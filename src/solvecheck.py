"""Prove every generated board is solvable: follow the built-in plan to a win."""
import pathlib
from playwright.sync_api import sync_playwright

url = pathlib.Path("bench_rush.html").resolve().as_uri()

SOLVE = """
(async () => {
  S.left = 9999;                       // the solver is testing solvability, not speed
  let guard = 0;
  while (S.phase === "play" && S.queue.length && guard++ < 500) {
    const b = hintBench();
    if (!b) return { ok: false, why: "no legal bench", seated: S.seated, total: S.total };
    seat(b);
    await new Promise(r => setTimeout(r, 55));
  }
  await new Promise(r => setTimeout(r, 900));
  return { ok: S.phase === "win", phase: S.phase, seated: S.seated, total: S.total,
           left: S.benches.filter(b => !b.gone).length };
})()
"""

LEVELS = [1, 2, 3, 5, 7, 8, 10, 12, 14, 20, 30, 45, 60, 90, 120, 180, 250, 320, 400, 480, 550, 600]

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1180, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=15000)

    fails = 0
    for L in LEVELS:
        pg.evaluate("L => load(L)", L)
        pg.wait_for_timeout(120)
        info = pg.evaluate("({w:S.W,h:S.H,b:S.benches.length,t:S.total,c:S.colours,time:S.time})")
        r = pg.evaluate(SOLVE)
        ok = "OK " if r["ok"] else "FAIL"
        if not r["ok"]:
            fails += 1
        print("%s L%-4d %dx%-2d benches %2d seats %2d colours %d %3ds -> %s"
              % (ok, L, info["w"], info["h"], info["b"], info["t"], info["c"], info["time"], r))
    print()
    print("failures:", fails, "of", len(LEVELS))
    print("page errors:", errs or "none")
    br.close()
