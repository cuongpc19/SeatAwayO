"""Cross-check what the player renders against the decoded JSON, board by board."""
import pathlib, json
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
boards = json.load(open("lv/boards_campaign.json", encoding="utf-8"))
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1000, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("INSTANT = true")
    print("boards in page:", pg.evaluate("LEVELS.length"), " expected:", len(boards))
    bad = 0
    for i in range(1, len(boards) + 1):
        pg.evaluate("L => load(L)", i)
        got = pg.evaluate("""() => {
          const cells = [];
          for (const b of S.seats) for (const [c,r] of cellsOf(b)) cells.push([c,r,b.colour]);
          cells.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
          return { name: S.name, w: S.W, h: S.H, time: S.time,
                   riders: S.total, cells };
        }""")
        exp = boards[i - 1]
        cells = []
        for x, y, ln, col, vert in exp["seats"]:
            for k in range(ln):
                cells.append([x, y + k, col] if vert else [x + k, y, col])
        cells.sort(key=lambda a: (a[0], a[1]))
        if (got["name"] != exp["id"] or got["w"] != exp["w"] or got["h"] != exp["h"]
                or got["time"] != exp["time"] or got["riders"] != len(exp["queue"])
                or got["cells"] != cells):
            bad += 1
            if bad <= 3: print("  MISMATCH", exp["id"], got["name"], got["w"], exp["w"])
    print("boards checked:", len(boards), " mismatches:", bad)
    print("errors:", errs[:2] or "none")
    br.close()
