import sys, re, collections
import UnityPy
env = UnityPy.load(sys.argv[1])
hits = collections.defaultdict(set)
for o in env.objects:
    t = o.type.name
    if t not in ("GameObject","Sprite","Texture2D","Material","MonoBehaviour","AnimationClip","Mesh"): continue
    try: nm = o.read().m_Name or ""
    except Exception: continue
    if re.search(r"hard|zor\b|spike|danger|warn|skull|fire\b|flame", nm, re.I):
        hits[t].add(nm)
for t in sorted(hits):
    names = sorted(hits[t])
    print("%s (%d):" % (t, len(names)))
    for n in names[:22]: print("    ", n.encode("ascii","replace").decode())
    if len(names) > 22: print("     ... +%d more" % (len(names)-22))
