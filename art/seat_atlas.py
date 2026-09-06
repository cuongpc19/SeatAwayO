"""Bake every seat variant the APK actually ships, plus riders facing each way.

The level data gives each seat a length (1, 2 or 3 cells) and a SeatDirect
(0..3). Only seven combinations occur:

    (1,0) (2,0)          - the ordinary up-facing seats, 99% of them
    (1,2) (2,2)          - the same, turned to face down       (level 351+)
    (2,1) (2,3) (3,3)    - turned side-on, cells running down  (level 353+)

Long seats are ONE piece spanning several cells, not a row of single seats, so
each variant gets its own sprite sized to its own bounding box.
"""
import json, base64, math, os, time
from PIL import Image
from toy3d import Cam, bake, colorize, scale_parts, rotate_parts, xform, _bounds
from assets import guest_parts, PALETTE, EYE, WOOD, WOOD_DARK, fence_post_parts
from assets import rbox, capsule, seat_parts

SCALE = 74
PITCH = 1.33
PAD = 10                    # px of slack around a sprite
ORDER = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "pink", "grey"]

# SeatDirect -> how far to spin the model. 0 faces up the screen; the cells of a
# 1/3 seat run down the screen, so those must face left or right.
DIRECT_SPIN = {0: math.pi, 1: -math.pi / 2, 2: 0.0, 3: math.pi / 2}
VARIANTS = [(1, 0), (2, 0), (1, 2), (2, 2), (2, 1), (2, 3), (3, 3)]




def fit(parts, pad=PAD):
    """Bake into a tile just big enough, and report where the origin landed."""
    prims = [q for p in parts for q in p["geo"]]
    cam0 = Cam(yaw=0.0, pitch=PITCH, scale=SCALE, ox=0, oy=0)
    lo, hi = _bounds(cam0.to_view(prims))
    x0, x1 = lo[0] * SCALE - pad, hi[0] * SCALE + pad
    y0, y1 = -hi[1] * SCALE - pad, -lo[1] * SCALE + pad
    W, H = int(math.ceil(x1 - x0)), int(math.ceil(y1 - y0))
    ox, oy = -x0, -y0
    cam = Cam(yaw=0.0, pitch=PITCH, scale=SCALE, ox=ox, oy=oy)
    return bake(parts, cam, W, H), (W, H), (round(ox, 2), round(oy, 2))


t0 = time.time()
shapes = {}          # name -> (cache, size, pivot)

for cells, direct in VARIANTS:
    parts = rotate_parts(seat_parts(cells), DIRECT_SPIN[direct])
    shapes["s%d_%d" % (cells, direct)] = fit(parts)
    print("  seat %d cells, direct %d   %.1fs" % (cells, direct, time.time() - t0))

for direct in (0, 1, 2, 3):
    # No face. The eyes were two near-black spheres with a hard specular on them,
    # which at board scale read as a pair of dark glasses rather than as eyes.
    # The queue is faceless too, so the riders lose nothing by matching it.
    parts = rotate_parts(scale_parts(guest_parts("sit", face=False), 0.88), DIRECT_SPIN[direct])
    shapes["r%d" % direct] = fit(parts)
print("  riders, four ways          %.1fs" % (time.time() - t0))

for name, pose in (("idle", "idle"), ("cheer", "cheer")):
    # the queue faces up the screen, so it is seen from behind
    parts = rotate_parts(scale_parts(guest_parts(pose, face=False), 0.88), math.pi)
    shapes[name] = fit(parts)
shapes["post"] = fit(fence_post_parts())
print("  queue, cheer, post         %.1fs" % (time.time() - t0))

# ---- pack ----
tiles = []
for name, (cache, size, pivot) in shapes.items():
    tint = ORDER if name[0] in "sr" or name in ("idle", "cheer") else [None]
    for col in tint:
        img = colorize(cache, PALETTE[col] if col else (255, 255, 255))
        tiles.append((name + ("_" + col if col else ""), img, size, pivot))

tiles.sort(key=lambda t: -t[2][1])
COLS_W = 2400
x = y = rowH = 0
placed = []
for name, img, (w, h), pivot in tiles:
    if x + w > COLS_W:
        x = 0; y += rowH; rowH = 0
    placed.append((name, img, x, y, w, h, pivot))
    x += w; rowH = max(rowH, h)
atlasH = y + rowH

atlas = Image.new("RGBA", (COLS_W, atlasH), (0, 0, 0, 0))
meta = {"scale": SCALE, "pitch": PITCH, "yaw": 0.0, "cell": CELL, "frames": {}}
for name, img, x, y, w, h, pivot in placed:
    atlas.alpha_composite(img, (x, y))
    meta["frames"][name] = [x, y, w, h, pivot[0], pivot[1]]

atlas.save("seat_atlas.png", optimize=True)
json.dump(meta, open("seat_atlas.json", "w"))
print("\nseat_atlas.png  %d x %d  %.0f KB  (%d frames)"
      % (atlas.size[0], atlas.size[1], os.path.getsize("seat_atlas.png") / 1024, len(placed)))
b64 = base64.b64encode(open("seat_atlas.png", "rb").read()).decode()
open("seat_atlas_b64.txt", "w").write(b64)
print("data URI  %.0f KB" % (len(b64) / 1024))
