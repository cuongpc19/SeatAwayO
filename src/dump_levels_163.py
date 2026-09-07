"""Dump the level JSON TextAssets out of the 1.63.1 datapack bundle.

1.63.1 dropped the binary LevelCfModel ScriptableObjects that decode_levels.py
reads; every level now ships as a TextAsset named after its id holding plain
JSON.  This writes them to one file keyed by id.
"""
import json, os, re, sys
import UnityPy

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "lv/levels_163_raw.json"

env = UnityPy.load(SRC)
levels, bad = {}, 0
for obj in env.objects:
    if obj.type.name != "TextAsset":
        continue
    d = obj.read()
    nm = getattr(d, "m_Name", "") or ""
    if not re.fullmatch(r"\d+", nm):
        continue
    try:
        levels[int(nm)] = json.loads(d.m_Script)
    except Exception:
        bad += 1

print("levels parsed :", len(levels))
print("unparseable   :", bad)
print("id range      :", min(levels), "-", max(levels))
missing = [i for i in range(min(levels), max(levels) + 1) if i not in levels]
print("gaps in range :", len(missing), missing[:20])
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
json.dump({str(k): levels[k] for k in sorted(levels)}, open(OUT, "w"), separators=(",", ":"))
print("wrote", OUT, "%.0f KB" % (os.path.getsize(OUT) / 1024))
print("\nkeys of level", min(levels), ":", json.dumps(levels[min(levels)])[:600])
