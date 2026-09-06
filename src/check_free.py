"""Which boards seat themselves, and how much of each one is free.

A board opens with `autoBoard` already running: anybody at the front of the queue
who can walk to a seat they fit in goes and sits in it, before the player has
touched anything. That is the game - the player opens paths, the queue walks
itself in - but it has an edge:

  * a board where SOME of the queue seats itself is normal, and is what makes
    the first move feel like it did something;
  * a board where the WHOLE queue seats itself is a level that plays itself. The
    player watches it win with zero moves.

This walks every campaign level in the editor build, with the walk animation
skipped, and reports both.

  python check_free.py            every campaign level
  python check_free.py 40         the first 40 only

The second pass then re-loads every board that gives away more than a quarter of
its queue, once per door row, because the door is the thing under suspicion: the
shipped level data never records it, so `load` guesses - the first free cell on
the right edge, counting from the front. The sweep says whether a board is open
by construction or only open at the row the guess landed on.
"""
import pathlib, sys, json
from playwright.sync_api import sync_playwright

url = pathlib.Path("../level_player.html").resolve().as_uri()
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0

SCAN = """n => {
  load(n);
  return { name: S.name, w: S.W, h: S.H, door: S.door, time: S.time,
           seats: S.seats.length, grey: S.seats.filter(FIXED).length,
           total: S.total, seated: S.seated, moves: S.moves, phase: S.phase };
}"""

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 900, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    # Skip the walk, and take the card off the end of a board that finishes: this
    # is a scan of 600 boards, not a play session.
    pg.evaluate("INSTANT = true; onFinish = () => {}; onSay = () => {}")

    # The game plays one board per level name - the 33 second and third
    # arrangements are editor-only - so the level numbers here are the game's.
    campaign = pg.evaluate("LEVELS.map((b, i) => i + 1).filter((_, i) => LEVELS[i].variant === 0)")
    upto = min(limit or len(campaign), len(campaign))
    print("campaign levels: %d   scanning %d" % (len(campaign), upto))

    rows = []
    for n in range(1, upto + 1):
        r = pg.evaluate(SCAN, campaign[n - 1])
        r["level"] = n
        rows.append(r)

    free = [r for r in rows if r["seated"] >= r["total"]]
    part = [r for r in rows if 0 < r["seated"] < r["total"]]
    none = [r for r in rows if r["seated"] == 0]

    print("\nboards that seat their whole queue with no input: %d of %d" % (len(free), upto))
    for r in free:
        print("   level %-4d %-16s %dx%d  door row %d  %2d seats (%d grey)  %2d passengers  %s"
              % (r["level"], r["name"], r["w"], r["h"], r["door"], r["seats"], r["grey"],
                 r["total"], "WON with %d moves" % r["moves"] if r["phase"] == "win" else r["phase"]))

    # ⚠ "some of the queue walked in" and "the FIRST passenger walked in" are the
    # same board. `autoBoard` only ever launches the head of the queue: if it
    # cannot seat them it stops, so nobody behind them moves either. That makes
    # this one count the answer to "which levels start by playing themselves".
    print("\nboards whose FIRST passenger walks in with no input: %d of %d"
          % (upto - len(none), upto))
    with open("free_levels.txt", "w", encoding="utf-8") as f:
        f.write("Levels whose first passenger seats themselves before the player moves.\n"
                "Written by check_free.py.  %d of %d campaign boards.\n\n" % (upto - len(none), upto))
        f.write(" ".join(str(r["level"]) for r in rows if r["seated"]) + "\n\n")
        f.write("The rest - the first passenger is stuck, so the player moves first (%d):\n\n"
                % len(none))
        f.write(" ".join(str(r["level"]) for r in rows if not r["seated"]) + "\n")

    print("\nand how far each one gets before it stalls:")
    print("   none of it      %3d boards" % len(none))
    print("   part of it      %3d boards" % len(part))
    if part:
        worst = sorted(part, key=lambda r: -(r["seated"] / r["total"]))[:12]
        print("   the closest to solving themselves:")
        for r in worst:
            print("      level %-4d %-16s %2d of %2d seated  (%d%%)"
                  % (r["level"], r["name"], r["seated"], r["total"],
                     round(100 * r["seated"] / r["total"])))
    # ---- is it the board, or is it where we put the door? ----
    hot = sorted((r for r in rows if r["seated"] / r["total"] > .25),
                 key=lambda r: -(r["seated"] / r["total"]))
    if hot:
        print("\nthe open ones, re-run at every door row (the guessed row is starred):")
        for r in hot:
            at = pg.evaluate("""([idx, h]) => {
                const out = [];
                for (let d = 0; d < h; d++) { DOOR_ROW = d; load(idx); out.push(S.seated); }
                DOOR_ROW = null; return out; }""", [campaign[r["level"] - 1], r["h"]])
            print("   level %-4d %-16s %2d/%-2d   %s"
                  % (r["level"], r["name"], r["seated"], r["total"],
                     " ".join(("*%d" if d == r["door"] else " %d") % v for d, v in enumerate(at))))
            r["byDoor"] = at
        shut = sum(1 for r in hot if min(r["byDoor"]) == 0)
        print("   %d of these %d are shut at some other door row - the board is not open,"
              % (shut, len(hot)))
        print("   the row the guess landed on is.")

    json.dump(rows, open("free_scan.json", "w"), indent=1)
    print("\nfull scan written to free_scan.json")
    print("errors:", errs[:3] or "none")
    br.close()
