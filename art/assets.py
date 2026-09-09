"""Original core assets for a colour-sort seating puzzle.

Every part carries either a tint factor `k` (multiplied by the level colour) or a
`fixed` RGB, so one bake serves all nine colours.
Convention: floor at y = 0, the object faces +Z (toward the camera).
"""
import numpy as np
from toy3d import *

PALETTE = {
    "red":    (232,  62,  72),
    "orange": (250, 130,  42),
    "yellow": (250, 196,  46),
    "green":  ( 74, 198,  92),
    # ⚠ The first colour the game ever shows - level 1 is all of it, and the
    # grey seats are drawn holding it. Sky blue, off a screenshot of the
    # shipped game; the slot used to be a teal cyan that nothing asked for.
    # ⚠ Deeper than it looks like it should be, and that is the tint factors.
    # Every part is `k` x this colour and the cushion runs k=1.14, so a light
    # base clips its own blue channel while red and green keep rising - the
    # seat washes out to a pale cyan-white. At 225 the highlight lands just
    # under the ceiling and the piece reads as solid blue, the weight the
    # orange beside it has always had.
    "sky":    ( 35, 155, 225),
    "blue":   ( 46, 146, 242),
    "purple": (162,  92, 234),
    "pink":   (244, 112, 176),
    "grey":   (150, 156, 168),
}
EYE = (34, 38, 52)
WOOD = (198, 150, 84)
WOOD_DARK = (168, 120, 62)


# ============================== BENCH (the seat) ==============================
def bench_parts():
    """A bus seat, shaped to read from almost straight above.

    Seen from 76 degrees up, the tall padded backrest is the big rounded mass and
    it sits at the BACK of the cell (-z, up the screen); the cushion shows only as
    a narrow lighter bar in front of it. Getting that the wrong way round makes
    every seat look like it is facing the wrong way.
    """
    SEAT_Y = 0.44            # cushion top lands at 0.495 = underside of a seated guest
    P = []
    # backrest: the big soft block, at the back
    P.append(dict(geo=rbox((0, 0.95, -0.30), (1.20, 1.00, 0.46), 0.19),
                  k=1.00, spec=0.44, shin=18))
    # head roll along its top edge
    P.append(dict(geo=capsule((-0.44, 1.40, -0.30), (0.44, 1.40, -0.30), 0.16),
                  k=1.10, spec=0.55))
    # cushion, in front of the backrest and a shade brighter
    P.append(dict(geo=rbox((0, SEAT_Y, 0.20), (1.12, 0.20, 0.52), 0.10),
                  k=1.14, spec=0.50, shin=22))
    # rounded front lip
    P.append(dict(geo=capsule((-0.50, SEAT_Y - 0.02, 0.44), (0.50, SEAT_Y - 0.02, 0.44), 0.075),
                  k=1.06, spec=0.52))
    # stubby legs, barely visible from above but they ground the shadow
    for sx in (-1, 1):
        for sz in (0.30, -0.30):
            P.append(dict(geo=rbox((sx * 0.48, 0.20, sz), (0.13, 0.40, 0.13), 0.045),
                          k=0.62, spec=0.26))
    return P


# ============================== ARMCHAIR (skin variant) ==============================
def armchair_parts():
    """Plush cinema seat - the shop-skin flavour of the same slot."""
    P = []
    P.append(dict(geo=rbox((0, 1.00, -0.34), (1.08, 1.04, 0.28), 0.14, rotmat(rx=0.10)),
                  k=1.00, spec=0.40, shin=18))
    P.append(dict(geo=capsule((-0.38, 1.54, -0.44), (0.38, 1.54, -0.44), 0.155),
                  k=1.08, spec=0.52))
    P.append(dict(geo=rbox((0, 0.52, 0.02), (1.04, 0.30, 0.94), 0.15),
                  k=1.12, spec=0.48, shin=20))
    for sx in (-1, 1):
        P.append(dict(geo=capsule((sx * 0.53, 0.78, 0.40), (sx * 0.53, 0.84, -0.32), 0.155),
                      k=0.94, spec=0.48))
        P.append(dict(geo=rbox((sx * 0.53, 0.50, 0.02), (0.19, 0.36, 0.80), 0.09),
                      k=0.84, spec=0.30))
        for sz in (-1, 1):
            P.append(dict(geo=capsule((sx * 0.39, 0.08, sz * 0.33), (sx * 0.39, 0.32, sz * 0.33), 0.10),
                          k=0.58, spec=0.24))
    return P


# ============================== GUEST (the person) ==============================
def guest_parts(pose="idle", phase=0.0, face=True):
    """Blocky guest. pose: idle | walk | sit | cheer"""
    sw = np.sin(phase) if pose == "walk" else 0.0
    P = []

    if pose == "sit":
        hip_y, knee_z = 0.65, 0.40
        for sx in (-1, 1):
            P.append(dict(geo=capsule((sx * 0.17, hip_y, -0.06), (sx * 0.19, hip_y - 0.04, knee_z), 0.155),
                          k=0.90, spec=0.40))
            P.append(dict(geo=capsule((sx * 0.19, hip_y - 0.06, knee_z), (sx * 0.19, 0.17, knee_z + 0.05), 0.145),
                          k=0.90, spec=0.40))
            P.append(dict(geo=rbox((sx * 0.19, 0.10, knee_z + 0.20), (0.30, 0.19, 0.40), 0.09),
                          k=0.44, spec=0.42))
        torso_y, arm_swing, arm_fwd = hip_y + 0.34, 0.0, 0.20
    else:
        for sx in (-1, 1):
            sgn = sx * sw
            P.append(dict(geo=capsule((sx * 0.17, 0.62, 0.0), (sx * 0.21, 0.18, sgn * 0.44), 0.155),
                          k=0.90, spec=0.40))
            P.append(dict(geo=rbox((sx * 0.21, 0.10, sgn * 0.44 + 0.12), (0.30, 0.19, 0.42), 0.09),
                          k=0.44, spec=0.42))
        torso_y, arm_swing, arm_fwd = 1.02, sw, 0.0

    # tapered torso: narrow hips, broad chest
    P.append(dict(geo=cone((0, torso_y - 0.34, 0), 0.285, (0, torso_y + 0.15, 0), 0.425),
                  k=1.00, spec=0.46, shin=18))
    for sx in (-1, 1):                                   # shoulder caps, so the
        P.append(dict(geo=sphere((sx * 0.30, torso_y + 0.15, 0), 0.175),   # silhouette
                      k=1.00, spec=0.5))                                   # reads from above

    for sx in (-1, 1):
        if pose == "cheer":
            hand = (sx * 0.74, torso_y + 0.70, 0.14)
        else:
            hand = (sx * 0.47, torso_y - 0.34, -sx * arm_swing * 0.46 + arm_fwd)
        P.append(dict(geo=capsule((sx * 0.36, torso_y + 0.13, 0), hand, 0.125),
                      k=0.90, spec=0.44))

    # A head wider than the shoulders eclipses the whole body under a near
    # top-down camera, so it is deliberately smaller than the chest.
    hy = torso_y + 0.58
    P.append(dict(geo=sphere((0, hy, 0), 0.385), k=1.00, spec=0.58, shin=26))
    if face:
        for sx in (-1, 1):
            P.append(dict(geo=sphere((sx * 0.128, hy + 0.045, 0.360), 0.058),
                          fixed=EYE, spec=0.95, shin=42, rim=0.05, amb=0.60))
    return P


# ============================== SEAT (the puzzle piece) ==============================
CELL = 1.60                 # grid pitch, must match SX/SZ in the player


def seat_parts(cells=1):
    """A bus seat spanning `cells` grid cells, authored facing +z.

    Lives here rather than in seat_atlas.py because the home cover bakes the same
    seat at its own scale, and two copies of a shape are two shapes."""
    W = cells * CELL - 0.30          # leave a gap between neighbouring seats
    SEAT_Y = 0.44
    P = []
    P.append(dict(geo=rbox((0, 0.95, -0.30), (W, 1.00, 0.46), 0.19),
                  k=1.00, spec=0.44, shin=18))
    P.append(dict(geo=capsule((-W / 2 + 0.16, 1.40, -0.30), (W / 2 - 0.16, 1.40, -0.30), 0.16),
                  k=1.10, spec=0.55))
    P.append(dict(geo=rbox((0, SEAT_Y, 0.20), (W - 0.08, 0.20, 0.52), 0.10),
                  k=1.14, spec=0.50, shin=22))
    P.append(dict(geo=capsule((-W / 2 + 0.20, SEAT_Y - 0.02, 0.44), (W / 2 - 0.20, SEAT_Y - 0.02, 0.44), 0.075),
                  k=1.06, spec=0.52))
    for i in range(cells):           # a divider between neighbouring places
        if i:
            x = -W / 2 + i * CELL
            P.append(dict(geo=rbox((x, 0.72, -0.06), (0.07, 0.62, 0.82), 0.03), k=0.86, spec=0.4))
    for sx in (-1, 1):
        for sz in (0.30, -0.30):
            P.append(dict(geo=rbox((sx * (W / 2 - 0.14), 0.20, sz), (0.13, 0.40, 0.13), 0.045),
                          k=0.62, spec=0.26))
    return P


def table_parts():
    """The small table that stands on a blocked floor cell.

    ⚠ Modelled here, with the same primitives and the same lit bake as the
    seats, rather than drawn on the canvas at run time. Two canvas versions came
    before this - a stone bench and a flat two-tone box - and both looked like a
    different game sitting beside a seat, because the seats are lit 3D renders
    and vector fills have no way to match a specular.

    ⚠ Wide and low, not a stool. The first modelled one was taller than it was
    wide and still did not belong: what the eye matches on is the SILHOUETTE,
    and every seat on this board is a wide flat slab. A tall box beside them
    reads as furniture from another game however well it is lit. Its width is
    close to a seat's, its depth about half that, and it sits low on four stubby
    legs.

    ⚠ Grey, and specifically the grey seat's own grey. That colour already means
    "this does not move" on every board in the game, taught by the fixed seats
    from level 7 - so the table says what it is before the player tries to drag
    it. Wood was prettier and told them nothing. The silhouette is what keeps
    the two apart: a fixed seat is two bands with a gap, this is one slab on
    legs.

    Fixed colours rather than a `k` multiplier: the seats take a palette colour
    per frame and this must not, or nine tinted copies of one table would read as
    seats of nine colours."""
    W = CELL - 0.22
    D = W * 0.52
    TOP, THICK, APRON, LEG = 0.74, 0.34, 0.18, 0.16
    LIGHT = PALETTE["grey"]
    DARK = tuple(int(c * 0.78) for c in LIGHT)
    P = [dict(geo=rbox((0, TOP, 0), (W, THICK, D), 0.19),
              fixed=LIGHT, spec=0.50, shin=20),
         dict(geo=rbox((0, TOP - THICK / 2 - APRON * .75, 0),
                       (W - 0.22, APRON, D - 0.18), 0.085),
              fixed=DARK, spec=0.34)]
    base = TOP - THICK / 2 - APRON
    for sx in (-1, 1):
        for sz in (-1, 1):
            P.append(dict(geo=rbox((sx * (W / 2 - LEG), base / 2, sz * (D / 2 - LEG * .7)),
                                   (LEG * 1.7, base, LEG * 1.7), LEG * .5),
                          fixed=DARK, spec=0.26))
    return P


# ============================== FENCE ==============================
def fence_post_parts():
    P = [dict(geo=rbox((0, 0.34, 0), (0.34, 0.68, 0.34), 0.10), fixed=WOOD, spec=0.35),
         dict(geo=rbox((0, 0.72, 0), (0.40, 0.14, 0.40), 0.06), fixed=WOOD_DARK, spec=0.40)]
    return P


def fence_rail_parts(length, axis="x"):
    """Horizontal rail spanning `length` along x or z."""
    size = (length, 0.20, 0.22) if axis == "x" else (0.22, 0.20, length)
    return [dict(geo=rbox((0, 0.46, 0), size, 0.08), fixed=WOOD, spec=0.34),
            dict(geo=rbox((0, 0.24, 0), size, 0.08), fixed=WOOD_DARK, spec=0.30)]
