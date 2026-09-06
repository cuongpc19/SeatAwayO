"""Re-read the decoded levels under the correct mechanic: 1 seat per bench cell,
benches block the grid and get moved to open a path from the gate."""
import pickle, collections, statistics as st
from decode_levels import parse_level

raws = pickle.load(open("lv/raws.pkl", "rb"))
seen, rows = set(), []
for nm, raw in raws:
    if (nm, raw) in seen: continue
    seen.add((nm, raw))
    d = parse_level(raw)
    if nm in {r[0] for r in rows}: continue
    rows.append((nm, d))

free_frac, gates, dirs, sizes, holes_by = [], collections.Counter(), collections.Counter(), collections.Counter(), 0
exact = 0
for nm, d in rows:
    cells = d["mapSizeW"] * d["mapSizeH"]
    holes = sum(1 for m in d["mapPos"] if m[1] == 0)
    playable = cells - holes
    slots = sum(s[3] for s in d["seats"])
    if slots == len(d["users"]): exact += 1
    free_frac.append((playable - slots) / playable)
    gates[tuple(d["gateRow"])] += 1
    for s in d["seats"]:
        dirs[s[4]] += 1; sizes[s[3]] += 1
    if holes: holes_by += 1

print("levels:", len(rows))
print("sum(sizeW) == guest count : %d / %d" % (exact, len(rows)))
print()
ff = sorted(free_frac)
print("free cells as a share of playable area")
print("  min %.2f   p10 %.2f   median %.2f   p90 %.2f   max %.2f" % (
    ff[0], ff[len(ff)//10], st.median(ff), ff[9*len(ff)//10], ff[-1]))
free_cells = []
for nm, d in rows:
    cells = d["mapSizeW"] * d["mapSizeH"]
    holes = sum(1 for m in d["mapPos"] if m[1] == 0)
    free_cells.append(cells - holes - sum(s[3] for s in d["seats"]))
fc = sorted(free_cells)
print("free cells, absolute: min %d  p10 %d  median %d  p90 %d  max %d" % (
    fc[0], fc[len(fc)//10], st.median(fc), fc[9*len(fc)//10], fc[-1]))
print()
print("bench length (sizeW):", sizes.most_common())
print("bench direct       :", dirs.most_common())
print("gateRow patterns   :", gates.most_common(6))
print("levels with holes  :", holes_by)
print()
# how many benches per colour group - i.e. how many seats share one colour
g = []
for nm, d in rows:
    per = collections.Counter()
    for s in d["seats"]:
        if s[5]: per[s[5]] += s[3]
    if per: g.append(st.mean(per.values()))
print("seats per colour, mean of per-level means: %.2f" % st.mean(g))
