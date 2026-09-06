"""What happens to the free-boarding boards if the door moves up one cell.

`load` guesses the door - the shipped data never records one - and takes the
first free cell on the right edge counting from the front. On 429 of the 600
campaign boards that guess lands on a row the head of the queue can already walk
in from, so the level starts by playing itself. `check_free.py` showed those same
boards go quiet at some other row; this asks the narrowest version of the fix:
one row towards the front, nothing else.

Three things can happen, and all three are counted:

  * the doorway lands beside a wall or a seat's back and nobody can reach a seat
    any more - the player has to make the first move, which is the point;
  * a seat is sitting ON the new door cell, so nobody can get on at all. Also a
    first move, and it is the one the tutorial teaches by name;
  * nothing changes, because the door was already on row 0 and cannot go up.

Then every board that moved is re-solved, depth 2, at BOTH doors - the one the
guess picked and the one above it. ⚠ The second run is the only one that means
anything: this solver wins 15 of these 235 boards at the door the game already
ships, so a bare "221 not beatable after the move" says the search is weak, not
that the door broke anything. Only the difference between the two runs is
evidence, and it has to be read as such.

  python check_door_up.py           the scan, then the solver
  python check_door_up.py fast      the scan only
"""
import pathlib, sys, json
from playwright.sync_api import sync_playwright

url = pathlib.Path("../level_player.html").resolve().as_uri()
fast = "fast" in sys.argv

# One board, two doors: the one `load` picks and the one above it.
TRY = """([idx]) => {
  DOOR_ROW = null;
  load(idx);
  const auto = { door: S.door, seated: S.seated, total: S.total, h: S.H, name: S.name };
  DOOR_ROW = Math.max(0, auto.door - 1);
  load(idx);
  const up = { door: S.door, seated: S.seated,
               // a seat parked on the door cell: nobody boards until it is moved
               blocked: !isFree(S, S.W - 1, S.door) };
  DOOR_ROW = null;
  return { auto, up };
}"""

# test_solve.py's search, pinned to one board: any chain of drags up to `depth`
# that ends with the head of the queue able to board.
SOLVE = """([idx, door, depth]) => {
  DOOR_ROW = door; load(idx); DOOR_ROW = null;
  S.left = 1e9;
  const snap = () => S.seats.map(b => [b.c, b.r]);
  const undo = h => S.seats.forEach((b, i) => place(S, b, h[i][0], h[i][1]));
  const score = () => (S.queue.length && pickSeat(S, S.queue[0])) ? 1 : 0;
  const dig = d => {
    for (const b of S.seats) {
      if (b.locked) continue;
      for (const [c, r] of placements(S, b)) {
        const h = snap();
        place(S, b, c, r);
        if (score() > 0) return true;
        if (d > 1 && dig(d - 1)) return true;
        undo(h);
      }
    }
    return false;
  };
  let drags = 0, spin = 0;
  autoBoard(true);
  while (S.phase === "play" && S.queue.length && drags < 400) {
    const before = S.seated;
    if (!dig(depth)) break;
    drags++;
    autoBoard(true);
    if (S.seated === before && ++spin > 40) break; else if (S.seated > before) spin = 0;
  }
  return { phase: S.phase, seated: S.seated, total: S.total, drags };
}"""

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 900, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("INSTANT = true; onFinish = () => {}; onSay = () => {}")
    campaign = pg.evaluate("LEVELS.map((b, i) => i + 1).filter((_, i) => LEVELS[i].variant === 0)")

    rows = []
    for n in range(1, len(campaign) + 1):
        r = pg.evaluate(TRY, [campaign[n - 1]])
        if not r["auto"]["seated"]:
            continue                      # this board already asks for a move
        r["level"] = n
        rows.append(r)

    stuck = [r for r in rows if not r["up"]["seated"]]
    still = [r for r in rows if r["up"]["seated"]]
    pinned = [r for r in rows if r["auto"]["door"] == 0]
    blocked = [r for r in stuck if r["up"]["blocked"]]
    print("boards whose first passenger walks in free: %d" % len(rows))
    print("   door moved up one row, and now:")
    print("      %3d ask for a move first   (of those, %d have a seat parked on the door)"
          % (len(stuck), len(blocked)))
    print("      %3d still let them in free" % len(still))
    print("      %3d could not move - the door was already on row 0" % len(pinned))

    if still:
        print("\n   still free after the move (level: seated before -> after, of total):")
        for r in sorted(still, key=lambda r: -r["up"]["seated"])[:24]:
            print("      %-4d %-16s %2d -> %-2d of %-2d   door %d -> %d%s"
                  % (r["level"], r["auto"]["name"], r["auto"]["seated"], r["up"]["seated"],
                     r["auto"]["total"], r["auto"]["door"], r["up"]["door"],
                     "   (pinned at row 0)" if r["auto"]["door"] == 0 else ""))

    if not fast:
        moved = [r for r in rows if r["up"]["door"] != r["auto"]["door"]]
        print("\nre-solving the %d boards the door actually moved on, depth 2, at both doors:"
              % len(moved))
        for r in moved:
            r["solveAuto"] = pg.evaluate(SOLVE, [campaign[r["level"] - 1], r["auto"]["door"], 2])
            r["solveUp"] = pg.evaluate(SOLVE, [campaign[r["level"] - 1], r["up"]["door"], 2])
        won = lambda r, k: r[k]["phase"] == "win"
        a = [r for r in moved if won(r, "solveAuto")]
        u = [r for r in moved if won(r, "solveUp")]
        broke = [r for r in moved if won(r, "solveAuto") and not won(r, "solveUp")]
        saved = [r for r in moved if not won(r, "solveAuto") and won(r, "solveUp")]
        print("   solved at the door the game ships : %d of %d" % (len(a), len(moved)))
        print("   solved with the door one row up   : %d of %d" % (len(u), len(moved)))
        print("   won before, lost after            : %d  %s"
              % (len(broke), [r["level"] for r in broke]))
        print("   lost before, won after            : %d  %s"
              % (len(saved), [r["level"] for r in saved]))
        print("   NOTE the search only beats %d of %d boards at the door they already ship"
              % (len(a), len(moved)))
        print("        with, so on its own it cannot say whether the move breaks a level.")
        print("        Only the two lines above can, and at %d against %d they are noise."
              % (len(broke), len(saved)))

    json.dump(rows, open("door_up.json", "w"), indent=1)
    print("\nwritten to door_up.json")
    print("errors:", errs[:3] or "none")
    br.close()
