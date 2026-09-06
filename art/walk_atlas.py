"""Bake a proper walk cycle: four facings x four phases x every colour.

The character model faces +Z, which the camera shows as "down the screen", so the
four facings are just the figure spun about its own axis. Legs and arms already
swing with the pose phase, and because the whole assembled figure is rotated, the
swing follows whichever way they are walking - head included.
"""
import json, base64, time, os, math
from PIL import Image
from toy3d import Cam, bake, colorize, scale_parts, rotate_parts
from assets import guest_parts, PALETTE

TILE = 120
PIVOT = (TILE // 2, int(TILE * 0.62))
SCALE = 74                      # must match atlas.py
GUEST_SCALE = 0.88
CAM = Cam(yaw=0.0, pitch=1.33, scale=SCALE, ox=PIVOT[0], oy=PIVOT[1])

# screen-space names, and the spin that points the figure that way
FACINGS = {"d": 0.0, "r": math.pi / 2, "u": math.pi, "l": -math.pi / 2}
PHASES = 4                      # a full stride, sampled four times
ORDER = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "pink", "grey"]

t0 = time.time()
caches = {}
for fname, ry in FACINGS.items():
    for ph in range(PHASES):
        phase = 2 * math.pi * ph / PHASES
        away = abs(ry - math.pi) < 1e-6           # walking away up the screen
        parts = rotate_parts(scale_parts(guest_parts("walk", phase=phase, face=not away), GUEST_SCALE), ry)
        caches[(fname, ph)] = bake(parts, CAM, TILE, TILE)
    print("  baked facing %s  %.1fs" % (fname, time.time() - t0))

tiles = []
for (fname, ph), cache in caches.items():
    for col in ORDER:
        tiles.append(("w%s%d_%s" % (fname, ph, col), colorize(cache, PALETTE[col])))

COLS = 12
rows = (len(tiles) + COLS - 1) // COLS
atlas = Image.new("RGBA", (COLS * TILE, rows * TILE), (0, 0, 0, 0))
meta = {"tile": TILE, "pivot": PIVOT, "scale": SCALE, "phases": PHASES,
        "facings": list(FACINGS), "frames": {}}
for i, (name, im) in enumerate(tiles):
    x, y = (i % COLS) * TILE, (i // COLS) * TILE
    atlas.alpha_composite(im, (x, y))
    meta["frames"][name] = [x, y]

atlas.save("walk_atlas.png", optimize=True)
json.dump(meta, open("walk_atlas.json", "w"))
print("walk_atlas.png  %d x %d  %.0f KB  (%d frames)"
      % (atlas.size[0], atlas.size[1], os.path.getsize("walk_atlas.png") / 1024, len(tiles)))
b64 = base64.b64encode(open("walk_atlas.png", "rb").read()).decode()
open("walk_atlas_b64.txt", "w").write(b64)
print("data URI  %.0f KB" % (len(b64) / 1024))
