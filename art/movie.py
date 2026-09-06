"""A still for the cinema screen, cast with the game's own characters.

Everything else in this game is drawn from the same SDF renderer, so a stock
photograph on the screen would be the one thing in the room that came from
somewhere else. This bakes a frame instead: a few guests, lit from behind at
sunset, held in a single pose - a film paused, not a film playing.

The camera here is nothing like the board's. The board looks almost straight
down; this one sits low and close, which is what makes the characters read as
actors on a screen rather than as pieces on a grid.
"""
import math, os
import numpy as np
from PIL import Image, ImageFilter
from toy3d import Cam, bake, colorize, scale_parts, rotate_parts
from assets import guest_parts, PALETTE

W, H = 1280, 720
HORIZON = int(H * 0.66)


def sky():
    """Sunset behind them: a vertical ramp, plus a low sun bloom."""
    ys = np.arange(H, dtype=np.float32)[:, None, None] / H
    xs = np.arange(W, dtype=np.float32)[None, :, None] / W

    top = np.array([54, 38, 92], np.float32)
    mid = np.array([201, 88, 66], np.float32)
    low = np.array([255, 178, 78], np.float32)
    t = np.clip(ys / 0.62, 0, 1) ** 1.4
    im = top * (1 - t) + mid * t
    t2 = np.clip((ys - 0.40) / 0.22, 0, 1) ** 2
    im = im * (1 - t2) + low * t2

    d = np.sqrt(((xs - 0.60) / 0.30) ** 2 + ((ys - HORIZON / H + .02) / 0.16) ** 2)
    bloom = np.clip(1 - d, 0, 1) ** 2
    im = im * (1 - bloom) + np.array([255, 240, 196], np.float32) * bloom
    return np.clip(im, 0, 255)


def hills(im):
    """Ridges, far to near, then the ground everything stands on. Painted in that
    order: a nearer band drawn first would be buried by the one behind it."""
    xs = np.arange(W)
    ys = np.arange(H)[:, None]
    bands = [(-96, 44, 3.1, (92, 58, 104)),      # far range
             (-52, 30, 2.1, (64, 38, 72)),       # nearer range
             (-14, 14, 1.4, (42, 25, 48)),       # the rise they stand on
             (0, 0, 1.0, (33, 19, 37))]          # ground
    for off, amp, freq, col in bands:
        ridge = (HORIZON + off - amp * (np.sin(xs / (W / freq) + freq * 2.7) * .5 + .5))[None, :]
        im = np.where((ys >= ridge)[..., None], np.array(col, np.float32), im)
    return Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))


def contact_shadow(w, h):
    """A soft oval, so a figure sits on the ground instead of hovering over a box."""
    yy, xx = np.mgrid[0:h, 0:w]
    d = ((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2
    a = np.clip(1 - d, 0, 1) ** 1.2 * 185
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 20, 11, 22
    rgba[..., 3] = a.astype(np.uint8)
    return Image.fromarray(rgba).filter(ImageFilter.GaussianBlur(max(1, w * .05)))


# --- the cast --------------------------------------------------------------
# low camera, slight three-quarter turn: a film frame, not a board
CAM = Cam(yaw=0.42, pitch=0.16, scale=1.0, ox=0, oy=0)

CAST = [
    # pose,    colour,  scale, ground x, depth z, turn
    ("idle",   "sky",   0.62,  1.15, -0.55, -0.40),
    ("cheer",  "red",    1.00, -0.90,  0.25,  0.50),
    ("idle",   "yellow", 0.84,  0.10,  0.00,  0.18),
]


def figure(pose, turn, scale):
    return rotate_parts(scale_parts(guest_parts(pose, face=True), scale), turn)


def main():
    frame = hills(sky())
    px_per_unit = H * 0.235           # how tall a guest stands in the frame

    for pose, col, sc, gx, gz, turn in CAST:
        parts = figure(pose, turn, sc)
        cam = Cam(yaw=CAM.yaw, pitch=CAM.pitch, scale=px_per_unit, ox=0, oy=0)
        # bake into a generous tile, then trim to what was actually covered
        S = int(px_per_unit * 3.2)
        cam = Cam(yaw=CAM.yaw, pitch=CAM.pitch, scale=px_per_unit, ox=S // 2, oy=int(S * 0.78))
        cache = bake(parts, cam, S, S)
        img = colorize(cache, PALETTE[col])
        bb = img.getbbox()
        if bb:
            img = img.crop(bb)
        x = int(W * 0.5 + gx * W * 0.26 - img.width / 2)
        y = int(HORIZON + gz * H * 0.10 - img.height + H * 0.02)

        sh = contact_shadow(int(img.width * 1.15), max(8, int(img.height * .16)))
        frame.paste(sh, (x - (sh.width - img.width) // 2,
                         y + img.height - sh.height // 2), sh)
        frame.paste(img, (x, y), img)

    # the sun sits behind them, so the whole frame carries a warm haze
    haze = Image.new("RGB", (W, H), (255, 186, 96))
    frame = Image.blend(frame, haze, 0.10)

    out = os.path.join("..", "bg", "movie1.jpg")
    frame.save(out, quality=88, optimize=True)
    print("bg/movie1.jpg  %dx%d  %.0f KB" % (W, H, os.path.getsize(out) / 1024))


if __name__ == "__main__":
    main()
