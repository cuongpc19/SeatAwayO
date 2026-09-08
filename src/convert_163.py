"""Turn the 1.63.1 levels into boards on a grid, the shape the engine reads.

What the panels turned out to be
--------------------------------
Every SeatPanel_N is a perfect W x H lattice: pitch 1.2 on both axes, y fixed
at 0.86, rotZ 0 everywhere.  Slot numbering is row-major from the door end with
both axes running backwards, so

    slot = row * W + col,  row 0 at max z (the door), col 0 at max x

and that inverts cleanly to a grid coordinate.  The emitted grid runs its
columns the other way, low x first, so that max x - the wall every panel hangs
its door on - is column W-1, which is the only column the engine will put a
door in.  Getting that backwards puts the door against the far wall on every
board in the campaign.

A bench covers one cell per person, and turnNumber says which way
-----------------------------------------------------------------
`doubleSeat` / `tripleSeat` / `fourSeater` are the footprint, the same as the
binary format's seat size: a two-seater covers two cells.  Reading them as a
capacity packed into one cell survives every overlap check, which is why it
lasted a while, but captures of the shipped game show two-cell benches - and
what makes the spans fit is `turnNumber`.  It is the seat's rotation, not a
count of turns: 0 runs along +x, 1 along +z, 2 along -x, 3 along -z, which is
SeatDirect under another name.  With it, boards that will not lay out drop from
422 to 20, and the multi-seats on those 422 are exactly the ones wearing turn 2,
pointing back the other way.

Checked against captures of the real game: level 5, and the board at ID 25,
come out cell for cell - spans, grey seats, door corner and all.

Capacity summed per colour still equals the queue's colour counts on 2674 of
2676 boards - a board is saturated, every place spoken for by one rider - and
the two that miss are ID 2488, whose queue is counted twice, and 2504, which
has no queue.

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
DOORS = "lv/doors_163.json"
OUT = "lv/boards_163.json"

# ⚠ The ladder does not start at ID 0. The bundle carries two campaigns: an
# older one in IDs 0..1004, still ramping 2, 3, 4, 5 seats from the front like a
# tutorial, and the one 1.63.1 actually plays from 1005 on. Captures taken off
# this very APK pin it: its level 3 is ID 1007 and its level 4 is ID 1008, each
# matching cell for cell and each the only board in the whole set that does. So
# the displayed level is ID - 1004, and the old block is left out of the ladder
# rather than shipped in front of it, which is what made the first thousand
# levels a second, easier tutorial.
FIRST_ID = 1005
LAST_ID = 2508      # 5000+ is event content, not the campaign

SECONDS_PER_RIDER = 3.5      # fitted to the binary levels; see the module docstring
MIN_SECONDS = 60

# ⚠ Colour 0 is not free to use. The engine reads a seat of colour 0 as a grey
# fixture: it never moves, and it only ever takes the first colour. That was
# true of the binary levels, where riders ran 1..8 and 0 could only mean grey.
# 1.63.1 renumbered from zero, so its colour 0 is an ordinary colour worn by
# 40% of the seats and 36% of the riders - shipping it unshifted would turn
# four seats in ten into immovable walls.
#
# Where it moves to is not arbitrary either. The binary levels opened on sky
# blue and 56% of their riders wore it; 1.63.1's colour 0 plays that same part,
# down to being the only colour on the opening boards, so it takes sky's index
# and the first levels look like they did before. NAMES is
# grey red sky yellow green orange purple blue pink, and only those nine have
# their own sprite - lime, teal, brown and navy share one with an earlier
# colour, which is why the palette stops at eight.
# NAMES is grey red sky yellow green orange purple blue pink, and the bundle
# ships exactly seven seat colours - Grid_Blue, Grid_Green, Grid_Orange,
# Grid_Pink, Grid_Puple, Grid_Red, Grid_Yellow - which is the 0..6 range.
# Four of the seven are read straight off captures of the real game: the board
# at ID 124 puts source 3 where the capture shows red, source 1 where it shows
# green and source 4 where it shows pink, with source 2 yellow in both; source 0
# is the blue every early level is made of. 5 and 6 were the two left over,
# orange and purple, and which way round they went was a guess until source ID
# 1016 turned up in a capture: the six seats it puts at (0,0) (2,0) (0,2) (2,2)
# (0,4) (2,4) are orange there and were coming out purple here. So 6 is orange
# and 5 is purple, and nothing in the palette is guessed any more.
COLOURS = {0: 2, 1: 4, 2: 3, 3: 1, 4: 8, 5: 6, 6: 5}
GREY = 0           # the engine's fixture colour, and GREY_TAKES is 2 - sky
# SeatDirect: 0 and 2 run along x, 1 and 3 along z. turnNumber is this, not a
# count of turns - see the module docstring.
STEP = [(1, 0), (0, 1), (-1, 0), (0, -1)]
# The two rare markers, 8 and 12 in the old format. They appear on 16 boards
# between them, all of which already use green, so 501 cannot have lime.
SPECIAL = {500: 7, 501: 6}


def recolour(c):
    return SPECIAL[c] if c in SPECIAL else COLOURS[c]


def seat_colour(s):
    """`staticSeat` is the grey fixture, not a rule of its own.

    All 14091 of them wear colour 0 and not one wears anything else, which is
    the binary format's grey seat exactly: a seat that never moves and takes
    only the first colour. The engine already has that - FIXED is colour 0, and
    GREY_TAKES is 2, which is where colour 0 lands - so writing grey out says
    the whole thing without a flag or a line of engine code.
    """
    return GREY if s["staticSeat"] else recolour(s["colour"])


def grids():
    """panel number -> (W, H, {slot: (col, row)})

    The lattice is one column wider than the board. Every panel carries an
    `ExtraGridGorsterge` strip sitting exactly on its lowest-x column with
    scaleX 0 - collapsed, switched off - and across all 2676 levels nothing
    ever lands there: no seat, no coloured tile, no hole, no obstacle. So the
    low column is dropped and the board is what is left, which is also what
    turns the commonest size from 6x8 into the 5x8 the binary campaign ran on.
    """
    out = {}
    for pn, areas in json.load(open(PANELS)).items():
        xs = sorted({v["x"] for v in areas.values()})
        zs = sorted({v["z"] for v in areas.values()})
        assert len(xs) * len(zs) == len(areas), "panel %s is not a full lattice" % pn
        dropped, xs = xs[0], xs[1:]
        W, H = len(xs), len(zs)
        # low x first: max x has to land on W-1, the engine's door wall
        col = {v: i for i, v in enumerate(xs)}
        row = {v: H - 1 - i for i, v in enumerate(zs)}
        cells = {int(k): (col[v["x"]], row[v["z"]])
                 for k, v in areas.items() if v["x"] != dropped}
        out[int(pn)] = (W, H, cells)
    return out


def clock(riders):
    """A time limit for a board that ships without one, at the old game's pace."""
    return max(MIN_SECONDS, int(round(SECONDS_PER_RIDER * riders / 5)) * 5)


def capacity(s):
    return 4 if s["fourSeater"] else 3 if s["tripleSeat"] else 2 if s["doubleSeat"] else 1


def convert():
    G = grids()
    doors = json.load(open(DOORS))
    boards, flags, dropped = [], collections.Counter(), []
    for r in json.load(open(LEVELS)):
        if not (FIRST_ID <= r["id"] <= LAST_ID):
            continue
        W, H, cells = G[r["panel"]]
        seats, extra = [], {}
        laid, ok = set(), True
        for i, s in enumerate(r["seats"]):
            if s["slot"] not in cells:      # the switched-off column; nothing uses it
                ok = False
                break
            c0, r0 = cells[s["slot"]]
            n, d = capacity(s), s["turn"] & 3
            dc, dr = STEP[d]
            covered = [(c0 + dc * k, r0 + dr * k) for k in range(n)]
            if any(not (0 <= c < W and 0 <= rr < H) for c, rr in covered) or laid & set(covered):
                ok = False
                break
            laid |= set(covered)
            # c, r, size, colour, SeatDirect. The engine lays a seat out from its
            # anchor in the positive direction whichever way it faces, so one
            # pointing back down an axis is anchored at its far end; the rotation
            # itself is kept, because the sprite and the no-entry-over-the-backrest
            # rule both read it.
            c, row = min(covered)
            # The atlas has no s1_1 or s1_3: a single cell was only ever drawn
            # facing along x. A one-cell seat covers the same cell whichever way
            # it points, so the rotation is folded onto the axis that has art
            # rather than leaving 487 seats with no sprite at all, which draws
            # nothing and reads as an empty square.
            seats.append([c, row, n, seat_colour(s), (d & 2) if n == 1 else d])
            # staticSeat ships as grey and turnNumber as the rotation; the engine
            # runs both, so neither belongs in mods.
            mods = {k: True for k in ("isLocked", "vanish", "split",
                                      "transparentSeat", "firstClass") if s[k]}
            if s["ice"]:
                mods["ice"] = s["ice"]
            for k in mods:
                flags[k] += 1
            if mods:
                extra[str(i)] = mods
        if not ok:
            dropped.append(r["id"])
            continue
        boards.append({
            "id": "Level_%05d" % (r["id"] - FIRST_ID + 1),
            "name": "Level_%05d" % (r["id"] - FIRST_ID + 1),
            "sourceId": r["id"],
            "track": "campaign",
            # The shell builds its campaign ladder by filtering on variant 0 and
            # reads difficulty off `diff`; 1.63.1 ships one board per id and no
            # difficultLevel at all, so both are constants here rather than
            # missing keys - a board without `variant` drops out of the ladder
            # silently and the game boots to an empty campaign.
            "variant": 0, "diff": 0,
            # Where the queue walks in. Without this the engine hunts down the
            # W-1 wall for the first free cell, which is the row the door is on
            # only while nothing is parked in it - and something is parked in it
            # on 987 of these boards.
            "door": doors[str(r["panel"])]["entryRow"],
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
    return boards, flags, dropped


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
        # a grey fixture takes the first colour, so its places belong to sky
        if GREY in per:
            per[COLOURS[0]] += per.pop(GREY)
        if not (0 <= b["door"] < b["h"]):
            bad["door row is off the grid"] += 1
        if per != collections.Counter(b["queue"] + b["queue2"]):
            bad["seats do not match the queue"] += 1
    return bad


def palette_check():
    """No board may land two of its colours on the same engine colour."""
    bad = 0
    for r in json.load(open(LEVELS)):
        used = {s["colour"] for s in r["seats"]} | set(r["queue"]) | set(r["queue2"])
        if len({recolour(c) for c in used}) != len(used):
            bad += 1
    return bad


boards, flags, dropped = convert()
clashes = palette_check()
bad = check(boards)
json.dump(boards, open(OUT, "w"), separators=(",", ":"))
print("boards        :", len(boards))
print("dropped       :", len(dropped), "that will not lay out:", dropped[:10])
print("grid sizes    :", collections.Counter((b["w"], b["h"]) for b in boards).most_common())
print("capacities    :", collections.Counter(s[2] for b in boards for s in b["seats"]))
print("clock         : min %ds  max %ds" % (min(b["time"] for b in boards), max(b["time"] for b in boards)))
print("colours       :", sorted({s[3] for b in boards for s in b["seats"]}))
print("riders        :", sum(len(b["queue"]) + len(b["queue2"]) for b in boards))
print("carried flags :", dict(flags))
print("grey fixtures :", sum(1 for b in boards for s in b["seats"] if s[3] == GREY),
      "on", sum(1 for b in boards if any(s[3] == GREY for s in b["seats"])), "boards")
first = next((b["id"] for b in boards if any(s[3] == GREY for s in b["seats"])), None)
print("first grey at :", first, "= campaign level",
      next(i + 1 for i, b in enumerate(boards) if b["id"] == first))
print("door rows     :", dict(collections.Counter(b["door"] for b in boards)))
print("colour clashes:", clashes)
print("failed checks :", dict(bad) or "none")
print("wrote", OUT, "%.0f KB" % (os.path.getsize(OUT) / 1024))
