"""Check the corrected mechanic: dragging is the only input, boarding is automatic."""
import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright

url = pathlib.Path("../level_player.html").resolve().as_uri()

# A player that only ever drags: slide whichever seat lets somebody board.
SOLVE = """
(async (maxDrags) => {
  S.left = 1e9;
  let drags = 0;
  autoBoard(true);
  while (S.phase === "play" && S.queue.length && drags < maxDrags) {
    let did = false;
    const before = S.seated;
    for (const b of S.seats) {
      for (const [c, r] of placements(S, b)) {
        const home = [b.c, b.r];
        place(S, b, c, r);
        if (S.queue.length && pickSeat(S, S.queue[0])) {
          drags++; autoBoard(true); did = true; break;
        }
        place(S, b, home[0], home[1]);
      }
      if (did) break;
    }
    if (!did) break;
    if (S.seated === before) break;      // no progress, avoid spinning
  }
  return { phase: S.phase, seated: S.seated, total: S.total, left: S.queue.length,
           drags, door: S.door, W: S.W, H: S.H,
           free: S.W * S.H - S.hole.reduce((a,v)=>a+v,0) - S.seats.reduce((a,b)=>a+b.len,0) };
})(600)
"""

LEVELS = [1, 2, 3, 5, 8, 10, 12, 14, 20, 30, 45, 60, 90, 120, 180, 250, 320, 353, 400, 480, 550, 600]

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url)
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.wait_for_timeout(500)

    # level 1 should board both riders with no input at all, as in the recording
    pg.evaluate("load(1)")
    pg.wait_for_timeout(1600)
    print("L1 with zero input ->", pg.evaluate("({seated:S.seated,total:S.total,phase:S.phase})"))
    pg.locator(".stage").screenshot(path="auto_l1.png")

    won = 0
    for L in LEVELS:
        pg.evaluate("INSTANT = true"); pg.evaluate("L => load(L)", L)
        pg.wait_for_timeout(120)
        r = pg.evaluate(SOLVE)
        ok = r["phase"] == "win"
        won += ok
        print("%s L%-4s %dx%-2d free %2d door %d -> seated %2d/%-2d drags %3d"
              % ("WIN " if ok else "STUCK", L, r["W"], r["H"], r["free"], r["door"],
                 r["seated"], r["total"], r["drags"]))
    print("\nsolved %d/%d by a drag-only player" % (won, len(LEVELS)))
    print("errors:", errs[:3] or "none")
    pg.evaluate("INSTANT = false; load(14)"); pg.wait_for_timeout(1200)
    pg.locator(".stage").screenshot(path="auto_l14.png")
    br.close()

ims = [Image.open(n).convert("RGB") for n in ("auto_l1.png", "auto_l14.png")]
w = 640
ts = [im.resize((w, int(im.height * w / im.width))) for im in ims]
sh = Image.new("RGB", (w, sum(t.height for t in ts)), (235, 238, 242))
y = 0
for t in ts: sh.paste(t, (0, y)); y += t.height
sh.save("auto_sheet.png")
print("auto_sheet.png", sh.size)
