"""Dump the seat-panel geometry the level JSON indexes into.

A level names a `seatPanelNumber` (0-16, absent means 0) and then addresses
slots by `seatNumber`; the coordinates live in the SeatPanel_N prefabs as
SeatArea children.  Slot 0 is the child named plain `SeatArea`, slots 1..N are
`SeatArea_1`..`SeatArea_N`.  A panel appears more than once in the bundle, so
every instance is walked and the richest one kept.
"""
import json, math, os, re, sys, collections
import UnityPy

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "lv/panels_163.json"

env = UnityPy.load(SRC)

go_name, tf_by_id = {}, {}
for obj in env.objects:
    t = obj.type.name
    if t == "GameObject":
        go_name[obj.path_id] = obj.read().m_Name
    elif t in ("Transform", "RectTransform"):
        tf_by_id[obj.path_id] = obj.read()

def pid(p):
    return p.m_PathID if hasattr(p, "m_PathID") else getattr(p, "path_id", 0)

tf_go = {tid: pid(tf.m_GameObject) for tid, tf in tf_by_id.items()}
go_tf = collections.defaultdict(list)
for tid, g in tf_go.items():
    go_tf[g].append(tid)
kids = {tid: [pid(c) for c in tf.m_Children] for tid, tf in tf_by_id.items()}

def euler_z(q):
    x, y, z, w = q.x, q.y, q.z, q.w
    return round(math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))), 2)

def slot_index(name):
    if name == "SeatArea":
        return 0
    m = re.fullmatch(r"SeatArea_(\d+)", name or "")
    return int(m.group(1)) if m else None

def areas_under(tid):
    """SeatArea slots anywhere in this panel instance's subtree."""
    out, stack = {}, [tid]
    while stack:
        cur = stack.pop()
        i = slot_index(go_name.get(tf_go.get(cur), ""))
        if i is not None and i not in out:
            tf = tf_by_id[cur]
            p = tf.m_LocalPosition
            out[i] = {"x": round(p.x, 3), "y": round(p.y, 3), "z": round(p.z, 3),
                      "rotZ": euler_z(tf.m_LocalRotation)}
        stack.extend(c for c in kids.get(cur, []) if c in tf_by_id)
    return out

panels = {}
for gid, nm in go_name.items():
    m = re.fullmatch(r"SeatPanel_(\d+)", nm or "")
    if not m:
        continue
    n = int(m.group(1))
    for tid in go_tf.get(gid, []):
        a = areas_under(tid)
        if len(a) > len(panels.get(n, {})):
            panels[n] = a

for n in sorted(panels):
    ks = sorted(panels[n])
    gaps = [i for i in range(max(ks) + 1) if i not in panels[n]] if ks else []
    print("  SeatPanel_%-3d slots=%-4d range=%s-%s gaps=%s"
          % (n, len(ks), ks[0], ks[-1], gaps or "none"))
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
json.dump({str(n): {str(k): v for k, v in sorted(panels[n].items())} for n in sorted(panels)},
          open(OUT, "w"), separators=(",", ":"))
print("wrote", OUT, "%.0f KB" % (os.path.getsize(OUT) / 1024))
