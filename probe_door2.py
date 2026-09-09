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
        areas = [(tf[ct].m_LocalPosition.x, tf[ct].m_LocalPosition.z)
                 for n,ct in nodes if re.fullmatch(r"SeatArea(_\d+)?", n or "")]
        if not areas: continue
        xs=sorted({round(x,2) for x,_ in areas}); zs=sorted({round(z,2) for _,z in areas})
        print("== %s  lattice x %s..%s  z %s..%s" % (nm, xs[0], xs[-1], zs[0], zs[-1]))
        out=[]
        for n, ct in nodes:
            if re.fullmatch(r"SeatArea(_\d+)?", n or ""): continue
            p = tf[ct].m_LocalPosition
            if not (xs[0]-0.7 <= round(p.x,2) <= xs[-1]+0.7 and zs[0]-0.7 <= round(p.z,2) <= zs[-1]+0.7):
                out.append((n, round(p.x,1), round(p.z,1)))
        seen=set(); uniq=[]
        for n,x,z in out:
            k=re.sub(r"\d+","#",n)
            if k in seen: continue
            seen.add(k); uniq.append((n,x,z))
        print("   outside the lattice:", [(n.encode('ascii','replace').decode(),x,z) for n,x,z in uniq[:22]])
        break
