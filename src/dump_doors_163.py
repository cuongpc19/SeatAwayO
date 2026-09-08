"""Where the door actually is on each seat panel.

The engine guesses: it walks the right-hand wall from the front and takes the
first free cell, because the binary levels it was written for never recorded a
door.  1.63.1 does - every panel prefab carries a door object next to its
SeatAreas, in the same local space - so the guess can be replaced by the real
thing.  Positions come out as grid coordinates on the same lattice the seats
use, plus which wall the door sits against.
"""
import json, os, re, sys, collections
import UnityPy

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "lv/doors_163.json"
DOOR = re.compile(r"door", re.I)   # any name that mentions a door; the wall test filters

env = UnityPy.load(SRC)
go_name, tf = {}, {}
for o in env.objects:
    if o.type.name == "GameObject":
        go_name[o.path_id] = o.read().m_Name
    elif o.type.name in ("Transform", "RectTransform"):
        tf[o.path_id] = o.read()

def pid(p):
    return p.m_PathID if hasattr(p, "m_PathID") else getattr(p, "path_id", 0)

tf_go = {t: pid(v.m_GameObject) for t, v in tf.items()}
go_tf = collections.defaultdict(list)
for t, g in tf_go.items():
    go_tf[g].append(t)
kids = {t: [pid(c) for c in v.m_Children] for t, v in tf.items()}

def walk(t):
    yield go_name.get(tf_go.get(t), ""), t
    for c in kids.get(t, []):
        if c in tf:
            yield from walk(c)

panels = {}
for gid, nm in go_name.items():
    m = re.fullmatch(r"SeatPanel_(\d+)", nm or "")
    if not m:
        continue
    n = int(m.group(1))
    for t in go_tf[gid]:
        nodes = list(walk(t))
        areas = {}
        doors = []
        for cname, ct in nodes:
            a = re.fullmatch(r"SeatArea(?:_(\d+))?", cname or "")
            if a:
                i = int(a.group(1)) if a.group(1) else 0
                if i not in areas:
                    p = tf[ct].m_LocalPosition
                    areas[i] = (round(p.x, 3), round(p.z, 3))
            elif cname == "raypos":
                p = tf[ct].m_LocalPosition
                doors.append(("raypos", round(p.x, 3), round(p.z, 3)))
            elif DOOR.search(cname or ""):
                p = tf[ct].m_LocalPosition
                doors.append((cname, round(p.x, 3), round(p.z, 3)))
        if not areas or not doors:
            continue
        if n in panels and len(panels[n]["_areas"]) >= len(areas):
            continue
        panels[n] = {"_areas": areas, "_doors": doors}
        break

out = {}
for n, d in sorted(panels.items()):
    areas = d["_areas"]
    xs = sorted({x for x, _ in areas.values()})
    zs = sorted({z for _, z in areas.values()})
    W, H = len(xs), len(zs)
    # same mapping the seats use: col 0 at max x, row 0 at max z (the front)
    def cell(x, z):
        col = min(range(W), key=lambda i: abs(xs[W - 1 - i] - x))
        row = min(range(H), key=lambda i: abs(zs[H - 1 - i] - z))
        return col, row
    rec = []
    # Only doors that sit outside the seat lattice are ways in; anything inside
    # it is a prop - several panels carry a decorative `door` at the same spot.
    for nm, x, z in sorted(d["_doors"]):
        # raypos is the cell passengers step into, so it is inside the lattice on
        # purpose; every other door inside it is a prop.
        if nm != "raypos" and xs[0] <= x <= xs[-1] and zs[0] <= z <= zs[-1]:
            continue
        col, row = cell(x, z)
        # which wall it is against: outside the lattice on x means a side door
        side = ("right" if x > xs[-1] else "left" if x < xs[0] else
                "front" if z > zs[-1] else "back" if z < zs[0] else "inside")
        rec.append({"name": nm, "x": x, "z": z, "col": col, "row": row, "wall": side})
    ray = next((r for r in rec if r["name"] == "raypos"), None)
    # A second door, where the panel carries one. Only Firecar does - BusDoor_2,
    # far wall, two rows off the back - and it is the one place in the bundle
    # that says where this game puts a second way in. The board coordinates here
    # are the emitted grid's: column 0 is the low-x wall, row 0 the front.
    second = next((r for r in rec if re.search(r"door_?2$", r["name"], re.I)), None)
    if second:
        second = {"col": W - 1 - second["col"], "row": second["row"]}
    out[str(n)] = {"w": W, "h": H, "doors": rec,
                   # the row the queue walks in on; row 0 is the front everywhere
                   "entryRow": ray["row"] if ray else 0,
                   "second": second}
    print("  SeatPanel_%-3d %dx%d  %s" % (n, W, H,
          "  ".join("%s -> col %d row %d (%s)" % (r["name"], r["col"], r["row"], r["wall"]) for r in rec)))

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
json.dump(out, open(OUT, "w"), separators=(",", ":"))
print("wrote", OUT)
