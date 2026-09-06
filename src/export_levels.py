"""Export the decoded levels as playable boards, and sanity-check the layout
   interpretation (a 2-cell seat extending along +x must never overlap another)."""
import pickle, json, re, collections
from decode_levels import parse_level

raws = pickle.load(open("lv/raws.pkl", "rb"))
seen, levels = set(), {}
for nm, raw in raws:
    if nm in levels: continue
    levels[nm] = parse_level(raw)

def track(name):
    if re.fullmatch(r"Level_\d{5}", name): return "campaign"
    if re.fullmatch(r"Level_\d{5}_\d{2}", name): return "variant"
    if re.fullmatch(r"Level_\d{4}", name): return "challenge"
    return "other"

overlap = axis_bad = 0
out = []
for nm, d in sorted(levels.items()):
    W, H = d["mapSizeW"], d["mapSizeH"]
    grid = {}
    ok = True
    for s in d["seats"]:
        _, px, py, size, direct, colour = s
        vert = direct in (1, 3)              # SeatDirect: 0/2 run along +x, 1/3 along +y
        for k in range(size):
            c, r = (px, py + k) if vert else (px + k, py)
            if not (0 <= c < W and 0 <= r < H): ok = False; break
            if (c, r) in grid: ok = False; break
            grid[(c, r)] = colour
        if not ok: break
    if not ok:
        overlap += 1
        continue
    holes = [i for i, m in enumerate(d["mapPos"]) if m[1] == 0]
    out.append({
        "name": nm, "track": track(nm), "w": W, "h": H,
        "time": d["timeLimit"],
        "holes": holes,
        "seats": [[s[1], s[2], s[3], s[5], 1 if s[4] in (1, 3) else 0] for s in d["seats"]],  # x, y, len, colour, vertical
        "queue": [u[2] for u in d["users"]],                       # colour per passenger
        "big": [i for i, u in enumerate(d["users"]) if u[1] > 1],
        "hidden": [i for i, u in enumerate(d["users"]) if u[3] == 1],
    })

print("levels decoded      :", len(levels))
print("layout inconsistent :", overlap)
print("exported            :", len(out))
print("by track            :", collections.Counter(o["track"] for o in out))

json.dump(out, open("lv/levels_full.json", "w"), separators=(",", ":"))
import os
print("lv/levels_full.json  %.0f KB" % (os.path.getsize("lv/levels_full.json") / 1024))

camp = [o for o in out if o["track"] == "campaign"]
camp.sort(key=lambda o: int(re.findall(r"\d+", o["name"])[0]))
json.dump(camp, open("lv/levels_campaign.json", "w"), separators=(",", ":"))
print("lv/levels_campaign.json  %.0f KB  (%d levels)"
      % (os.path.getsize("lv/levels_campaign.json") / 1024, len(camp)))

# what the first level looks like - should match the recording: 2 seats, 2 riders
l1 = next(o for o in camp if o["name"] == "Level_00001")
print("\nLevel_00001:", l1["w"], "x", l1["h"], "time", l1["time"],
      "seats", l1["seats"], "queue", l1["queue"])
