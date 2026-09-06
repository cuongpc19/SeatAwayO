"""Render the deliverables: asset sheets + a gameplay board."""
import os, time
import numpy as np
from PIL import Image, ImageDraw
from toy3d import *
from assets import *
from board import build_board, GUEST_SCALE

os.makedirs("out", exist_ok=True)
os.makedirs("out/sprites", exist_ok=True)
BG = (240, 244, 250, 255)
ORDER = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "pink", "grey"]


def hero(parts, size=420, scale=None, oy=0.86):
    scale = scale or size * 0.29
    cam = Cam(yaw=0.58, pitch=0.30, scale=scale, ox=size / 2, oy=size * oy)
    return bake(parts, cam, size, size), contact_shadow(parts, cam, size, size), cam


def tile(cache, sh, colour, size, bg=BG):
    im = Image.new("RGBA", (size, size), bg)
    im.alpha_composite(sh)
    im.alpha_composite(colorize(cache, PALETTE[colour]))
    return im


def sheet(rows, size, bg=BG, gap=0):
    w = max(len(r) for r in rows)
    out = Image.new("RGBA", (w * size + gap * (w - 1), len(rows) * size + gap * (len(rows) - 1)), bg)
    for y, row in enumerate(rows):
        for x, im in enumerate(row):
            out.alpha_composite(im, (x * (size + gap), y * (size + gap)))
    return out


t0 = time.time()

# ---------- 1. the seat, all nine colours ----------
S = 300
cb, sb, _ = hero(bench_parts(), S, scale=S * 0.30, oy=0.80)
bench_row = [tile(cb, sb, c, S) for c in ORDER]
sheet([bench_row[:5], bench_row[5:] + [Image.new("RGBA", (S, S), BG)]], S).convert("RGB") \
    .save("out/01_bench_palette.png")

# ---------- 2. the guest, all nine colours ----------
cg, sg, _ = hero(guest_parts("idle"), S, scale=S * 0.26)
guest_row = [tile(cg, sg, c, S) for c in ORDER]
sheet([guest_row[:5], guest_row[5:] + [Image.new("RGBA", (S, S), BG)]], S).convert("RGB") \
    .save("out/02_guest_palette.png")

# ---------- 3. poses ----------
poses = [("idle", guest_parts("idle")),
         ("walk_a", guest_parts("walk", phase=1.15)),
         ("walk_b", guest_parts("walk", phase=-1.15)),
         ("sit", guest_parts("sit")),
         ("cheer", guest_parts("cheer"))]
pose_tiles = []
for name, parts in poses:
    c, s, _ = hero(parts, S, scale=S * 0.26)
    pose_tiles.append(tile(c, s, "blue", S))
    for col in ORDER:
        colorize(c, PALETTE[col]).save(f"out/sprites/guest_{name}__{col}.png")
sheet([pose_tiles], S).convert("RGB").save("out/03_guest_poses.png")

# ---------- 4. seat variants ----------
seats = [("bench", bench_parts()), ("armchair", armchair_parts())]
seat_tiles = []
for name, parts in seats:
    c, s, _ = hero(parts, S, scale=S * 0.30, oy=0.80)
    seat_tiles.append(tile(c, s, "green" if name == "bench" else "purple", S))
    for col in ORDER:
        colorize(c, PALETTE[col]).save(f"out/sprites/{name}__{col}.png")
fc, fs, _ = hero(fence_post_parts(), S, scale=S * 0.30, oy=0.78)
seat_tiles.append(tile(fc, fs, "grey", S))
sheet([seat_tiles], S).convert("RGB").save("out/04_seat_variants.png")

print("assets %.1fs" % (time.time() - t0))

# ---------- 5. the board ----------
G, R, Y, P, B, O, X = "green", "red", "yellow", "purple", "blue", "orange", "grey"
def cell(b, g=None): return dict(bench=b, guest=g)

grid = [
    [cell(G, G), cell(G, G), cell(X),    None,       cell(P, P), cell(P),    cell(Y, Y), cell(Y)],
    [cell(R, R), cell(R),    cell(X),    cell(B, B), cell(B),    cell(B, B), cell(X),    cell(O, O)],
    [None,       cell(Y, Y), cell(Y),    cell(X),    cell(G),    cell(G, G), cell(P, P), cell(P)],
    [cell(B, B), cell(B),    cell(O, O), cell(O),    cell(X),    cell(R, R), cell(R),    cell(X)],
    [cell(P),    cell(P, P), cell(X),    cell(Y, Y), cell(Y),    cell(X),    cell(B, B), cell(B)],
]
queue = [R, R, Y, B, P, G, O, B]

t = time.time()
st = build_board(grid, queue, walker=(G, (2.9, 0, 4.9)), W=1560, H=860, scale=66)
st.compose().convert("RGB").save("out/05_board.png")
print("board %.1fs" % (time.time() - t))
print("total %.1fs" % (time.time() - t0))
