"""Is the exported level set actually identical to what is in the APK?

Three questions:
  1. do some level names ship more than one distinct board, and did I silently
     pick one of them?
  2. does the export round-trip - re-derive it from the raw bytes and diff?
  3. what did the export drop compared to the decoded struct?
"""
import pickle, json, collections, hashlib

raws = pickle.load(open("lv/raws.pkl", "rb"))
from decode_levels import parse_level

# ---- 1. duplicate names with different content ----
by_name = collections.defaultdict(list)
for nm, raw in raws:
    by_name[nm].append(raw)

multi = {nm: {hashlib.sha1(r).hexdigest() for r in rs} for nm, rs in by_name.items()}
dupe_names = {nm: h for nm, h in multi.items() if len(h) > 1}
print("distinct level names        :", len(by_name))
print("names shipping >1 board     :", len(dupe_names))

# how different are the variants?
def sig(d):
    return (d["mapSizeW"], d["mapSizeH"], d["timeLimit"],
            tuple(sorted((s[1], s[2], s[3], s[4], s[5]) for s in d["seats"])),
            tuple(sorted(u[2] for u in d["users"])))

same_board, diff_board = 0, []
for nm in dupe_names:
    sigs = {sig(parse_level(r)) for r in by_name[nm]}
    if len(sigs) == 1:
        same_board += 1
    else:
        diff_board.append(nm)
print("  ... same board, different bytes :", same_board)
print("  ... genuinely different boards  :", len(diff_board), diff_board[:8])

# ---- 2. round-trip the export ----
exported = {o["name"]: o for o in json.load(open("lv/levels_full.json", encoding="utf-8"))}
print("\nexported levels             :", len(exported))

def rebuild(d, name, track):
    return {
        "w": d["mapSizeW"], "h": d["mapSizeH"], "time": d["timeLimit"],
        "holes": [i for i, m in enumerate(d["mapPos"]) if m[1] == 0],
        "seats": [[s[1], s[2], s[3], s[5], 1 if s[4] in (1, 3) else 0] for s in d["seats"]],
        "queue": [u[2] for u in d["users"]],
    }

bad = []
for nm, o in exported.items():
    d = parse_level(by_name[nm][0])
    r = rebuild(d, nm, o["track"])
    for k in ("w", "h", "time", "holes", "seats", "queue"):
        if r[k] != o[k]:
            bad.append((nm, k)); break
print("round-trip mismatches       :", len(bad), bad[:5])

# ---- 3. what the export leaves behind ----
d = parse_level(by_name["Level_00001"][0])
print("\nfields in the decoded struct:", sorted(d.keys()))
print("fields kept in the export   :", sorted(k for k in exported["Level_00001"] if k != "name"))
dropped = []
for nm in list(exported)[:400]:
    d = parse_level(by_name[nm][0])
    if any(g != -1 for g in d["gateRow"]): dropped.append((nm, "gateRow", d["gateRow"]))
    if d["difficultLevel"]: dropped.append((nm, "difficultLevel", d["difficultLevel"]))
print("dropped-but-nonzero samples :", dropped[:6], "..." if len(dropped) > 6 else "")
print("  total in first 400        :", len(dropped))

# ---- 4. seat colour: exported straight through? ----
cols = collections.Counter()
for nm, o in exported.items():
    for s in o["seats"]: cols[s[3]] += 1
print("\nseat colour ids in export   :", sorted(cols))
qcols = collections.Counter()
for nm, o in exported.items():
    for c in o["queue"]: qcols[c] += 1
print("passenger colour ids        :", sorted(qcols))
