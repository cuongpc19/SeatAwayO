import sys, re, collections
import UnityPy
env = UnityPy.load(sys.argv[1])
go, tf = {}, {}
for o in env.objects:
    if o.type.name == "GameObject": go[o.path_id] = o.read().m_Name
    elif o.type.name in ("Transform","RectTransform"): tf[o.path_id] = o.read()
def pid(p): return p.m_PathID if hasattr(p,"m_PathID") else getattr(p,"path_id",0)
tfg = {t: pid(v.m_GameObject) for t,v in tf.items()}
gtf = collections.defaultdict(list)
for t,g in tfg.items(): gtf[g].append(t)
kids = {t:[pid(c) for c in v.m_Children] for t,v in tf.items()}
def walk(t):
    yield go.get(tfg.get(t),""), t
    for c in kids.get(t,[]):
        if c in tf: yield from walk(c)
print("panel  vehicle-grid   door           raw x     raw z    -> board col,row (col0 = min x, row0 = max z)")
for gid, nm in sorted(go.items(), key=lambda kv: kv[1]):
    m = re.fullmatch(r"SeatPanel_(\d+)", nm or "")
    if not m: continue
    n = int(m.group(1))
    if n > 16: continue
    for t in gtf[gid]:
        nodes = list(walk(t))
        areas=[(round(tf[ct].m_LocalPosition.x,2), round(tf[ct].m_LocalPosition.z,2))
               for x,ct in nodes if re.fullmatch(r"SeatArea(_\d+)?", x or "")]
        if not areas: continue
        xs=sorted({x for x,_ in areas}); zs=sorted({z for _,z in areas})
        xs2 = xs[1:]                      # the extra lane is dropped on the way in
        W,H = len(xs2), len(zs)
        def cell(px,pz):
            c = min(range(W), key=lambda i: abs(xs2[i]-px))
            r = min(range(H), key=lambda i: abs(zs[H-1-i]-pz))
            return c, r
        for x, ct in nodes:
            if not re.match(r"(Bus)?Door_?\d", x or "", re.I): continue
            p = tf[ct].m_LocalPosition
            c,r = cell(round(p.x,2), round(p.z,2))
            print("  %-4d %dx%-4d %-14s %7.2f %8.2f    col %d row %d" % (n, W, H, x, p.x, p.z, c, r))
        break
