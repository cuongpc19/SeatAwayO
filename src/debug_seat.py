import pathlib, json
from playwright.sync_api import sync_playwright

url = pathlib.Path("bench_rush.html").resolve().as_uri()

DBG = """
(async () => {
  S.left = 9999;
  for (let i = 0; i < 3; i++) { const b = hintBench(); if (!b) break; seat(b);
    await new Promise(r => setTimeout(r, 60)); }
  await new Promise(r => setTimeout(r, 600));
  draw();
  const out = [];
  for (const b of S.benches) {
    if (b.gone || !b.occ.length) continue;
    const benchX = LAY.x0 + b.c * SX, benchZ = LAY.z0 + b.r * SZ;
    const bp = P(benchX, 0, benchZ);
    const [gx, gz] = seatPos(b, 0);
    const gp = P(gx, 0.06, gz);
    out.push({ cell: [b.c, b.r], w: b.w, cap: b.cap, occ: b.occ.length,
               world: { benchX: +benchX.toFixed(2), benchZ: +benchZ.toFixed(2),
                        gx: +gx.toFixed(2), gz: +gz.toFixed(2) },
               screen: { bench: [Math.round(bp[0]), Math.round(bp[1])],
                         guest: [Math.round(gp[0]), Math.round(gp[1])] },
               dpx: Math.round(gp[0] - bp[0]), dpy: Math.round(gp[1] - bp[1]) });
  }
  return { s: +LAY.s.toFixed(1), metaScale: META.scale, pivot: META.pivot,
           tile: META.tile, SX, SZ, SEAT_DX, SEAT_DZ, SEAT_SC, benches: out };
})()
"""

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1180, "height": 1180})
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=15000)
    pg.evaluate("load(6)")
    pg.wait_for_timeout(200)
    print(json.dumps(pg.evaluate(DBG), indent=1))
    br.close()
