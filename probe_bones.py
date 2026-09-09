import sys, collections, re
import UnityPy
env = UnityPy.load(sys.argv[1])
objs = {o.path_id: o for o in env.objects}
go = {p: o.read() for p, o in objs.items() if o.type.name == "GameObject"}
tf = {p: o.read() for p, o in objs.items() if o.type.name in ("Transform", "RectTransform")}
def pid(p): return p.m_PathID if hasattr(p, "m_PathID") else getattr(p, "path_id", 0)
tfg = {t: pid(v.m_GameObject) for t, v in tf.items()}
for want in ("Cadillac", "Limo", "firecar"):
    for gid, d in go.items():
        if (d.m_Name or "").lower() != want.lower(): continue
        for c in d.m_Components:
            o = objs.get(pid(c))
            if not o or o.type.name != "SkinnedMeshRenderer": continue
            smr = o.read()
            bones = getattr(smr, "m_Bones", []) or []
            print("== %s : %d bones" % (want, len(bones)))
            for b in bones:
                t = tf.get(pid(b))
                if not t: continue
                nm = go.get(tfg.get(pid(b)))
                nm = nm.m_Name if nm else "?"
                p = t.m_LocalPosition
                print("     %-30s x=%7.2f y=%6.2f z=%7.2f" % (nm.encode('ascii','replace').decode()[:30], p.x, p.y, p.z))
            break
        break
