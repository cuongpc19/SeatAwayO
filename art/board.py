"""Compose a playable-looking board from the baked assets.

Orthographic projection is linear, so an asset is baked once at the world origin
and then blitted at the screen offset of its world position - one bake per asset,
not one per instance.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from toy3d import *
from assets import *

GRASS  = (108, 190, 104)
DIRT_A = (178, 142,  94)
DIRT_B = (158, 122,  78)
LANE   = (206, 190, 152)
SKY    = (146, 212, 246)
GUEST_SCALE = 0.88

SX, SZ = 1.88, 1.78          # grid spacing


class Stage:
    def __init__(self, W, H, cam, tile=240):
        self.W, self.H, self.cam = W, H, cam
        self.tile = tile
        # sprite camera: same orientation/scale, pivot inside a small tile
        self.scam = Cam(cam.yaw, cam.pitch, cam.s, tile * 0.5, tile * 0.72)
        self.sprites = {}
        self.items = []
        self.canvas = Image.new("RGBA", (W, H), SKY + (255,))
        self.shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    def define(self, name, parts, shadow=True):
        t = self.tile
        cache = bake(parts, self.scam, t, t)
        sh = contact_shadow(parts, self.scam, t, t, blur=4, alpha=92) if shadow else None
        self.sprites[name] = dict(cache=cache, shadow=sh, tinted={})

    def _tint(self, name, colour):
        s = self.sprites[name]
        key = colour if isinstance(colour, str) else tuple(colour)
        if key not in s["tinted"]:
            rgb = PALETTE[colour] if isinstance(colour, str) else colour
            s["tinted"][key] = colorize(s["cache"], rgb)
        return s["tinted"][key]

    def add(self, name, colour, pos, shadow=True, bias=0.0):
        self.items.append((np.asarray(pos, float), name, colour, shadow, bias))

    # ---------- flat floor painting ----------
    def _quad(self, layer, p3, fill):
        sx, sy, _ = self.cam.screen(np.asarray(p3, float))
        ImageDraw.Draw(layer).polygon(list(zip(sx, sy)), fill=fill + (255,))

    def floor(self, rows, cols, lane_x):
        lay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        x0, z0 = -(cols - 1) / 2 * SX, -(rows - 1) / 2 * SZ
        pad = 1.30
        L, R = x0 - pad, x0 + (cols - 1) * SX + pad
        T, B = z0 - pad, z0 + (rows - 1) * SZ + pad
        self._quad(lay, [[L - 8, 0, T - 8], [R + 9, 0, T - 8],
                         [R + 9, 0, B + 9], [L - 8, 0, B + 9]], GRASS)
        self._quad(lay, [[lane_x - .85, .002, T - 1.0], [lane_x + .85, .002, T - 1.0],
                         [lane_x + .85, .002, B + 4.4], [lane_x - .85, .002, B + 4.4]], LANE)
        for r in range(rows):
            for c in range(cols):
                a, b = x0 + (c - .5) * SX, x0 + (c + .5) * SX
                u, v = z0 + (r - .5) * SZ, z0 + (r + .5) * SZ
                self._quad(lay, [[a, .004, u], [b, .004, u], [b, .004, v], [a, .004, v]],
                           DIRT_A if (r + c) % 2 == 0 else DIRT_B)
        self.canvas.alpha_composite(lay)
        return x0, z0, (L, R, T, B)

    def draw(self):
        px, py = self.cam.ox, self.cam.oy
        spx, spy = self.scam.ox, self.scam.oy
        keys = [self.cam.screen(it[0][None])[2][0] + it[4] for it in self.items]
        for i in np.argsort(keys):
            pos, name, colour, sh, _bias = self.items[i]
            sx, sy, _ = self.cam.screen(pos[None])
            dx = int(round(sx[0] - spx)); dy = int(round(sy[0] - spy))
            s = self.sprites[name]
            if sh and s["shadow"] is not None:
                self.shadow.alpha_composite(s["shadow"], (dx, dy))
            self.canvas.alpha_composite(self._tint(name, colour), (dx, dy))
        out = Image.new("RGBA", (self.W, self.H), SKY + (255,))
        out.alpha_composite(self.canvas)
        return out

    def compose(self):
        """Shadows go under everything except the floor, so rebuild the stack."""
        px, py = self.cam.ox, self.cam.oy
        spx, spy = self.scam.ox, self.scam.oy
        shadow = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        body = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        keys = [self.cam.screen(it[0][None])[2][0] + it[4] for it in self.items]
        for i in np.argsort(keys):
            pos, name, colour, sh, _bias = self.items[i]
            sx, sy, _ = self.cam.screen(pos[None])
            dx = int(round(sx[0] - spx)); dy = int(round(sy[0] - spy))
            s = self.sprites[name]
            if sh and s["shadow"] is not None:
                shadow.alpha_composite(s["shadow"], (dx, dy))
            body.alpha_composite(self._tint(name, colour), (dx, dy))
        out = self.canvas.copy()
        out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(1.5)))
        out.alpha_composite(body)
        return out


def rail(length, axis):
    return fence_rail_parts(length, axis)


def build_board(grid, queue, walker=None, W=1320, H=830, scale=68):
    rows, cols = len(grid), len(grid[0])
    cam = Cam(yaw=0.15, pitch=0.62, scale=scale, ox=W * 0.46, oy=H * 0.50)
    st = Stage(W, H, cam, tile=int(scale * 4.2))

    lane_x = -(cols - 1) / 2 * SX + (cols - 1) * SX + 3.05
    x0, z0, (L, R, T, B) = st.floor(rows, cols, lane_x)

    st.define("bench", bench_parts())
    st.define("sit", scale_parts(guest_parts("sit"), GUEST_SCALE))
    st.define("idle", scale_parts(guest_parts("idle"), GUEST_SCALE))
    st.define("walkA", scale_parts(guest_parts("walk", phase=1.15), GUEST_SCALE))
    st.define("walkB", scale_parts(guest_parts("walk", phase=-1.15), GUEST_SCALE))
    st.define("post", fence_post_parts(), shadow=False)
    st.define("railX", rail(R - L, "x"), shadow=False)
    st.define("railZ", rail(B - T, "z"), shadow=False)

    # fence: two long rails per axis, posts at the corners
    st.add("railX", WOOD, ((L + R) / 2, 0, T), shadow=False)
    st.add("railX", WOOD, ((L + R) / 2, 0, B), shadow=False)
    st.add("railZ", WOOD, (L, 0, (T + B) / 2), shadow=False)
    st.add("railZ", WOOD, (R, 0, (T + B) / 2), shadow=False)
    for x in np.linspace(L, R, cols + 1):
        st.add("post", WOOD, (x, 0, T), shadow=False)
        st.add("post", WOOD, (x, 0, B), shadow=False)
    for z in np.linspace(T, B, rows + 1):
        st.add("post", WOOD, (L, 0, z), shadow=False)
        st.add("post", WOOD, (R, 0, z), shadow=False)

    # benches + seated guests
    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            if not cell: continue
            pos = (x0 + c * SX, 0, z0 + r * SZ)
            st.add("bench", cell["bench"], pos)
            if cell.get("guest"):
                st.add("sit", cell["guest"], (pos[0], 0.06, pos[2] - 0.05), shadow=False, bias=0.30)

    # queue on the lane
    for i, colour in enumerate(queue):
        st.add("idle" if i % 2 else "walkB", colour,
               (lane_x, 0, B + 3.1 - i * 1.02))

    if walker:
        colour, wpos = walker
        st.add("walkA", colour, wpos)
    return st
