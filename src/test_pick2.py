"""Sweep many boards, including the rotated and 3-place seats."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
JS = """
(() => {
  const box = cv.getBoundingClientRect();
  const kx = cv.width / box.width, ky = cv.height / box.height;
  let bad = 0, n = 0, kinds = {};
  for (const b of S.seats) {
    const key = b.len + "_" + b.dir; kinds[key] = (kinds[key] || 0) + 1;
    const [sx, sz] = seatCentre(b);
    // the centre of the seat, and the centre of each of its places
    const pts = [[sx, sz]].concat(cellsOf(b).map(([c, r]) => [cellW(c), cellZ(r)]));
    for (const [wx, wz] of pts) {
      const [px, py] = P(wx, 0, wz);
      const got = pickSeatAt(box.left + px / kx, box.top + py / ky);
      n++; if (!got || got.id !== b.id) bad++;
    }
  }
  return { bad, n, kinds };
})()
"""
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1000})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    tot = bad = 0; kinds = {}
    for L in (386, 387, 388, 392, 408, 538, 548, 588):
        pg.evaluate("INSTANT = true"); pg.evaluate("L => load(L)", L); pg.wait_for_timeout(60)
        r = pg.evaluate(JS)
        tot += r["n"]; bad += r["bad"]
        for k, v in r["kinds"].items(): kinds[k] = kinds.get(k, 0) + v
        if r["bad"]: print("  L%-4d %d/%d points picked the wrong seat" % (L, r["bad"], r["n"]))
    print("points tested            :", tot)
    print("picked the wrong seat    :", bad)
    print("seat kinds covered       :", dict(sorted(kinds.items())))
    print("errors:", errs[:3] or "none")
    br.close()
