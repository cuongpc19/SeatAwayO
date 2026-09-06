"""The editor's Export JSON panel, end to end.

Opens the panel, drags a seat, and checks the JSON follows the board, keeps
every field the page cannot edit, and reloads into exactly the same board when
it is fed back in as a level - which is what makes an export a save point.
"""
import pathlib, json
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
LEVEL = 40                                   # big enough to have room to drag

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1100, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("n => load(n)", LEVEL); pg.wait_for_timeout(200)

    print("panel hidden at start :", pg.locator("#exp").is_hidden())
    pg.click("#b-export"); pg.wait_for_timeout(120)
    print("panel opens           :", pg.locator("#exp").is_visible(),
          "| button reads", repr(pg.locator("#b-export").inner_text()))
    before = json.loads(pg.input_value("#exp-json"))
    raw = pg.evaluate("n => LEVELS[n - 1]", LEVEL)
    print("note                  :", pg.locator("#exp-note").inner_text())

    # every field the editor cannot touch has to survive untouched
    carried = [k for k in raw if k not in ("w", "h", "holes", "seats", "queue", "time")]
    kept = [k for k in carried if before.get(k) == raw[k]]
    print("fields carried through: %d/%d %s" % (len(kept), len(carried), carried))
    print("door recorded         :", before.get("door"), "== S.door", pg.evaluate("S.door"))
    print("key order matches src :", list(before)[:len(raw)] == list(raw))

    # drag a seat and watch the JSON follow it
    pg.click("#b-trace")
    pg.locator("#board").scroll_into_view_if_needed()   # mouse coords are viewport ones
    p = pg.evaluate("""(() => {
      const i = S.seats.findIndex(b => !b.locked && placements(S, b).length);
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
    pg.mouse.move(p["to"][0], p["to"][1], steps=10); pg.mouse.up(); pg.wait_for_timeout(200)
    onboard = pg.evaluate("i => [S.seats[i].c, S.seats[i].r]", p["i"])
    print("trace                 :", pg.evaluate("document.getElementById('trace').textContent"))
    print("seat on the board     :", onboard)
    after = json.loads(pg.input_value("#exp-json"))
    moved = after["seats"][p["i"]][:2]
    print("drag %s -> %s     : seat in JSON now %s  %s"
          % (p["home"], p["target"], moved,
             "OK" if moved == list(p["target"]) else "FAILED"))
    print("only that seat moved  :", sum(1 for a, b in zip(before["seats"], after["seats"]) if a != b))
    print("queue kept whole      : %d exported vs %d shipped, %d still at the stop"
          % (len(after["queue"]), len(raw["queue"]), pg.evaluate("S.queue.length")))

    # feed it back in as a level: the board has to come up exactly as saved
    # read it in the same turn as the load, before anyone has walked aboard
    back = pg.evaluate("""b => {
        LEVELS[LEVELS.length] = b; DOOR_ROW = null; load(LEVELS.length);
        return { w: S.W, h: S.H, door: S.door, time: S.time,
                 seats: S.seats.map(s => [s.c, s.r, s.len, s.colour, s.dir]),
                 holes: [...S.hole].flatMap((v, i) => v ? [i] : []),
                 queue: S.queue.slice(), total: S.total }; }""", after)
    # load() hands the first passenger straight to autoBoard, so the live queue is
    # the saved one minus whoever has already set off; the rest must line up.
    gone = len(after["queue"]) - len(back["queue"])
    bad = [k for k in ("w", "h", "door", "time", "seats", "holes") if back[k] != after[k]]
    if back["queue"] != after["queue"][gone:] or back["total"] != len(after["queue"]):
        bad.append("queue")
    print("round trip            :", "identical" if not bad else "MISMATCH " + str(bad))
    for k in bad:
        print("   %-6s saved %r reloaded %r" % (k, after[k], back[k]))

    # the download button
    with pg.expect_download() as dl:
        pg.click("#b-exp-save")
    d = dl.value
    print("download              :", d.suggested_filename)

    pg.click("#b-export")
    print("panel closes          :", pg.locator("#exp").is_hidden(),
          "| button reads", repr(pg.locator("#b-export").inner_text()))
    print("console errors        :", errs or "none")
    br.close()
