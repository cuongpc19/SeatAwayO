"""Toy-3D renderer: SDF ray-marching under an orthographic 3/4 camera.

Shading is factorised as  colour = albedo * A + B , where A and B depend only on
geometry. A shape is therefore baked once and recoloured for free - the same
trick the genre uses (one neutral render, tinted per colour at runtime).
"""
import numpy as np
from PIL import Image, ImageFilter

SS = 3
EPS = 8e-4
NEG = -1e9

# ---------------- primitives (world space) ----------------
def sphere(c, r):        return [dict(t="sph", c=np.array(c, float), r=float(r))]
def capsule(a, b, r):    return [dict(t="cap", a=np.array(a, float), b=np.array(b, float), r=float(r))]
def cone(a, ra, b, rb):  return [dict(t="cone", a=np.array(a, float), b=np.array(b, float), ra=float(ra), rb=float(rb))]
def rbox(c, size, r, rot=None):
    h = np.maximum(np.array(size, float) / 2 - r, 1e-6)
    return [dict(t="box", c=np.array(c, float), h=h, r=float(r),
                 R=np.eye(3) if rot is None else np.asarray(rot, float))]

def rotmat(rx=0.0, ry=0.0, rz=0.0):
    cx, sx = np.cos(rx), np.sin(rx); cy, sy = np.cos(ry), np.sin(ry); cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx

def xform(prims, rot=(0, 0, 0), move=(0, 0, 0)):
    R = rotmat(*rot); m = np.asarray(move, float)
    out = []
    for p in prims:
        q = dict(p)
        for k in ("c", "a", "b"):
            if k in q: q[k] = R @ q[k] + m
        if q["t"] == "box": q["R"] = R @ q["R"]
        out.append(q)
    return out

def group(*lists):
    out = []
    for l in lists: out += list(l)
    return out

# ---------------- camera ----------------
class Cam:
    def __init__(self, yaw=0.60, pitch=0.28, scale=110, ox=0, oy=0):
        self.yaw, self.pitch, self.s, self.ox, self.oy = yaw, pitch, scale, ox, oy
        self.V = rotmat(rx=pitch) @ rotmat(ry=yaw)          # world -> view

    def screen(self, p):
        v = np.asarray(p, float) @ self.V.T
        return self.ox + v[..., 0] * self.s, self.oy - v[..., 1] * self.s, v[..., 2] * self.s

    def to_view(self, prims):
        out = []
        for p in prims:
            q = dict(p)
            for k in ("c", "a", "b"):
                if k in q: q[k] = self.V @ q[k]
            if q["t"] == "box": q["R"] = self.V @ q["R"]
            out.append(q)
        return out

# ---------------- signed distance ----------------
def _sd(P, prims):
    d = None
    for p in prims:
        t = p["t"]
        if t == "sph":
            v = P - p["c"]
            s = np.sqrt((v * v).sum(-1)) - p["r"]
        elif t == "cap":
            a, b = p["a"], p["b"]
            ba = b - a
            pa = P - a
            bb = ba @ ba
            h = np.clip((pa @ ba) / bb, 0, 1)[..., None] if bb > 1e-12 else 0.0
            v = pa - ba * h
            s = np.sqrt((v * v).sum(-1)) - p["r"]
        elif t == "cone":
            a, b, r1, r2 = p["a"], p["b"], p["ra"], p["rb"]
            ba = b - a
            l2 = ba @ ba
            if l2 < 1e-12:                       # degenerate -> plain sphere
                v = P - a
                s = np.sqrt((v * v).sum(-1)) - max(r1, r2)
            else:
                rr = r1 - r2
                a2 = l2 - rr * rr
                il2 = 1.0 / l2
                pa = P - a
                y = pa @ ba
                z = y - l2
                w = pa * l2 - ba * y[..., None]
                x2 = (w * w).sum(-1)
                y2 = y * y * l2
                z2 = z * z * l2
                k = np.sign(rr) * rr * rr * x2
                s = np.where(np.sign(z) * a2 * z2 > k,
                             np.sqrt(np.maximum(x2 + z2, 0)) * il2 - r2,
                             np.where(np.sign(y) * a2 * y2 < k,
                                      np.sqrt(np.maximum(x2 + y2, 0)) * il2 - r1,
                                      (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1))
        else:
            q = np.abs((P - p["c"]) @ p["R"]) - p["h"]
            qc = np.maximum(q, 0)
            s = np.sqrt((qc * qc).sum(-1)) + np.minimum(q.max(-1), 0) - p["r"]
        d = s if d is None else np.minimum(d, s)
    return d

def _bounds(prims):
    lo = np.full(3, 1e9)
    hi = np.full(3, -1e9)
    for p in prims:
        t = p["t"]
        if t == "sph":
            lo = np.minimum(lo, p["c"] - p["r"]); hi = np.maximum(hi, p["c"] + p["r"])
        elif t == "cap":
            for k in ("a", "b"):
                lo = np.minimum(lo, p[k] - p["r"]); hi = np.maximum(hi, p[k] + p["r"])
        elif t == "cone":
            lo = np.minimum(lo, p["a"] - p["ra"]); hi = np.maximum(hi, p["a"] + p["ra"])
            lo = np.minimum(lo, p["b"] - p["rb"]); hi = np.maximum(hi, p["b"] + p["rb"])
        else:
            e = np.abs(p["R"]) @ p["h"] + p["r"]
            lo = np.minimum(lo, p["c"] - e); hi = np.maximum(hi, p["c"] + e)
    return lo, hi

def march(prims_world, cam, W, H, steps=110):
    """Orthographic march along -z in view space."""
    pv = cam.to_view(prims_world)
    lo, hi = _bounds(pv)
    x0 = max(int(np.floor((cam.ox + lo[0] * cam.s) * SS)) - 2, 0)
    x1 = min(int(np.ceil((cam.ox + hi[0] * cam.s) * SS)) + 2, W * SS)
    y0 = max(int(np.floor((cam.oy - hi[1] * cam.s) * SS)) - 2, 0)
    y1 = min(int(np.ceil((cam.oy - lo[1] * cam.s) * SS)) + 2, H * SS)
    if x1 <= x0 or y1 <= y0: return None
    yy, xx = np.mgrid[y0:y1, x0:x1]
    vx = (xx / SS - cam.ox) / cam.s
    vy = (cam.oy - yy / SS) / cam.s
    z = np.full(vx.shape, hi[2] + 1e-3)
    zmin = lo[2] - 1e-3
    alive = np.ones(vx.shape, bool)
    for _ in range(steps):
        idx = np.nonzero(alive)
        if idx[0].size == 0: break
        pts = np.stack([vx[idx], vy[idx], z[idx]], -1)
        d = _sd(pts, pv)
        z[idx] -= np.maximum(d, EPS * 0.5)
        alive[idx] = (d > EPS) & (z[idx] > zmin)
    hit = z > zmin
    n = np.zeros(vx.shape + (3,), np.float32)
    if hit.any():
        idx = np.nonzero(hit)
        base = np.stack([vx[idx], vy[idx], z[idx]], -1)
        e = EPS * 4
        g = []
        for k in range(3):
            off = np.zeros(3); off[k] = e
            g.append(_sd(base + off, pv) - _sd(base - off, pv))
        gv = np.stack(g, -1)
        gv /= np.maximum(np.linalg.norm(gv, axis=-1, keepdims=True), 1e-9)
        n[idx] = gv
    return z, n, hit, (x0, y0, x1, y1)

# ---------------- shading ----------------
LIGHT = np.array([-0.38, 0.68, 0.62]); LIGHT /= np.linalg.norm(LIGHT)
HALF = LIGHT + np.array([0., 0., 1.]); HALF /= np.linalg.norm(HALF)

def bake(parts, cam, W, H):
    """parts: [{geo, k | fixed, spec, shin, amb, rim, tone}]"""
    h, w = H * SS, W * SS
    zbuf = np.full((h, w), NEG, np.float32)
    A = np.zeros((h, w), np.float32)
    B = np.zeros((h, w, 3), np.float32)
    K = np.zeros((h, w), np.float32)
    F = np.zeros((h, w, 3), np.float32)
    cov = np.zeros((h, w), bool)
    for p in parts:
        out = march(p["geo"], cam, W, H)
        if out is None: continue
        z, n, hit, (bx0, by0, bx1, by1) = out
        if not hit.any(): continue
        spec = p.get("spec", .5); shin = p.get("shin", 22); amb = p.get("amb", .38)
        rim = p.get("rim", .22); tone = p.get("tone", .52)
        rim_col = np.array(p.get("rim_col", (255, 255, 255)), np.float32)
        lam = np.clip(n @ LIGHT, 0, 1)
        sp = np.clip(n @ HALF, 0, 1) ** shin
        rimf = (1 - np.clip(n[..., 2], 0, 1)) ** 3
        a = (tone + (1 - tone) * (amb + (1 - amb) * lam)).astype(np.float32)
        b = (255 * spec * sp[..., None] + rim_col * (rim * rimf)[..., None]).astype(np.float32)
        win = hit & (z > zbuf[by0:by1, bx0:bx1])
        if not win.any(): continue
        zbuf[by0:by1, bx0:bx1][win] = z[win]
        A[by0:by1, bx0:bx1][win] = a[win]
        B[by0:by1, bx0:bx1][win] = b[win]
        cov[by0:by1, bx0:bx1] |= win
        if "fixed" in p:
            F[by0:by1, bx0:bx1][win] = np.array(p["fixed"], np.float32)
            K[by0:by1, bx0:bx1][win] = 0.0
        else:
            K[by0:by1, bx0:bx1][win] = p.get("k", 1.0)
            F[by0:by1, bx0:bx1][win] = 0.0
    return dict(A=A, B=B, K=K, F=F, cov=cov, W=W, H=H)

def colorize(cache, base, out_size=None):
    base = np.array(base, np.float32)
    K, F, A, B, cov = cache["K"], cache["F"], cache["A"], cache["B"], cache["cov"]
    albedo = np.where(K[..., None] > 0, np.clip(base * K[..., None], 0, 255), F)
    col = np.clip(albedo * A[..., None] + B, 0, 255)
    rgba = np.dstack([col, cov.astype(np.float32) * 255]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    return im.resize(out_size or (cache["W"], cache["H"]), Image.LANCZOS)

def contact_shadow(parts, cam, W, H, blur=6, alpha=100, lift=1.6):
    """Flatten everything near the floor onto y=0 and blur it."""
    flat = []
    for p in parts:
        for q in p["geo"]:
            r = dict(q); skip = False
            for k in ("c", "a", "b"):
                if k in r:
                    v = r[k].copy()
                    if v[1] - r.get("r", r.get("ra", 0.0)) > lift: skip = True; break
                    v[1] = 0.0
                    r[k] = v
            if skip: continue
            if r["t"] == "box":
                r["h"] = np.array([r["h"][0], 1e-3, r["h"][2]])
                r["R"] = np.eye(3)
            flat.append(dict(geo=[r], k=1.0))
    if not flat:
        return Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c = bake(flat, cam, W, H)
    a = Image.fromarray((c["cov"].astype(np.float32) * alpha).astype(np.uint8))
    a = a.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", (W, H), (16, 24, 48, 255))
    out.putalpha(a)
    return out

def scaled(prims, s):
    """Uniform scale about the origin."""
    out = []
    for p in prims:
        q = dict(p)
        for k in ("c", "a", "b"):
            if k in q: q[k] = q[k] * s
        for k in ("r", "ra", "rb"):
            if k in q: q[k] = q[k] * s
        if q["t"] == "box": q["h"] = q["h"] * s
        out.append(q)
    return out

def scale_parts(parts, s):
    return [dict(p, geo=scaled(p["geo"], s)) for p in parts]

def rotate_parts(parts, ry):
    """Spin a whole assembled figure about the vertical axis."""
    return [dict(p, geo=xform(p["geo"], rot=(0, ry, 0))) for p in parts]
