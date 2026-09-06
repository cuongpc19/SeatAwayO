import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=25000)
    pg.evaluate("load(45)")
    pg.wait_for_function("S && !S.boarding && S.anim.length === 0", timeout=20000)
    print(pg.evaluate("""() => {
      const rect = cv.getBoundingClientRect();
      const a = pickWorld(rect.left + 300, rect.top + 300);
      const b = pickWorld(rect.left + 300, rect.top + 348);   // 48 css px lower
      return { LAY_s: +LAY.s.toFixed(2), cvW: cv.width, cvH: cv.height,
               rectW: Math.round(rect.width), rectH: Math.round(rect.height),
               cssToCanvas: +(cv.width / rect.width).toFixed(3),
               worldA: a.map(v => +v.toFixed(2)), worldB: b.map(v => +v.toFixed(2)),
               dz_for_48px: +(b[1] - a[1]).toFixed(3),
               cellSizeWorld: SX };
    }"""))
    br.close()
