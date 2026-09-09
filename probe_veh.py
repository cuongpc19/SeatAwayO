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
def walk(t, d=0):
    yield go.get(tfg.get(t),""), t, d
    for c in kids.get(t,[]):
        if c in tf: yield from walk(c, d+1)
for want in ("Cadillac", "Limo"):
    for gid, nm in go.items():
        if nm != want: continue
        for t in gtf[gid]:
            nodes = list(walk(t))
            pass
            print("== %s : %d nodes" % (want, len(nodes)))
            for n, ct, d in nodes[:40]:
                p = tf[ct].m_LocalPosition
                print("   %s%-26s x=%7.2f z=%7.2f" % ("  "*d, n.encode('ascii','replace').decode()[:26], p.x, p.z))
            break
        break
