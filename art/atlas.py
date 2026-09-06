"""Bake every gameplay sprite at the board camera into one atlas PNG + JSON."""
import json, base64, io, time
from PIL import Image
import math
from toy3d import Cam, bake, colorize, scale_parts, rotate_parts
from assets import bench_parts, guest_parts, fence_post_parts, PALETTE

# camera measured off a recording of the shipped game: the bus is axis-aligned
# (yaw 0) and seen from 76 degrees above the horizon, i.e. nearly straight down
TILE = 148
PIVOT = (TILE // 2, int(TILE * 0.62))
SCALE = 74
GUEST_SCALE = 0.88
CAM = Cam(yaw=0.0, pitch=1.33, scale=SCALE, ox=PIVOT[0], oy=PIVOT[1])

# Seats face UP the screen in the shipped game: the backrest sits at the front of
# the cell (+z) and the cushion behind it, so the rider has their back to us.
# The models are authored facing +z, hence the half turn.
FLIP = math.pi

SHAPES = {
    "bench": rotate_parts(bench_parts(), FLIP),
    "sit":   rotate_parts(scale_parts(guest_parts("sit"), GUEST_SCALE), FLIP),
    # the queue waits facing away from us too, same as the riders
    "idle":  rotate_parts(scale_parts(guest_parts("idle"), GUEST_SCALE), FLIP),
    "walk":  scale_parts(guest_parts("walk", phase=1.15), GUEST_SCALE),
    "cheer": scale_parts(guest_parts("cheer"), GUEST_SCALE),
}
ORDER = ["red", "orange", "yellow", "green", "sky", "blue", "purple", "pink", "grey"]

t0 = time.time()
caches = {}
for k, parts in SHAPES.items():
    caches[k] = bake(parts, CAM, TILE, TILE)
    print("  baked %-6s %.1fs" % (k, time.time() - t0))
post_cache = bake(fence_post_parts(), CAM, TILE, TILE)

tiles = []
for shape in SHAPES:
    for col in ORDER:
        tiles.append(("%s_%s" % (shape, col), colorize(caches[shape], PALETTE[col])))
tiles.append(("post", colorize(post_cache, (255, 255, 255))))

COLS = 8
rows = (len(tiles) + COLS - 1) // COLS
atlas = Image.new("RGBA", (COLS * TILE, rows * TILE), (0, 0, 0, 0))
meta = {"tile": TILE, "pivot": PIVOT, "scale": SCALE, "cols": COLS,
        "yaw": CAM.yaw, "pitch": CAM.pitch, "frames": {}}
for i, (name, im) in enumerate(tiles):
    x, y = (i % COLS) * TILE, (i // COLS) * TILE
    atlas.alpha_composite(im, (x, y))
    meta["frames"][name] = [x, y]

atlas.save("atlas.png", optimize=True)
json.dump(meta, open("atlas.json", "w"))
import os
print("atlas.png %d x %d  %.0f KB  (%d frames)" % (
    atlas.size[0], atlas.size[1], os.path.getsize("atlas.png") / 1024, len(tiles)))

# also emit a base64 data URI for inlining
b64 = base64.b64encode(open("atlas.png", "rb").read()).decode()
open("atlas_b64.txt", "w").write(b64)
print("data URI %.0f KB" % (len(b64) / 1024))
