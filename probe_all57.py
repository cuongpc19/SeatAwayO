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
for gid, nm in go.items():
    m = re.fullmatch(r"SeatPanel_(5|7)", nm or "")
    if not m: continue
    for t in gtf[gid]:
        nodes = list(walk(t))
        if not any(n.startswith("SeatArea") for n,_ in nodes): continue
        areas=[(tf[ct].m_LocalPosition.x, tf[ct].m_LocalPosition.z) for n,ct in nodes if re.fullmatch(r"SeatArea(_\d+)?", n or "")]
        xs=sorted({round(x,2) for x,_ in areas})
        print("== %s   seat columns x = %s" % (nm, xs))
        # anything sitting at or beyond the LEFT edge
        left=[]
        for n,ct in nodes:
            p=tf[ct].m_LocalPosition
            if round(p.x,2) <= xs[0] + 0.1 and not re.fullmatch(r"SeatArea(_\d+)?", n or ""):
                left.append((n, round(p.x,2), round(p.z,2)))
        seen=set(); out=[]
        for n,x,z in left:
            k=re.sub(r"\d+","#",n)
            if k in seen: continue
            seen.add(k); out.append((n.encode('ascii','replace').decode(),x,z))
        print("   objects at or past the left edge (x <= %.1f):" % (xs[0]+0.1))
        for o in out[:18]: print("      ", o)
        break
