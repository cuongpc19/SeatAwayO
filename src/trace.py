import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1000, "height": 900})
    seen = []
    pg.on("pageerror", lambda e: seen.append(getattr(e, "stack", None) or str(e)))
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("load(8)")
    pg.wait_for_timeout(200)
    out = pg.evaluate("""() => {
      try { const b = S.seats[0]; return { ok: true, cells: cellsOf(b), pl: placements(S, b).length }; }
      catch (e) { return { ok: false, err: String(e), stack: e.stack }; }
    }""")
    print(out)
    pg.wait_for_timeout(200)
    print("PAGE ERRORS:", seen[:2])
    br.close()
