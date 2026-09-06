"""Compose a gameplay board from the baked sprites."""
import pickle, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from toy3d import Cam, SS
from toy3d import colorize
from assets import PALETTE

CACHE = pickle.load(open("cache.pkl", "rb"))
S = CACHE["seat"]["W"]
BAKE_SCALE, BAKE_OX, BAKE_OY = 132.0, S/2, S*0.86

def sprite(name, colour, zoom):
    key = (name, colour, round(zoom, 4))
    if key not in _cache:
        im = colorize(CACHE[name], PALETTE[colour])
        sh = CACHE[name]["shadow"]
        if zoom != 1.0:
            n = (max(1, int(S*zoom)), max(1, int(S*zoom)))
            im = im.resize(n, Image.LANCZOS); sh = sh.resize(n, Image.LANCZOS)
        _cache[key] = (im, sh)
    return _cache[key]
_cache = {}

def place(canvas, name, colour, pos, cam, shadow_layer=None):
    zoom = cam.s / BAKE_SCALE
    im, sh = sprite(name, colour, zoom)
    x, y, z = cam.screen(np.array([pos], float))
    ox = int(round(x[0] - BAKE_OX*zoom)); oy = int(round(y[0] - BAKE_OY*zoom))
    if shadow_layer is not None: shadow_layer.alpha_composite(sh, (ox, oy))
    canvas.alpha_composite(im, (ox, oy))
    return z[0]

def floor_quad(canvas, cam, x0, x1, z0, z1, top=(126,196,124), side=(88,150,92), h=0.30):
    pts = np.array([[x0,0,z1],[x1,0,z1],[x1,0,z0],[x0,0,z0]], float)
    sx, sy, _ = cam.screen(pts)
    poly = list(zip(sx, sy))
    lay = Image.new("RGBA", canvas.size, (0,0,0,0)); d = ImageDraw.Draw(lay)
    front = [(sx[0], sy[0]+h*cam.s), (sx[1], sy[1]+h*cam.s), (sx[1], sy[1]), (sx[0], sy[0])]
    right = [(sx[1], sy[1]+h*cam.s), (sx[2], sy[2]+h*cam.s), (sx[2], sy[2]), (sx[1], sy[1])]
    d.polygon(right, fill=tuple(int(c*0.80) for c in side)+(255,))
    d.polygon(front, fill=side+(255,))
    d.polygon(poly, fill=top+(255,))
    canvas.alpha_composite(lay)

def render_board(grid, queue, cols_spacing=1.42, rows_spacing=1.62,
                 W=1200, H=900, scale=64, sky=(214,236,252)):
    rows, cols = len(grid), len(grid[0])
    cam = Cam(yaw=0.42, pitch=0.34, scale=scale, ox=W*0.5, oy=H*0.70)
    canvas = Image.new("RGBA", (W, H), sky + (255,))
    shadows = Image.new("RGBA", (W, H), (0,0,0,0))

    x0 = -(cols-1)/2*cols_spacing; z0 = -(rows-1)/2*rows_spacing
    floor_quad(canvas, cam,
               x0-1.15, x0+(cols-1)*cols_spacing+1.15,
               z0-1.15, z0+(rows-1)*rows_spacing+2.9)

    items = []
    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            if cell is None: continue
            pos = (x0 + c*cols_spacing, 0, z0 + r*rows_spacing)
            items.append((pos, cell))
    for i, (colour, pose) in enumerate(queue):
        pos = (x0 + (cols-1)/2*cols_spacing - i*0.95,
               0, z0 + (rows-1)*rows_spacing + 2.15)
        items.append((pos, (None, colour, pose)))

    items.sort(key=lambda it: cam.screen(np.array([it[0]], float))[2][0])
    for pos, cell in items:
        seat_col, occ_col, pose = cell
        if seat_col is not None:
            place(canvas, "seat", seat_col, pos, cam, shadows)
        if occ_col is not None:
            nm = "char_sit" if pose == "sit" else pose
            dz = 0.02 if pose == "sit" else 0.0
            y  = 0.66 if pose == "sit" else 0.0
            place(canvas, nm, occ_col, (pos[0], y, pos[2]+dz), cam,
                  None if pose == "sit" else shadows)
    out = Image.new("RGBA", (W, H), sky + (255,))
    out.alpha_composite(shadows.filter(ImageFilter.GaussianBlur(2)))
    out.alpha_composite(canvas)
    return out
