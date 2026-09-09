import sys, collections
import UnityPy
env = UnityPy.load(sys.argv[1])
go, comp = {}, collections.defaultdict(list)
objs = {}
for o in env.objects:
    objs[o.path_id] = o
    if o.type.name == "GameObject":
        d = o.read(); go[o.path_id] = d
def pid(p): return p.m_PathID if hasattr(p,"m_PathID") else getattr(p,"path_id",0)
for want in ("Cadillac", "Limo"):
    for gid, d in go.items():
        if (d.m_Name or "") != want: continue
        print("==", want)
        for c in d.m_Components:
            o = objs.get(pid(c))
            if not o: continue
            print("   component:", o.type.name)
            if o.type.name == "MeshFilter":
                mf = o.read()
                mo = objs.get(pid(mf.m_Mesh))
                if mo:
                    m = mo.read()
                    print("      mesh %r  submeshes=%d  verts=%s"
                          % (m.m_Name, len(getattr(m, "m_SubMeshes", []) or []),
                             getattr(m, "m_VertexCount", "?")))
                    for i, sm in enumerate(getattr(m, "m_SubMeshes", []) or []):
                        lc = getattr(sm, "m_LocalAABB", None)
                        if lc:
                            c0, e = lc.m_Center, lc.m_Extent
                            print("        sub %d  centre x=%7.2f y=%6.2f z=%7.2f   size %5.2f x %5.2f x %5.2f"
                                  % (i, c0.x, c0.y, c0.z, e.x*2, e.y*2, e.z*2))
            if o.type.name == "MeshRenderer":
                mr = o.read()
                mats = []
                for mm in getattr(mr, "m_Materials", []) or []:
                    md = objs.get(pid(mm))
                    mats.append(md.read().m_Name if md else "?")
                print("      materials:", mats)
        break
