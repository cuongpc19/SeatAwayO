"""Bake a seat and several candidate tables side by side, at the board's own
camera and light, so a shape can be judged against what it will stand next to.

The atlas takes twelve seconds to rebuild and the game another twenty to load,
which is a slow loop for a question that is only "does this belong". This bakes
the two pieces alone and puts them shoulder to shoulder."""
import math, sys
from PIL import Image, ImageDraw
from toy3d import Cam, bake, colorize, _bounds
from assets import rbox, seat_parts, PALETTE, CELL, WOOD, WOOD_DARK

# The grey seat's own colour, so a grey table can be judged against the piece it
# is borrowing its meaning from.
GY = PALETTE["grey"]
GY_D = tuple(int(c * 0.78) for c in GY)

SCALE, PITCH, PAD = 74, 1.33, 10


def fit(parts, pad=PAD):
    prims = [q for p in parts for q in p["geo"]]
    cam0 = Cam(yaw=0.0, pitch=PITCH, scale=SCALE, ox=0, oy=0)
    lo, hi = _bounds(cam0.to_view(prims))
    x0, x1 = lo[0] * SCALE - pad, hi[0] * SCALE + pad
    y0, y1 = -hi[1] * SCALE - pad, -lo[1] * SCALE + pad
    W, H = int(math.ceil(x1 - x0)), int(math.ceil(y1 - y0))
    cam = Cam(yaw=0.0, pitch=PITCH, scale=SCALE, ox=-x0, oy=-y0)
    return bake(parts, cam, W, H)


def table(w_off, top, thick, leg, wood=WOOD, dark=WOOD_DARK, spec=.46, r=.10):
    """w_off: how much narrower than a cell. top: how high the surface sits."""
    W = CELL - w_off
    D = W * 0.80
    P = [dict(geo=rbox((0, top, 0), (W, thick, D), r), fixed=wood, spec=spec, shin=20),
         dict(geo=rbox((0, top - thick * .82, 0), (W - .16, thick * .55, D - .16), r * .5),
              fixed=dark, spec=.30)]
    for sx in (-1, 1):
        for sz in (-1, 1):
            P.append(dict(geo=rbox((sx * (W / 2 - leg), (top - thick) / 2, sz * (D / 2 - leg)),
                                   (leg * 1.6, top - thick, leg * 1.6), leg * .5),
                          fixed=dark, spec=.26))
    return P


def wide(w_off, top, thick, apron, leg, r=.16, spec=.50):
    """The seat's proportion: wide, low, and read as two horizontal bands with a
    gap between them - which is the silhouette the eye actually matches on."""
    W = CELL - w_off
    D = W * 0.52
    P = [dict(geo=rbox((0, top, 0), (W, thick, D), r), fixed=WOOD, spec=spec, shin=20)]
    if apron:
        P.append(dict(geo=rbox((0, top - thick / 2 - apron * .75, 0),
                               (W - .22, apron, D - .18), r * .45), fixed=WOOD_DARK, spec=.34))
    base = top - thick / 2 - (apron or 0)
    for sx in (-1, 1):
        for sz in (-1, 1):
            P.append(dict(geo=rbox((sx * (W / 2 - leg), base / 2, sz * (D / 2 - leg * .7)),
                                   (leg * 1.7, base, leg * 1.7), leg * .5),
                          fixed=WOOD_DARK, spec=.26))
    return P


WATER = (206, 232, 244)
CAP = (46, 146, 242)


def bottle(x, y0, h, rad, cap=CAP, water=WATER, z=0.0):
    """A water bottle standing on the table: body, shoulder, neck, cap."""
    return [
        dict(geo=rbox((x, y0 + h * .40, z), (rad * 2, h * .80, rad * 2), rad * .82),
             fixed=water, spec=.62, shin=26),
        dict(geo=rbox((x, y0 + h * .86, z), (rad * 1.15, h * .22, rad * 1.15), rad * .5),
             fixed=water, spec=.60, shin=26),
        dict(geo=rbox((x, y0 + h * 1.02, z), (rad * 1.3, h * .16, rad * 1.3), rad * .45),
             fixed=cap, spec=.46, shin=20),
    ]


def wide_c(wood, dark, **kw):
    P = wide(.22, .74, .34, .18, .16, r=.19, **kw)
    for q in P:
        q["fixed"] = wood if q["fixed"] == WOOD else dark
    return P


TOP_SURFACE = .74 + .34 / 2          # where the table's lid ends

OPTS = [
    ("K khong chai", wide_c(GY, GY_D)),
    ("P h1.4 r.17",  wide_c(GY, GY_D) + bottle(-.22, TOP_SURFACE, 1.40, .17, z=-.10)),
    ("R thon r.14",  wide_c(GY, GY_D) + bottle(-.24, TOP_SURFACE, 1.45, .14, z=-.10)),
    ("S thon r.12",  wide_c(GY, GY_D) + bottle(-.26, TOP_SURFACE, 1.50, .12, z=-.10)),
]

seat = colorize(fit(seat_parts(1)), PALETTE["sky"])
grey = colorize(fit(seat_parts(1)), PALETTE["grey"])
tiles = [("GHE mau", seat), ("GHE XAM co dinh", grey)]     + [(n, colorize(fit(p), (255, 255, 255))) for n, p in OPTS]

Z = 3
pad, head = 12, 26
w = max(t[1].size[0] for t in tiles) * Z
h = max(t[1].size[1] for t in tiles) * Z
out = Image.new("RGB", (len(tiles) * (w + pad) + pad, h + head + pad), (188, 192, 200))
d = ImageDraw.Draw(out)
for i, (name, im) in enumerate(tiles):
    big = im.resize((im.size[0] * Z, im.size[1] * Z), Image.NEAREST)
    x = pad + i * (w + pad)
    out.paste(big, (x + (w - big.size[0]) // 2, head + (h - big.size[1])), big)
    d.text((x + 4, 6), name, fill=(30, 34, 48))
out.save("table_preview.png")
print("table_preview.png", out.size)
