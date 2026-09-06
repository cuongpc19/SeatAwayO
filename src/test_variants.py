"""Every seat variant must draw, and nobody may pass through a seat."""
import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=25000)
    pg.evaluate("INSTANT = true")

    missing, kinds = set(), {}
    for L in range(1, 634):
        pg.evaluate("L => load(L)", L)
        r = pg.evaluate("""() => {
          const out = {}, miss = [];
          for (const b of S.seats) {
            const key = b.len + "_" + b.dir;
            out[key] = (out[key] || 0) + 1;
            if (!META.frames[seatFrame(b)]) miss.push(seatFrame(b));
            if (!META.frames[riderFrame(b, 1)]) miss.push(riderFrame(b, 1));
          }
          return { out, miss };
        }""")
        for k, v in r["out"].items(): kinds[k] = kinds.get(k, 0) + v
        missing.update(r["miss"])
    print("seat variants drawn:", dict(sorted(kinds.items())))
    print("frames missing from the atlas:", sorted(missing) or "none")

    # nobody may enter a place from behind it, nor through another place of the seat
    bad = pg.evaluate("""() => {
      let behind = 0, through = 0;
      for (let L = 1; L <= 120; L++) {
        load(L);
        for (const b of S.seats) {
          const back = FACING[b.dir];
          const own = new Set(cellsOf(b).map(([c,r]) => c+","+r));
          for (let k = 0; k < b.len; k++) {
            const [c, r] = cellsOf(b)[k];
            for (const [ec, er] of cellEntries(S, b, k)) {
              if (ec === c - back[0] && er === r - back[1]) behind++;
              if (own.has(ec + "," + er)) through++;
            }
          }
        }
      }
      return { behind, through };
    }""")
    print("entries from behind a place        :", bad["behind"], "(must be 0)")
    print("entries through another place      :", bad["through"], "(must be 0)")

    pg.evaluate("INSTANT = false; load(353)")
    pg.wait_for_timeout(2200)
    pg.locator(".stage").screenshot(path="var_353.png")
    pg.evaluate("load(356)"); pg.wait_for_timeout(2200)
    pg.locator(".stage").screenshot(path="var_356.png")
    print("errors:", errs[:3] or "none")
    br.close()
ims = [Image.open(n).convert("RGB") for n in ("var_353.png","var_356.png")]
w = 420
ts = [im.resize((w, int(im.height*w/im.width))) for im in ims]
sh = Image.new("RGB", (w*2, max(t.height for t in ts)), (232,236,240))
for i,t in enumerate(ts): sh.paste(t,(i*w,0))
sh.save("variants_sheet.png"); print(sh.size)
