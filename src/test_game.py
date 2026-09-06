"""The game shell end to end: play, drag, clear a level, and check the card,
the saved progress and the level picker all follow."""
import pathlib, json
from playwright.sync_api import sync_playwright
url = pathlib.Path("../game.html").resolve().as_uri()

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 460, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)

    print("home visible          :", pg.locator("#home").is_visible())
    pg.click("#h-play"); pg.wait_for_timeout(600)
    print("play visible          :", pg.locator("#play").is_visible(), "level", pg.evaluate("S.level"))

    # a real drag with real mouse events on the game page
    p = pg.evaluate("""(() => {
      const i = S.seats.findIndex(b => !b.locked && placements(S, b).length);
      if (i < 0) return null;
      const b = S.seats[i], t = placements(S, b)[0];
      const box = cv.getBoundingClientRect(), kx = cv.width/box.width, ky = cv.height/box.height;
      const n = (b.len - 1) / 2;
      const ctr = (c, r) => b.dir & 1 ? [cellW(c), cellZ(r) + n*SZ] : [cellW(c) + n*SX, cellZ(r)];
      const [ax, az] = ctr(b.c, b.r), [bx, bz] = ctr(t[0], t[1]);
      const A = P(ax, 0, az), B = P(bx, 0, bz);
      return { i, home: [b.c, b.r], target: t,
               from: [box.left+A[0]/kx, box.top+A[1]/ky],
               to:   [box.left+B[0]/kx, box.top+B[1]/ky] }; })()""")
    pg.mouse.move(*p["from"]); pg.mouse.down()
    pg.mouse.move(p["to"][0], p["to"][1], steps=10); pg.mouse.up(); pg.wait_for_timeout(120)
    now = pg.evaluate("i => [S.seats[i].c, S.seats[i].r]", p["i"])
    print("drag %s -> %s          : %s" % (p["home"], p["target"], "OK" if now == p["target"] else "FAILED " + str(now)))

    # clear it with time to spare and read the card
    pg.evaluate("S.left = S.time * 0.8; S.seated = S.total; S.queue.length = 0; finish(true)")
    pg.wait_for_timeout(900)
    print("card shown            :", pg.locator("#card").is_visible())
    print("  title               :", pg.locator("#c-title").inner_text())
    print("  stars lit           :", pg.evaluate("document.querySelectorAll('#c-stars svg path[fill^=url]').length"))
    print("  summary             :", pg.locator("#c-sum").inner_text())
    print("  confetti pieces     :", pg.evaluate("document.querySelectorAll('#c-confetti i').length"))
    sv = pg.evaluate("JSON.parse(localStorage.getItem('seataway.save.v2'))")
    print("  saved               :", json.dumps(sv))

    pg.click("#c-next"); pg.wait_for_timeout(500)
    print("next level            :", pg.evaluate("S.level"), "card hidden:", not pg.locator("#card").is_visible())
    pg.click("#g-home"); pg.wait_for_timeout(200)
    pg.click("#h-levels"); pg.wait_for_timeout(300)
    print("picker buttons        :", pg.evaluate("document.querySelectorAll('#l-grid .cellbtn').length"),
          "unlocked:", pg.evaluate("document.querySelectorAll('#l-grid .cellbtn:not(.locked)').length"))

    # a loss
    pg.evaluate("startLevel(3); S.left = 0.02"); pg.wait_for_timeout(900)
    print("loss card             :", pg.locator("#c-title").inner_text(),
          "| lose styling:", pg.evaluate("document.getElementById('c-card').classList.contains('lose')"))
    print("errors:", errs[:4] or "none")
    br.close()
