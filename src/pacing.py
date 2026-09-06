"""Turn the decoded campaign into a compact pacing table a generator can follow.

Every 20 levels we take the median of the design dials. The prototype interpolates
between these anchors and rolls its own boards - the curve is reused, the layouts
are not.
"""
import csv, json, collections

rows = list(csv.DictReader(open("lv/campaign.csv", encoding="utf-8")))
rows.sort(key=lambda r: int(r["num"]))
def I(r, k): return int(r[k])

def med(a):
    s = sorted(a); m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2

STEP = 20
anchors = []
for lo in range(0, 600, STEP):
    blk = [r for r in rows if lo < I(r, "num") <= lo + STEP]
    if not blk: continue
    grids = collections.Counter((I(r, "W"), I(r, "H")) for r in blk)
    slots = [I(r, "slots") for r in blk]
    anchors.append({
        "level": lo + STEP // 2,
        "grid": list(grids.most_common(1)[0][0]),
        "colours": round(med([I(r, "colours") for r in blk])),
        "slots": round(med(slots)),
        "greyPct": round(sum(I(r, "greySlots") for r in blk) / max(sum(slots), 1), 3),
        "widePct": round(sum(I(r, "wideBenches") for r in blk) / max(len(blk), 1) / 12, 3),
        "time": round(med([I(r, "timeLimit") for r in blk])),
    })

# how often each rarer grid shows up, and when each mechanic unlocks
grid_mix = collections.Counter("%dx%d" % (I(r, "W"), I(r, "H")) for r in rows)
unlocks = {}
for key, test in {
    "grey":   lambda r: I(r, "greySlots") > 0,
    "wide":   lambda r: I(r, "maxBenchSize") >= 2,
    "hole":   lambda r: I(r, "holes") > 0,
    "big":    lambda r: I(r, "bigGuests") > 0,
    "hidden": lambda r: I(r, "hiddenGuests") > 0,
    "rot":    lambda r: I(r, "rotatedBenches") > 0,
}.items():
    hit = [I(r, "num") for r in rows if test(r)]
    unlocks[key] = min(hit) if hit else None

out = {"anchors": anchors, "unlocks": unlocks,
       "gridMix": dict(grid_mix), "levels": len(rows)}
json.dump(out, open("lv/pacing.json", "w"), separators=(",", ":"))
print("anchors:", len(anchors))
for a in anchors[:6] + anchors[-3:]:
    print("  L%-4d grid %-6s col %d  slots %2d  grey %.0f%%  wide %.0f%%  %ds"
          % (a["level"], "%dx%d" % tuple(a["grid"]), a["colours"], a["slots"],
             a["greyPct"] * 100, a["widePct"] * 100, a["time"]))
print("unlocks:", unlocks)
print("json bytes", len(json.dumps(out)))
