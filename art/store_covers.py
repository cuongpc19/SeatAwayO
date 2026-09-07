"""The covers CrazyGames shows in its grid, built the way Marble Sort builds its.

    python store_covers.py   ->  ../store/crazygames/cover-<size>.png

These are not the home screen and they are not screenshots. They are the tile a
player sees in a wall of forty other tiles, and the only job is to be the one
they click. Marble Sort's own three - `MarbleSort/Manythings/image` - are worth
copying beat for beat, because they work:

  - a vivid ground, one saturated radial, and nothing else on it. Our home
    screen's near-black navy reads as a hole in a page of bright thumbnails;
  - the name enormous, on two lines, in the pieces' own colours, cut out with a
    thick white sticker edge so it survives being shrunk to 200px wide;
  - three pieces, huge, most of the frame wide, each with a dark outline and a
    soft cast underneath so they lift off the ground;
  - no tagline, no buttons, no board. A thumbnail has room for one idea.

⚠ The pieces are re-rendered per size rather than cropped. A 16:9 crop of a 2:3
render loses the outer two seats, and a 1:1 crop loses the second line of the
title. Same three pieces, same lettering, three cameras.

Slow - it is a raymarcher at cover resolution - and not part of build.py.
"""
import math
import os
import time

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from assets import CELL, PALETTE, guest_parts
from home_cover import FACE, seat, tint
from toy3d import Cam, bake, colorize, rotate_parts, scale_parts, xform

OUT = "../store/crazygames"
FONT = "Baloo2-ExtraBold.ttf"

# ⚠ Near the board's own camera (1.33) rather than the low, front-on angle this
# started at. Low, the seat back stands between the camera and whoever is in the
# seat, and the passenger reads as a ball parked behind a sofa; from up here you
# look down into the seat and see them sitting in it. Not all the way to 1.45,
# where the seat loses its front face and the row goes flat.
PITCH = 1.30

# The ground: one radial, bright in the middle and deep at the corners. Ours is
# the game's indigo rather than their purple, but at their saturation - the
# home screen's #12163a is a black square at thumbnail size.
GROUND_HI = (86, 74, 214)
GROUND_LO = (28, 22, 74)

INK = (26, 24, 62)                  # the outline around every piece, and the type's shadow

# The passenger, a little larger and a little higher in the seat than the board
# draws one. ⚠ Not a cheat for its own sake: at 0.88 and flat on the cushion the
# head barely clears the seat back, and at the size a store tile is actually
# looked at - 200px wide - the one thing the picture has to say, that these are
# seats with people in them, is the thing that disappears first.
RIDER_SCALE = 1.12
RIDER_LIFT = 0.22

TITLE = ["SEAT", "MATCH"]
# Two colours a line, split mid-word, which is exactly what BALL SORT does. The
# colours are the seats' own, so the type and the pieces are one set of things.
TITLE_COLOURS = [[("SE", "red"), ("AT", "yellow")],
                 [("MA", "sky"), ("TCH", "green")]]


def rider(colour, x):
    """A guest sitting in the seat at `x`, sized for the cover."""
    p = rotate_parts(scale_parts(guest_parts("sit", face=False), RIDER_SCALE), FACE)
    return tint([dict(q, geo=xform(q["geo"], move=(x, RIDER_LIFT, -0.04))) for q in p],
                PALETTE[colour])


def ground(w, h):
    """A radial, drawn small and blown up - a per-pixel loop at cover size is
    1.7 million square roots for something the eye reads as a wash."""
    n = 192
    g = Image.new("RGB", (n, n))
    d = ImageDraw.Draw(g)
    d.rectangle([0, 0, n, n], fill=GROUND_LO)
    steps = 96
    for i in range(steps, 0, -1):
        t = i / steps                       # 1 at the rim, 0 at the middle
        r = n * 0.78 * t
        c = tuple(int(a + (b - a) * (1 - t) ** 1.5) for a, b in zip(GROUND_LO, GROUND_HI))
        d.ellipse([n / 2 - r, n / 2 - r * 1.0, n / 2 + r, n / 2 + r * 1.0], fill=c)
    return g.resize((w, h), Image.BICUBIC).convert("RGBA")


def grown(mask, px, cut=24):
    """`mask` fattened by roughly `px`, with a soft edge kept.

    A blur and a threshold rather than MaxFilter: MaxFilter only takes small odd
    windows, and the sticker edge here is 1% of the frame - eight or ten pixels
    at cover size, which would be four passes and square corners."""
    if px <= 0:
        return mask
    return mask.filter(ImageFilter.GaussianBlur(px * 0.62)).point(
        lambda p: 255 if p > cut else 0).filter(ImageFilter.GaussianBlur(1.1))


def pieces(w, h, row_y, width_frac, gap=1.72):
    """The three pieces, outlined and cast, on a transparent layer.

    The row is measured in cells and the camera is scaled to fit it, so asking
    for 88% of the frame gets 88% of the frame at any size - the alternative,
    writing a pixel scale per size, drifts the moment a seat changes width."""
    span = 2 * gap + CELL + 0.25         # outer seats are a cell wide, plus a hair of air
    scale = w * width_frac / span
    cam = Cam(yaw=0.0, pitch=PITCH, scale=scale, ox=w / 2, oy=h * row_y)

    # Two taken and one empty, which is the picture Marble Sort's three blocks
    # make as well - and it is the whole puzzle in one line: colours that match
    # go together, and the grey one is the piece that will not move for you.
    scene = (seat(1, "red", -gap) + rider("red", -gap)
             + seat(1, "sky", 0.0) + rider("sky", 0.0)
             + seat(1, "grey", gap))
    lit = colorize(bake(scene, cam, w, h), (255, 255, 255))

    a = lit.getchannel("A")
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # the cast first: the silhouette, dropped and blurred, so the row sits on
    # the ground instead of floating in front of it
    cast = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cast.putalpha(a.filter(ImageFilter.GaussianBlur(w * 0.018)).point(lambda p: int(p * 0.55)))
    out.alpha_composite(cast, (0, int(h * 0.022)))

    # then the sticker edge
    edge = Image.new("RGBA", (w, h), INK + (255,))
    edge.putalpha(grown(a, w * 0.009))
    out.alpha_composite(edge)

    out.alpha_composite(lit)
    return out


def line_width(text, font, d):
    return sum(d.textlength(c, font=font) for c in text)


def fitted(text, want_px, cap=520):
    lo, hi = 8, cap
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = ImageFont.truetype(FONT, mid)
        lo, hi = (mid, hi) if line_width(text, f, probe) <= want_px else (lo, mid - 1)
    return ImageFont.truetype(FONT, lo)


def title(img, top_y, width_frac, gap_frac=0.06):
    """The name, two lines, cut out with a white edge.

    Every letter is placed by hand rather than handed to `text()` in one go:
    the line changes colour mid-word, and there is no way to say that to PIL
    otherwise. The size is fitted to the widest line so the two stack square.
    """
    w, h = img.size
    d = ImageDraw.Draw(img)
    want = w * width_frac
    font = min((fitted(t, want) for t in TITLE), key=lambda f: f.size)

    s = font.size
    lines = []
    for text, spec in zip(TITLE, TITLE_COLOURS):
        lines.append((line_width(text, font, d), spec))
    total = len(TITLE) * s * 0.86 + (len(TITLE) - 1) * s * gap_frac

    # Drawn on its own layer: the white edge is the whole block's silhouette
    # grown outwards, so it has to exist before anything is composited.
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    y = h * top_y - total / 2
    for (wide, spec), text in zip(lines, TITLE):
        x = (w - wide) / 2
        for chunk, colour in spec:
            for ch in chunk:
                # the lip under each letter, the way the UI headings are stacked
                ld.text((x, y + s * 0.075), ch, font=font,
                        fill=tuple(int(c * 0.66) for c in PALETTE[colour]) + (255,))
                ld.text((x, y), ch, font=font, fill=PALETTE[colour] + (255,))
                x += ld.textlength(ch, font=font)
        y += s * (0.86 + gap_frac)

    a = layer.getchannel("A")
    edge = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    edge.putalpha(grown(a, s * 0.11))

    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shade.putalpha(grown(a, s * 0.13).filter(ImageFilter.GaussianBlur(s * 0.06))
                   .point(lambda p: int(p * 0.55)))

    img.alpha_composite(shade, (0, int(s * 0.10)))
    img.alpha_composite(edge)
    img.alpha_composite(layer)
    return img


#      file name          w     h   title_y  title_w  row_y  row_w
SPECS = [
    # Landscape. The type is held to a third of the width - their own title is
    # about that - and the row runs nearly edge to edge under it.
    ("cover-1920x1080", 1920, 1080, 0.28, 0.40, 0.84, 0.80),
    # Portrait 2:3. The tile a phone sees, and the one this game is shaped for.
    ("cover-800x1200",   800, 1200, 0.31, 0.86, 0.75, 1.00),
    # Square. Between the two: the type can be wide, the row cannot.
    ("cover-800x800",    800,  800, 0.29, 0.62, 0.80, 0.94),
]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, w, h, ty, tw, ry, rw in SPECS:
        t0 = time.time()
        img = ground(w, h)
        img.alpha_composite(pieces(w, h, ry, rw))
        img = title(img, ty, tw).convert("RGB")
        path = os.path.join(OUT, name + ".png")
        img.save(path, optimize=True)
        print("%-22s %s  %.0f KB  %.1fs"
              % (name + ".png", img.size, os.path.getsize(path) / 1024, time.time() - t0))
