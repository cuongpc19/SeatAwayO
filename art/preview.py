import time
from PIL import Image
from toy3d import *
from assets import *

BG = (238, 243, 250, 255)
W = 400
CAM = Cam(yaw=0.58, pitch=0.30, scale=118, ox=W / 2, oy=W * 0.86)

items = [
    ("bench", bench_parts(), "green"),
    ("idle", guest_parts("idle"), "blue"),
    ("walk", guest_parts("walk", phase=1.15), "red"),
    ("sit", guest_parts("sit"), "yellow"),
    ("chair", armchair_parts(), "purple"),
]

sheet = Image.new("RGBA", (W * len(items), W), BG)
for i, (name, parts, col) in enumerate(items):
    t = time.time()
    c = bake(parts, CAM, W, W)
    sh = contact_shadow(parts, CAM, W, W)
    tile = Image.new("RGBA", (W, W), BG)
    tile.alpha_composite(sh)
    tile.alpha_composite(colorize(c, PALETTE[col]))
    sheet.alpha_composite(tile, (i * W, 0))
    print("  %-6s %5.1fs" % (name, time.time() - t))
sheet.convert("RGB").save("test_sheet.png")
print("ok")
