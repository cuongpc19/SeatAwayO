"""Play the real decoded levels in a browser and check the mechanic holds up."""
import pathlib, json
from playwright.sync_api import sync_playwright

url = pathlib.Path("../level_player.html").resolve().as_uri()

# Greedy auto-player: seat whoever can be seated; when nobody can, slide the seat
# that gets a matching seat next to the corridor.
AUTO = """
(async (maxSteps) => {
  S.left = 1e9;
  let slides = 0, guard = 0;
  while (S.phase === "play" && S.queue.length && guard++ < maxSteps) {
    const ci = S.queue[0];
    const region = reachRegion(S);
    let target = S.seats.find(b => canSeat(S, b, ci, region));
    if (target) { sendTo(target, true); continue; }
    // try to open a path: any single slide that makes a matching seat reachable
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
    if (done) continue;
    // otherwise shove any seat aside and see if that helps
    for (const other of S.seats) {
      for (const [c, r] of placements(S, other)) {
        const home = [other.c, other.r];
        place(S, other, c, r);
        const reg = reachRegion(S);
        if (S.seats.some(b => canSeat(S, b, ci, reg))) { slides++; done = true; break; }
        place(S, other, home[0], home[1]);
      }
      if (done) break;
    }
    if (!done) break;
  }
  await new Promise(r => setTimeout(r, 30));
  return { phase: S.phase, seated: S.seated, total: S.total, left: S.queue.length,
           slides, door: S.door, W: S.W, H: S.H,
           free: S.W * S.H - S.hole.reduce((a,v)=>a+v,0) - S.seats.reduce((a,b)=>a+b.len,0) };
})(1200)
"""

LEVELS = [1, 2, 3, 5, 8, 10, 12, 14, 20, 30, 45, 60, 90, 120, 180, 250, 320, 353, 400, 480, 550, 600]

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.wait_for_timeout(400)
    pg.screenshot(path="real_l1.png", full_page=True)

    won = 0
    for L in LEVELS:
        pg.evaluate("L => load(L)", L)
        pg.wait_for_timeout(150)
        info = pg.evaluate("({name:S.name, seats:S.seats.length, total:S.total, col:S.colours, time:S.time})")
        r = pg.evaluate(AUTO)
        ok = r["phase"] == "win"
        won += ok
        print("%s L%-4s %-13s %dx%-2d seats %2d riders %2d col %d free %2d door %d -> %s seated %2d/%-2d slides %2d"
              % ("WIN " if ok else "STUCK", L, info["name"], r["W"], r["H"], info["seats"], info["total"],
                 info["col"], r["free"], r["door"], r["phase"], r["seated"], r["total"], r["slides"]))
        if L == 30:
            pg.screenshot(path="real_l30.png", full_page=True)
    print("\nsolved %d/%d" % (won, len(LEVELS)))
    print("errors:", errs or "none")
    br.close()
