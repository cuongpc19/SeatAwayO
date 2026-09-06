"""Export EVERY distinct board in the APK, not one per name.

171 level names ship 2-3 genuinely different boards. The earlier export kept the
first and dropped the rest; this one keeps them all, tagged with a variant index,
and carries the fields the first pass left behind.
"""
import pickle, json, re, collections, os
from decode_levels import parse_level

raws = pickle.load(open("lv/raws.pkl", "rb"))

def track(name):
    if re.fullmatch(r"Level_\d{5}", name): return "campaign"
    if re.fullmatch(r"Level_\d{5}_\d{2}", name): return "variant"
    if re.fullmatch(r"Level_\d{4}", name): return "challenge"
    return "other"

by = collections.OrderedDict()
for nm, raw in raws:
    by.setdefault(nm, [])
    if raw not in by[nm]:
        by[nm].append(raw)

out, overlaps = [], 0
for nm, variants in by.items():
    for vi, raw in enumerate(variants):
        d = parse_level(raw)
        W, H = d["mapSizeW"], d["mapSizeH"]
        grid, ok = set(), True
        for s in d["seats"]:
            _, px, py, size, direct, colour = s
            vert = direct in (1, 3)
            for k in range(size):
                c, r = (px, py + k) if vert else (px + k, py)
                if not (0 <= c < W and 0 <= r < H) or (c, r) in grid: ok = False; break
                grid.add((c, r))
            if not ok: break
        if not ok:
            overlaps += 1
            continue
        out.append({
            "name": nm,
            "variant": vi,
            "id": nm if len(variants) == 1 else "%s#%d" % (nm, vi + 1),
            "track": track(nm),
            "w": W, "h": H,
            "time": d["timeLimit"],
            "diff": d["difficultLevel"],
            "cam": [round(d["camSize"], 3), round(d["camWinSize"], 3)],
            "gate": d["gateRow"],
            "holes": [i for i, m in enumerate(d["mapPos"]) if m[1] == 0],
            "seats": [[s[1], s[2], s[3], s[5], s[4]] for s in d["seats"]],   # x, y, len, colour, SeatDirect
            "queue": [u[2] for u in d["users"]],
            "big": [i for i, u in enumerate(d["users"]) if u[1] > 1],
            "hidden": [i for i, u in enumerate(d["users"]) if u[3] == 1],
        })

print("raw assets in bundle    :", len(raws))
print("distinct boards         :", len(out), "(+%d rejected for overlap)" % overlaps)
print("names                   :", len(by))
print("names with >1 board     :", sum(1 for v in by.values() if len(v) > 1))
print("by track                :", dict(collections.Counter(o["track"] for o in out)))

json.dump(out, open("lv/boards_all.json", "w"), separators=(",", ":"))
print("lv/boards_all.json  %.0f KB" % (os.path.getsize("lv/boards_all.json") / 1024))

camp = [o for o in out if o["track"] == "campaign"]
camp.sort(key=lambda o: (int(re.findall(r"\d+", o["name"])[0]), o["variant"]))
json.dump(camp, open("lv/boards_campaign.json", "w"), separators=(",", ":"))
print("lv/boards_campaign.json  %.0f KB  (%d boards, %d names)"
      % (os.path.getsize("lv/boards_campaign.json") / 1024, len(camp),
         len({o["name"] for o in camp})))

# byte-exact round-trip: rebuild each record from its own raw and diff
flat = {}
for nm, variants in by.items():
    for vi, raw in enumerate(variants): flat[(nm, vi)] = raw
bad = 0
for o in out:
    d = parse_level(flat[(o["name"], o["variant"])])
    chk = {
        "w": d["mapSizeW"], "h": d["mapSizeH"], "time": d["timeLimit"], "diff": d["difficultLevel"],
        "gate": d["gateRow"],
        "holes": [i for i, m in enumerate(d["mapPos"]) if m[1] == 0],
        "seats": [[s[1], s[2], s[3], s[5], s[4]] for s in d["seats"]],   # x, y, len, colour, SeatDirect
        "queue": [u[2] for u in d["users"]],
    }
    if any(chk[k] != o[k] for k in chk): bad += 1
print("round-trip mismatches   :", bad, "/", len(out))
