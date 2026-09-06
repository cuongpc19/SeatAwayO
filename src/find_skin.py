"""What does the shipped game say about themes? The level records carry none, so
the answer is in the config assets beside them."""
import UnityPy, re, collections

SRC = (r"C:/Users/admin/AppData/Local/Temp/claude/C--Users-admin/"
       r"3beaed4b-e1cd-4d23-aa1b-7645b344a31c/scratchpad/seataway/assets/bin/Data/data.unity3d")

env = UnityPy.load(SRC)
kinds = collections.Counter()
hits = []
for obj in env.objects:
    kinds[obj.type.name] += 1
    if obj.type.name not in ("MonoBehaviour", "TextAsset"):
        continue
    try:
        d = obj.read()
        name = getattr(d, "m_Name", "") or getattr(d, "name", "")
    except Exception:
        continue
    if re.search(r"skin|cinema|config|chair|ground|human", str(name), re.I):
        hits.append((obj.type.name, str(name), obj.path_id))

print("object kinds:", dict(kinds.most_common(10)))
print("\nassets whose name mentions a skin or a config:")
for t, n, pid in sorted(hits)[:60]:
    print("   %-14s %-42s %d" % (t, n, pid))
print("total:", len(hits))
