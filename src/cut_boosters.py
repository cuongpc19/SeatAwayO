"""Cut the three booster tiles out of the sheet an image model drew.

    python cut_boosters.py      boosters/sheet.png -> boosters/{time,jump,area}.webp

The sheet (Manythings/booster.png, copied to boosters/sheet.png because
Manythings is not in git) is three finished 3D tiles side by side - orange
stopwatch, purple hop, green "+ lane" - on transparency. Two faults came with
it, both invisible on the white an image viewer shows and both plain on the
game's dark dim:

  - a scatter of faint rainbow pixels around every tile, left by whatever cut
    the background away. Everything not joined to a tile is dropped;
  - the tiles themselves are not opaque: alpha sits at 251-253, so the room
    shows faintly through a button. Anything that solid is made solid.

Each tile is then cropped, centred on a square and scaled to 256 px - the
button is 4.1rem, about 200 device pixels on a 3x phone, and the walkthrough
scales it by 1.22 - with alpha premultiplied for the scaling, so the edge does
not pick up the colour of the transparent pixels around it. WebP, because the
glossy gradients that make them look 3D are what PNG compresses worst.
"""
import pathlib
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parent / "boosters"
NAMES = ("time", "jump", "area")          # left to right on the sheet
SIZE = 256

sheet = Image.open(HERE / "sheet.png").convert("RGBA")
px = np.array(sheet)
alpha = px[..., 3].astype(np.int32)
solid = alpha > 128
labels, n = ndimage.label(solid)
areas = ndimage.sum(solid, labels, range(1, n + 1))
tiles = [i + 1 for i in np.argsort(areas)[::-1][:3]]
assert all(areas[t - 1] > 0.05 * solid.size for t in tiles), "fewer than three tiles on the sheet"
tiles.sort(key=lambda t: np.where(labels == t)[1].mean())      # left to right

for name, t in zip(NAMES, tiles):
    body = ndimage.binary_fill_holes(labels == t)
    keep = ndimage.binary_dilation(body, iterations=3)           # its own soft edge, nothing further out
    a = np.where(keep, alpha, 0)
    a = np.where(a >= 240, 255, a)                               # a button is not a window
    ys, xs = np.where(body)
    y0, y1, x0, x1 = ys.min() - 4, ys.max() + 5, xs.min() - 4, xs.max() + 5
    tile = np.dstack([px[..., :3], a]).astype(np.uint8)[y0:y1, x0:x1]
    h, w = tile.shape[:2]
    side = max(h, w)
    sq = np.zeros((side, side, 4), np.uint8)
    sq[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = tile
    img = Image.fromarray(sq, "RGBA").convert("RGBa").resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")
    out = HERE / (name + ".webp")
    img.save(out, "WEBP", quality=90, method=6)
    print("%-5s %4dx%-4d from the sheet -> %s, %.1f KB" % (name, w, h, out.name, out.stat().st_size / 1024))
