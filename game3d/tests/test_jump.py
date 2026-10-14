# -*- coding: utf-8 -*-
"""The jump booster flies a PASSENGER, and the address bar works.

Both of these were wrong once:
  1. ?level / ?reset / ?win / ?intro had not been ported at all.
  2. The jump teleported a SEAT - copied from a dead `if (JUMP)` branch in
     engine.js's placements() that the shipped shell never reaches.
"""
import sys
from _base import ok, open_game, end_lesson, run, JUMP_TARGET


def state(pg):
    return pg.evaluate("""() => { const g = DBG.board;
      return { seats: g.seats.map(b => [b.id, b.c, b.r]), seated: g.seated,
               q: g.queue.length + g.queue2.length, coins: DBG.save.coins }; }""")


def main(br):
    pg, errs = open_game(br, "?dbg=1&reset=1&level=14&intro=jump")

    # ---- the address bar
    ok("?level=14 opens board 14 straight off", pg.evaluate("DBG.cur") == 14)
    ok("?level goes past the unlock gate", pg.evaluate("DBG.save.unlocked") >= 14)
    ok("?reset is stripped from the address bar", "reset" not in pg.evaluate("location.search"))
    ok("?intro=jump leaves only the jump lesson owed",
       pg.evaluate("DBG.save.seen.indexOf('jump')") == -1
       and pg.evaluate("DBG.save.seen.indexOf('grey')") >= 0)

    # ---- a jump seats somebody and moves NO seat
    pg.evaluate("DBG.save.coins=9999")
    pg.click("#b-jump"); pg.wait_for_timeout(250)
    ok("the button arms", pg.evaluate("DBG.armed") == "jump")
    before = state(pg)
    t = pg.evaluate(JUMP_TARGET, True)
    ok("armed, at least one seat is a legal target", t is not None)
    if t:
        pg.mouse.click(t["x"], t["y"]); pg.wait_for_timeout(200)
        ok("the tap launches a FLIGHT, not a seat move",
           pg.evaluate("DBG.board.walkers.filter(a=>a.fly).length") == 1)
        ok("a flyer does not occupy a floor cell",
           pg.evaluate("(DBG.board.walkers.find(a=>a.fly)||{}).cell") is None)
        # ⚠ Wait for the LANDING, not a stopwatch: under swiftshader a fixed
        # second can be a handful of frames.
        pg.wait_for_function("DBG.board.walkers.every(a=>!a.fly)", timeout=10000)
        after = state(pg)
        moved = [a for a, b in zip(before["seats"], after["seats"]) if a != b]
        ok("NO seat teleported", not moved, "moved=%s" % moved)
        ok("somebody actually sat down", after["seated"] > before["seated"])
        # ⚠ Not "one shorter": ordinary boarding runs through the flight too.
        walking = pg.evaluate("DBG.board.walkers.length")
        ok("nobody is lost between queue, floor and seats",
           before["q"] - after["q"] == after["seated"] - before["seated"] + walking)
        ok("the booster disarmed on use", pg.evaluate("DBG.armed") is None)

    # ---- a tap that cannot work is free
    pg.evaluate("DBG.save.coins=9999")
    c0 = pg.evaluate("DBG.save.coins")
    pg.click("#b-jump"); pg.wait_for_timeout(200)
    ok("arming alone takes no gold", pg.evaluate("DBG.save.coins") == c0)
    bad = pg.evaluate(JUMP_TARGET, False)
    if bad:
        pg.mouse.click(bad["x"], bad["y"]); pg.wait_for_timeout(250)
        ok("a tap on an unusable seat keeps it armed", pg.evaluate("DBG.armed") == "jump")
        ok("...and takes no gold", pg.evaluate("DBG.save.coins") == c0)
    pg.click("#b-jump"); pg.wait_for_timeout(200)
    ok("cancelling is free", pg.evaluate("DBG.armed") is None and pg.evaluate("DBG.save.coins") == c0)

    # ---- gold goes when the jump LANDS
    pg.evaluate("DBG.save.coins=9999; FREEBIE=null")
    c0 = pg.evaluate("DBG.save.coins")
    pg.click("#b-jump"); pg.wait_for_timeout(150)
    t2 = pg.evaluate(JUMP_TARGET, True)
    if t2:
        pg.mouse.click(t2["x"], t2["y"])
        pg.wait_for_function("DBG.board.walkers.every(a=>!a.fly)", timeout=10000)
        ok("a landed jump costs exactly the price", c0 - pg.evaluate("DBG.save.coins") == 300)
    ok("no page errors (jump)", not errs, "; ".join(errs[:3]))
    pg.close()

    # ---- ?win
    pg2, errs2 = open_game(br, "?dbg=1&level=30&win=1")
    ok("?win=1 opens the result card",
       pg2.evaluate("document.getElementById('card').classList.contains('on')"))
    ok("no page errors (?win)", not errs2, "; ".join(errs2[:3]))
    pg2.close()


if __name__ == "__main__":
    sys.exit(1 if run(main) else 0)
