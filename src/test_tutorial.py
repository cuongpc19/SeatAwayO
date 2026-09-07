"""The coaching on boards 1 and 2: does it appear when the board needs it,
point at a move that actually works, and get out of the way once it is made?"""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../index.html").resolve().as_uri()

STATE = """() => ({
  shown: !document.getElementById('coach').hidden,
  title: document.getElementById('coach-title').textContent,
  text:  document.getElementById('coach-text').textContent,
  tut:   TUT && { seat: TUT.seat.id, at: [TUT.seat.c, TUT.seat.r], to: TUT.to },
  door:  S.door, doorFree: isFree(S, S.W - 1, S.door),
  queue: S.queue.length, seated: S.seated + '/' + S.total, phase: S.phase })"""

def drag(pg, seat_id, to):
    p = pg.evaluate("""([id, to]) => {
      const b = S.seats[id];
      const box = cv.getBoundingClientRect(), kx = cv.width/box.width, ky = cv.height/box.height;
      const n = (b.len - 1) / 2;
      const ctr = (c, r) => b.dir & 1 ? [cellW(c), cellZ(r) + n*SZ] : [cellW(c) + n*SX, cellZ(r)];
      const [ax, az] = ctr(b.c, b.r), [bx, bz] = ctr(to[0], to[1]);
      const A = P(ax, 0, az), B = P(bx, 0, bz);
      return { from: [box.left+A[0]/kx, box.top+A[1]/ky],
               to:   [box.left+B[0]/kx, box.top+B[1]/ky] }; }""", [seat_id, to])
    pg.mouse.move(*p["from"]); pg.mouse.down()
    pg.mouse.move(p["to"][0], p["to"][1], steps=12); pg.mouse.up()

SIG = "() => S ? [S.phase, S.seated, S.queue.length, S.anim.length, S.boarding].join() : 'x'"


def settle(pg, quiet_ms=1500, floor_ms=2600, cap_ms=20000):
    """Wait for the board to stop moving.

    ⚠ Two traps, both of which read exactly like "the coach mark never appeared".

    `!anim.length && !boarding` is true at the instant a level loads, before
    autoBoard has launched anybody - so on its own it returns immediately and
    every reading after it is of a board that has not started.

    And the board opens on a still beat of nearly two seconds before the first
    passenger moves. A short run of identical samples falls entirely inside it.
    So: nothing may change for `quiet_ms`, and not before `floor_ms` has passed
    at all."""
    last, quiet, waited = None, 0, 0
    step = 200
    while waited < cap_ms:
        pg.wait_for_timeout(step)
        waited += step
        now = pg.evaluate(SIG)
        quiet = quiet + step if now == last else 0
        last = now
        if (waited >= floor_ms and quiet >= quiet_ms
                and pg.evaluate("() => !S || (!S.anim.length && !S.boarding)")):
            return
    raise AssertionError("board never settled, last state " + str(last))


def open_board(pg, lvl):
    """Get onto the board, past anything in front of it.

    ⚠ startLevel does not always open a board: the first level to carry a new
    feature stops on an intro card, and the board is behind it. Without this the
    reading is of a board that never opened - which reads exactly like a coach
    mark that never appeared."""
    pg.evaluate("n => startLevel(n)", lvl)
    for _ in range(4):
        pg.wait_for_timeout(250)
        if not pg.locator("#intro").is_visible():
            return
        pg.click("#intro-ok")
    raise AssertionError("intro card would not close on level %d" % lvl)


def report(tag, s):
    print("  %-22s coach=%s  %r / %r" % (tag, s["shown"], s["title"], s["text"][:58] + "..."))
    print("  %-22s TUT=%s  door row %s %s  queue %s  seated %s"
          % ("", s["tut"], s["door"], "free" if s["doorFree"] else "BLOCKED",
             s["queue"], s["seated"]))

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 420, "height": 860})
    errs = []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof BOOTED !== 'undefined' && BOOTED", timeout=20000)
    pg.evaluate("save.unlocked = 2; persist()")

    for lvl in (1, 2):
        print("=== level %d ===" % lvl)
        open_board(pg, lvl)
        settle(pg)                            # let whoever can board, board
        # follow the coaching for as long as it keeps pointing: a board is only
        # really taught if doing what it says all the way through wins it
        for step in range(1, 7):
            s = pg.evaluate(STATE)
            if not s["tut"]:
                break
            report("step %d:" % step, s)
            drag(pg, s["tut"]["seat"], s["tut"]["to"])
            settle(pg)
        a = pg.evaluate(STATE)
        print("  %-22s %s" % ("steps coached:", step - 1 if not s["tut"] else step))
        print("  %-22s %s" % ("coach cleared:", not a["shown"]))
        print("  %-22s %s  seated %s" % ("result:", a["phase"], a["seated"]))

    # it must stay out of every other level
    pg.evaluate("save.unlocked = 12; persist()")
    pg.evaluate("startLevel(6)"); settle(pg)
    o = pg.evaluate(STATE)
    print("=== level 6 (not taught) ===")
    print("  coach shown:", o["shown"], " TUT:", o["tut"])
    print("errors:", errs or "none")
    br.close()
