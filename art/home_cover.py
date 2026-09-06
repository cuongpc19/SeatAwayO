"""The home screen's cover art: one 2:3 render, baked the way the atlas is.

The home screen is a picture with two buttons on it, and the picture is the only
thing on it that says what the game is. So this is the same seat and the same
guest the board draws, at three times the scale, lit the same way - not a
screenshot of a board, which would be a picture of a puzzle mid-solve rather than
of the pieces.

Three pieces in a row, and they are not chosen for looks: a coloured seat with
someone in it, a double seat with two, and a grey seat nobody can move. Those are
the three things the game teaches in its first ten levels, and the results card
counts down to two of them by name.

  python home_cover.py     ->  home_cover.png

Slow (a raymarcher, at cover resolution), so it is not part of `build.py`; the
PNG it leaves behind is what the build inlines.
"""
import math, os, time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from toy3d import Cam, bake, colorize, contact_shadow, scale_parts, rotate_parts, xform
from assets import guest_parts, seat_parts, PALETTE, CELL

W, H = 1080, 1620           # 2:3, so the cover fills a phone and crops sideways
SCALE = 112                 # px per world unit - the atlas bakes at 74

# ⚠ The row has to fit the middle 70% of the render and not a pixel more. The
# cover fills the screen rather than fitting inside it, so a 9:19.5 phone sees
# 540 of the 773 units the art is scaled to - x from 15% to 85% - and anything
# outside that band is cropped off on the one device the game is for. At this
# scale the row runs 18% to 82%, the same band Marble Sort's own three pieces
# sit in. It was 150 with the pieces at 2.5 cells, which put the outer two seats
# half off the screen on a phone; 122 put them exactly on the crop line.
PITCH = 1.33                # the board's own camera, 76 degrees above the horizon
FACE = math.pi              # SeatDirect 0: the seat faces up the screen

# Where the row sits. Marble Sort puts its three pieces just below the middle,
# with the title above and the call to action over the empty foot; the same
# split leaves room for the logo at 30% and the PLAY button at 82%.
ROW_Y = 0.615
GROUND = ((22, 26, 54), (74, 84, 142))      # top and foot of the ground
GLOW = (248, 191, 26)                        # the livery yellow, behind the row


def tint(parts, colour):
    """Freeze a part list to one colour.

    The atlas bakes a shape once and colours it nine ways, so every part carries
    a tint factor rather than a colour. Here three differently coloured pieces
    have to share one bake - one pass, so they occlude each other and cast one
    shadow - and `colorize` only knows one base colour. `fixed` is the escape
    hatch the baker already has: the factor is applied here instead."""
    out = []
    for p in parts:
        q = dict(p)
        if "fixed" not in q:
            k = q.pop("k", 1.0)
            q["fixed"] = tuple(min(255.0, c * k) for c in colour)
        out.append(q)
    return out


def seat(cells, colour, x, z=0.0):
    p = rotate_parts(seat_parts(cells), FACE)
    return tint([dict(q, geo=xform(q["geo"], move=(x, 0, z))) for q in p], PALETTE[colour])


def rider(colour, x, z=0.0):
    """A guest sitting in a seat, placed the way the board places one: on the
    cell centre, a touch up and a touch back."""
    p = rotate_parts(scale_parts(guest_parts("sit", face=False), 0.88), FACE)
    return tint([dict(q, geo=xform(q["geo"], move=(x, 0.05, z - 0.04))) for q in p],
                PALETTE[colour])


def ground():
    """The flat the pieces stand on: a vertical ramp, a warm glow where the row
    is, and a vignette. Painted rather than rendered - it is a backdrop, and a
    raymarched plane would only be a slower gradient."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    top, foot = GROUND
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, foot)))

    # The glow, drawn small and blown up: a radial gradient at full size is a
    # per-pixel loop over 1.7 million pixels for something the eye reads as haze.
    g = Image.new("L", (256, 256), 0)
    gd = ImageDraw.Draw(g)
    for i in range(64, 0, -1):
        r = 128 * i / 64
        gd.ellipse([128 - r, 128 - r, 128 + r, 128 + r], fill=int(132 * (1 - i / 64) ** 1.6))
    g = g.resize((int(W * 1.5), int(W * 1.5)), Image.BILINEAR)
    halo = Image.new("RGB", g.size, GLOW)
    img.paste(halo, (int(W / 2 - g.width / 2), int(H * ROW_Y - g.height / 2)), g)

    # A vignette, so the cover has a foot the white lettering can sit on.
    v = Image.new("L", (64, 96), 255)
    vd = ImageDraw.Draw(v)
    vd.ellipse([-26, -34, 90, 130], fill=0)
    v = v.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
    img.paste(Image.new("RGB", (W, H), (10, 14, 32)), (0, 0), v.point(lambda p: int(p * 0.72)))
    return img



# ---- the lettering ---------------------------------------------------------
# The name used to be HTML laid over this picture. Baked in, it is the same
# drawing everywhere - the store covers are crops of this render, and a title
# that lives in the DOM cannot come with them.
TITLE = "Take a Seat"
TAGLINE = "find everyone a seat"
FONT = "Baloo2-ExtraBold.ttf"       # the same face the UI headings use
TITLE_Y = 0.30                      # the band the row above was laid out to leave free
SAFE = 0.70                         # ⚠ see below

LIVERY = (248, 191, 26)             # --livery
LIVERY_DK = (217, 156, 20)          # --livery-dk
TRIM_DK = (168, 50, 32)             # --trim-dk


def fitted(text, want_px, cap=260):
    """Largest size at which `text` still fits `want_px` wide."""
    lo, hi = 8, cap
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = ImageFont.truetype(FONT, mid)
        lo, hi = (mid, hi) if f.getbbox(text)[2] - f.getbbox(text)[0] <= want_px else (lo, mid - 1)
    return ImageFont.truetype(FONT, lo)


def spaced(d, xy, text, font, fill, track):
    """PIL has no letter-spacing, and the tagline is set at 0.22em in the CSS."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + track


def lettering(img):
    """Title and tagline, in the livery, with the CSS logo's own drop stack.

    ⚠ Kept inside the same safe band as the row of seats. A 9:19.5 phone crops
    this 2:3 render to x 15%..85%, so anything wider than 70% of the canvas
    loses its ends on the one device the game is for. The size is fitted to the
    measured width rather than written down, so a longer name shrinks instead of
    running off the crop - which is what a hand-set size does silently.
    """
    d = ImageDraw.Draw(img)
    f = fitted(TITLE, W * SAFE)
    bb = f.getbbox(TITLE)
    x = (W - (bb[2] - bb[0])) / 2 - bb[0]
    y = H * TITLE_Y - (bb[3] - bb[1]) / 2 - bb[1]
    s = f.size

    # the soft cast first, on its own layer so the blur cannot eat the faces
    soft = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(soft).text((x, y + s * 0.19), TITLE, font=f, fill=(0, 0, 0, 90))
    img.alpha_composite(soft.filter(ImageFilter.GaussianBlur(s * 0.06)))

    # then the two hard offsets under the face - the CSS logo's 0 3px / 0 7px
    d.text((x, y + s * 0.115), TITLE, font=f, fill=TRIM_DK)
    d.text((x, y + s * 0.050), TITLE, font=f, fill=LIVERY_DK)
    d.text((x, y), TITLE, font=f, fill=LIVERY)

    # the tagline, tracked out the way the CSS tracks it
    tf = ImageFont.truetype(FONT, int(s * 0.205))
    track = tf.size * 0.20
    wide = sum(d.textlength(c, font=tf) for c in TAGLINE) + track * (len(TAGLINE) - 1)
    # ⚠ `y + bb[3]`, not `y + (bb[3] - bb[1])`. `y` is already the draw origin,
    # which sits bb[1] above the ink; subtracting bb[1] again lifted the tagline
    # by the ascent and printed it through the middle of the title.
    ty = y + bb[3] + s * 0.10
    spaced(d, ((W - wide) / 2, ty + 2), TAGLINE, tf, (0, 0, 0, 110), track)
    spaced(d, ((W - wide) / 2, ty), TAGLINE, tf, (255, 255, 255, 255), track)
    return img


def render(w, h, scale, row_y, title_y, safe, gap=2.45):
    """One cover, at whatever shape is asked for.

    The store wants 1920x1080, 800x1200 and 800x800 and the home screen wants
    2:3. Re-rendering the same scene into each is what keeps them one picture in
    three frames rather than three drawings that drift apart; a crop could not
    do it, because a 16:9 crop of a 2:3 render loses the row or the title.

    ⚠ The module constants really are rebound here. Every painter below reads
    W/H/SCALE/ROW_Y/TITLE_Y/SAFE as globals, and threading six arguments through
    all of them to render one more size would be the larger change for no gain.
    Nothing calls two sizes at once."""
    global W, H, SCALE, ROW_Y, TITLE_Y, SAFE
    W, H, SCALE, ROW_Y, TITLE_Y, SAFE = w, h, scale, row_y, title_y, safe

    t0 = time.time()
    cam = Cam(yaw=0.0, pitch=PITCH, scale=SCALE, ox=W / 2, oy=H * ROW_Y)

    # ⚠ The row is measured in cells, not pixels. A double seat is two cells wide
    # by definition, so writing the gaps in cells is the only way the middle
    # piece stays visibly twice the others if `CELL` ever moves.
    scene = (seat(1, "red", -gap) + rider("red", -gap)
             + seat(2, "yellow", 0.0) + rider("yellow", -CELL / 2) + rider("sky", CELL / 2)
             + seat(1, "grey", gap))

    shadow = contact_shadow(scene, cam, W, H, blur=26, alpha=150)
    lit = colorize(bake(scene, cam, W, H), (255, 255, 255))
    out = ground().convert("RGBA")
    out.alpha_composite(shadow)
    out.alpha_composite(lit)
    print("    %d x %d  %.1fs" % (W, H, time.time() - t0))
    return lettering(out).convert("RGB")


if __name__ == "__main__":
    # No .b64 twin beside the atlas ones: build.py inlines this straight from the
    # PNG, and a second copy on disk is only a second thing to forget to redo.
    render(1080, 1620, 112, ROW_Y, TITLE_Y, SAFE).save("home_cover.png", optimize=True)
    print("home_cover.png  %.0f KB" % (os.path.getsize("home_cover.png") / 1024))
