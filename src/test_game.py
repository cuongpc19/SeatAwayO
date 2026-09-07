"""The game shell end to end: play, drag, clear a level, and check the card,
the saved progress and the level picker all follow."""
import pathlib, json
from playwright.sync_api import sync_playwright
url = pathlib.Path("../index.html").resolve().as_uri()

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 460, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof BOOTED !== 'undefined' && BOOTED", timeout=20000)

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

    # clear it with time to spare. The card is held back for a beat of confetti
    # first, so check the celebration is up and the card is not, then wait it out.
    pg.evaluate("S.left = S.time * 0.8; S.seated = S.total; S.queue.length = 0; finish(true)")
    pg.wait_for_timeout(300)
    cheering = pg.evaluate("cardEl.classList.contains('cheer')")
    print("celebrating first     :", cheering,
          "| card held back:", not pg.evaluate("cardEl.classList.contains('on')"),
          "| paper falling:", pg.evaluate("document.querySelectorAll('#c-confetti i').length"))
    assert cheering, "no confetti beat: the card came up on the same tick as the win"
    assert not pg.evaluate("cardEl.classList.contains('on')"), "the card did not wait"
    pg.wait_for_selector("#card.on", timeout=5000)
    print("card shown            :", pg.locator("#c-title").is_visible())
    print("  title               :", pg.locator("#c-title").inner_text())
    # the star is a flat gold path now, the way Marble Sort bakes it
    print("  stars lit           :", pg.evaluate("document.querySelectorAll('#c-stars path[fill=\"#ffc21e\"]').length"))
    print("  feature bar         :", pg.locator("#c-feat-lab").inner_text(),
          "| badge:", pg.evaluate("$('c-feat-badge').firstElementChild.tagName"))
    print("  purse               :", " ".join(pg.locator("#c-coins").inner_text().split()),
          "| summary hidden:", pg.evaluate("$('c-sum').hidden"))
    print("  confetti pieces     :", pg.evaluate("document.querySelectorAll('#c-confetti i').length"))
    sv = pg.evaluate("JSON.parse(localStorage.getItem('seatmatch.save.v1'))")
    print("  saved               :", json.dumps(sv))

    pg.click("#c-next"); pg.wait_for_timeout(500)
    print("next level            :", pg.evaluate("S.level"), "card hidden:", not pg.locator("#card").is_visible())
    # the gear pauses and opens the card; HOME is a row on it now
    pg.click("#g-menu"); pg.wait_for_timeout(250)
    print("pause card            :", pg.locator("#settings").is_visible(),
          "| clock held:", pg.evaluate("PAUSED"))
    pg.click("#set-home"); pg.wait_for_timeout(200)
    pg.click("#h-levels"); pg.wait_for_timeout(300)
    print("picker buttons        :", pg.evaluate("document.querySelectorAll('#l-grid .cellbtn').length"),
          "unlocked:", pg.evaluate("document.querySelectorAll('#l-grid .cellbtn:not(.locked)').length"))

    # a loss
    pg.evaluate("startLevel(3); S.left = 0.02"); pg.wait_for_timeout(900)
    assert not pg.evaluate("cardEl.classList.contains('cheer')"), "a loss should not celebrate"
    print("loss card             :", pg.locator("#c-title").inner_text(),
          "| lose styling:", pg.evaluate("document.getElementById('c-card').classList.contains('lose')"),
          "| stars:", pg.evaluate("document.querySelectorAll('#c-stars .star').length"))
    print("  summary             :", " ".join(pg.locator("#c-sum").inner_text().split()))
    print("errors:", errs[:4] or "none")
    br.close()
