import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
PLAY = """
(async (n) => { S.left = 1e9;
  for (let i = 0; i < n; i++) {
    const ci = S.queue[0]; if (ci === undefined) break;
    const reg = reachRegion(S);
    const t = S.seats.find(b => canSeat(S, b, ci, reg));
    if (!t) break; sendTo(t, true);
  }
  draw(); return { seated: S.seated, total: S.total }; })(%d)
"""
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    for lvl, n, tag in ((1, 0, "l1"), (14, 6, "l14"), (45, 12, "l45")):
        pg.evaluate("L => load(L)", lvl); pg.wait_for_timeout(200)
        if n: print(lvl, pg.evaluate(PLAY % n))
        pg.wait_for_timeout(200)
        pg.locator(".stage").screenshot(path="p3_%s.png" % tag)
    pg.screenshot(path="p3_full.png", full_page=True)
    br.close()
ims = [Image.open("p3_%s.png" % t).convert("RGB") for t in ("l1", "l14", "l45")]
w = 620
ts = [im.resize((w, int(im.height * w / im.width))) for im in ims]
sh = Image.new("RGB", (w, sum(t.height for t in ts)), (235, 238, 242))
y = 0
for t in ts: sh.paste(t, (0, y)); y += t.height
sh.save("p3_sheet.png"); print(sh.size)
