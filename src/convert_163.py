"""Turn the 1.63.1 levels into boards on a grid, the shape the engine reads.

What the panels turned out to be
--------------------------------
Every SeatPanel_N is a perfect W x H lattice: pitch 1.2 on both axes, y fixed
at 0.86, rotZ 0 everywhere.  Slot numbering is row-major from the door end with
both axes running backwards, so

    slot = row * W + col,  row 0 at max z (the door), col 0 at max x

and that inverts cleanly to a grid coordinate.

A bench covers one cell, not several
------------------------------------
`doubleSeat` / `tripleSeat` / `fourSeater` are the bench's *capacity*, not its
footprint.  Three things say so and no third reading survives them:

  * no level anywhere puts two seatData entries on the same slot;
  * treating capacity as a span overlaps other benches on 422 boards, and on
    18 of the 19 boards that use a four-seater;
  * summing capacity per colour equals the queue's colour counts exactly on
    2674 of 2676 boards.  A board is saturated: every place is spoken for by
    one rider, and the two that miss are ID 2488 (queue counted twice) and
    2504 (no queue at all).

That last one also fixes the colours.  Colour 0 is a real colour here, not the
grey wildcard it was in the binary format - the shipped JSON just omits it as a
zero.  The palette is 0..6, seven colours, and 500/501 are the two rare
specials that used to be 8 and 12.

The clock is gone, and has to be put back.  Nothing in 1.63.1 carries a
timeLimit and `moveCount` appears on two boards, but the clock is the only
thing this game can lose on and the only thing it scores stars from, so a
board with no clock is a board that cannot be failed.  Rather than invent a
pace, SECONDS_PER_RIDER is fitted to the binary levels: across the 606 boards
past their 300-second tutorial block the median is 3.75 s per rider, and a
flat 3.5 lands closest, off by a median of 20 seconds.
"""
import collections, json, os

LEVELS = "lv/levels_163.json"
PANELS = "lv/panels_163.json"
OUT = "lv/boards_163.json"

SECONDS_PER_RIDER = 3.5      # fitted to the binary levels; see the module docstring
MIN_SECONDS = 60

# ⚠ Colour 0 is not free to use. The engine reads a seat of colour 0 as a grey
# fixture: it never moves, and it only ever takes the first colour. That was
# true of the binary levels, where riders ran 1..8 and 0 could only mean grey.
# 1.63.1 renumbered from zero, so its colour 0 is an ordinary colour worn by
# 40% of the seats and 36% of the riders - shipping it unshifted would turn
# four seats in ten into immovable walls. Everything moves up one, which leaves
# 0 unused and meaning what the engine already thinks it means.
COLOUR_SHIFT = 1
SPECIAL = {500: 8, 501: 9}   # the two rare markers, 8 and 12 in the old format


def recolour(c):
    return SPECIAL.get(c, c + COLOUR_SHIFT)


def grids():
    """panel number -> (W, H, {slot: (col, row)})"""
    out = {}
    for pn, areas in json.load(open(PANELS)).items():
        xs = sorted({v["x"] for v in areas.values()})
        zs = sorted({v["z"] for v in areas.values()})
        W, H = len(xs), len(zs)
        col = {v: W - 1 - i for i, v in enumerate(xs)}
        row = {v: H - 1 - i for i, v in enumerate(zs)}
        assert W * H == len(areas), "panel %s is not a full lattice" % pn
        out[int(pn)] = (W, H, {int(k): (col[v["x"]], row[v["z"]]) for k, v in areas.items()})
    return out


def clock(riders):
    """A time limit for a board that ships without one, at the old game's pace."""
    return max(MIN_SECONDS, int(round(SECONDS_PER_RIDER * riders / 5)) * 5)


def capacity(s):
    return 4 if s["fourSeater"] else 3 if s["tripleSeat"] else 2 if s["doubleSeat"] else 1


def convert():
    G = grids()
    boards, flags = [], collections.Counter()
    for r in json.load(open(LEVELS)):
        W, H, cells = G[r["panel"]]
        seats, extra = [], {}
        for i, s in enumerate(r["seats"]):
            c, row = cells[s["slot"]]
            # c, r, capacity, colour, SeatDirect, footprint. The sixth number is
            # what tells the engine a bench covers one cell however many people
            # it holds; a board without it is read the old way, footprint = seats.
            seats.append([c, row, capacity(s), recolour(s["colour"]), 0, 1])
            mods = {k: True for k in ("staticSeat", "isLocked", "vanish", "split",
                                      "transparentSeat", "firstClass") if s[k]}
            if s["ice"]:
                mods["ice"] = s["ice"]
            if s["turn"]:
                mods["turn"] = s["turn"]
            for k in mods:
                flags[k] += 1
            if mods:
                extra[str(i)] = mods
        boards.append({
            "id": "Level_%05d" % r["id"], "name": "Level_%05d" % r["id"],
            "track": "campaign",
            # The shell builds its campaign ladder by filtering on variant 0 and
            # reads difficulty off `diff`; 1.63.1 ships one board per id and no
            # difficultLevel at all, so both are constants here rather than
            # missing keys - a board without `variant` drops out of the ladder
            # silently and the game boots to an empty campaign.
            "variant": 0, "diff": 0,
            "panel": r["panel"], "w": W, "h": H,
            "time": clock(len(r["queue"]) + len(r["queue2"])),
            "moves": r["moveCount"],
            "holes": [],                     # every cell is floor; benches sit on it
            "seats": seats,                  # c, r, capacity, colour, dir
            "queue": [recolour(c) for c in r["queue"]],
            "queue2": [recolour(c) for c in r["queue2"]],
            "secondDoor": r["secondDoor"],
            "mods": extra,                   # per-seat rules the engine does not run yet
            "holeObstacles": r["holeObstacles"],
            "obstacles": r["obstacles"],
            "colouredGrid": r["colouredGrid"],
            "seatArms": r["seatArms"],
        })
    return boards, flags


def check(boards):
    """Nothing ships that the grid or the colour count says is impossible."""
    bad = collections.Counter()
    for b in boards:
        seen = set()
        for c, r, cap, col, *_ in b["seats"]:
            if not (0 <= c < b["w"] and 0 <= r < b["h"]):
                bad["off-grid"] += 1
            if (c, r) in seen:
                bad["two benches on one cell"] += 1
            seen.add((c, r))
        per = collections.Counter()
        for _, _, cap, col, *_ in b["seats"]:
            per[col] += cap
        if 0 in per:
            bad["a seat kept colour 0, which the engine reads as grey"] += 1
        if per != collections.Counter(b["queue"] + b["queue2"]):
            bad["seats do not match the queue"] += 1
    return bad


boards, flags = convert()
bad = check(boards)
json.dump(boards, open(OUT, "w"), separators=(",", ":"))
print("boards        :", len(boards))
print("grid sizes    :", collections.Counter((b["w"], b["h"]) for b in boards).most_common())
print("capacities    :", collections.Counter(s[2] for b in boards for s in b["seats"]))
print("clock         : min %ds  max %ds" % (min(b["time"] for b in boards), max(b["time"] for b in boards)))
print("colours       :", sorted({s[3] for b in boards for s in b["seats"]}))
print("riders        :", sum(len(b["queue"]) + len(b["queue2"]) for b in boards))
print("carried flags :", dict(flags))
print("failed checks :", dict(bad) or "none")
print("wrote", OUT, "%.0f KB" % (os.path.getsize(OUT) / 1024))
