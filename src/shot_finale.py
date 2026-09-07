"""Win one board in each room and photograph the ending as it plays.

    python shot_finale.py [level]   ->  fin_<theme>.png, four frames side by side

The board is solved by the shortest greedy move that lets the front of the queue
sit, which is enough for the early levels this is pointed at."""
import pathlib, sys
from PIL import Image
from playwright.sync_api import sync_playwright

LEVEL = int(sys.argv[1]) if len(sys.argv) > 1 else 3
THEMES = ["classroom", "station", "stadium", "concert", "cinema"]
AT_MS = [200, 600, 1000, 1400]                  # where in the 1500 ms beat to look

SOLVE = """
async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const ok = document.getElementById("intro-ok");
  if (ok && ok.offsetParent) ok.click();
  for (let guard = 0; guard < 400 && S.phase === "play"; guard++) {
    if (S.boarding || S.anim.length || !S.queue.length) { await sleep(60); continue; }
    if (pickSeat(S, S.queue[0])) { autoBoard(); await sleep(60); continue; }
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
    if (!best) return "stuck with " + S.queue.length + " outside";
    place(S, best.b, best.c, best.r); S.moves++; onSeatMoved(); onHud(); draw(); autoBoard();
    await sleep(60);
  }
  return S.phase;
}
"""

url = pathlib.Path("../index.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    for theme in THEMES:
        pg = br.new_page(viewport={"width": 520, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url + "?theme=" + theme + "&level=" + str(LEVEL))
        pg.wait_for_function("typeof BOOTED !== 'undefined' && BOOTED", timeout=20000)
        pg.evaluate("SPEED = 3")
        pg.wait_for_timeout(300)
        result = pg.evaluate(SOLVE)
        frames = []
        if result == "win":
            pg.wait_for_function("FIN !== null", timeout=3000)
            t0 = pg.evaluate("FIN.t0")
            for at in AT_MS:
                pg.wait_for_function("t => performance.now() - FIN.t0 >= t", arg=at, timeout=3000)
                path = "fin_%s_%d.png" % (theme, at)
                pg.screenshot(path=path)
                frames.append((at, pg.evaluate("FIN.f"), Image.open(path)))
            w = sum(im.width for _, _, im in frames) + 8 * (len(frames) - 1)
            sheet = Image.new("RGB", (w, frames[0][2].height), (40, 40, 40))
            x = 0
            for _, _, im in frames:
                sheet.paste(im, (x, 0)); x += im.width + 8
            sheet.save("fin_%s.png" % theme)
        print("%-10s level %d: %s | f at frames: %s | errors: %s" % (
            theme, LEVEL, result, [round(f, 2) for _, f, _ in frames], errs or "none"))
        pg.close()
    br.close()
