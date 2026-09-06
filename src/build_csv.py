"""Decode every level, dedupe, and emit CSVs."""
import pickle, re, csv, collections, json
from decode_levels import parse_level, metrics

raws = pickle.load(open("lv/raws.pkl", "rb"))
print("assets:", len(raws))

rows, seen = [], {}
for nm, raw in raws:
    d = parse_level(raw)
    m = metrics(d)
    key = (nm, raw)
    if key in seen: continue
    seen[key] = 1
    m["name"] = nm
    m["raw_len"] = len(raw)
    rows.append((m, d))

print("unique (name,bytes):", len(rows))

# collapse duplicates that are byte-identical under the same name
uniq = {}
for m, d in rows:
    uniq.setdefault(m["name"], (m, d))
print("unique names:", len(uniq))

def track(name):
    if re.fullmatch(r"Level_\d{5}", name):    return "campaign"
    if re.fullmatch(r"Level_\d{5}_\d{2}", name): return "variant"
    if re.fullmatch(r"Level_\d{4}", name):    return "challenge"
    return "other"

def order(name):
    mm = re.findall(r"\d+", name)
    return tuple(int(x) for x in mm)

allrows = []
for nm, (m, d) in uniq.items():
    r = dict(m); r["track"] = track(nm)
    n = re.findall(r"\d+", nm)
    r["num"] = int(n[0]); r["variant"] = int(n[1]) if len(n) > 1 else 0
    allrows.append(r)
allrows.sort(key=lambda r: (r["track"], r["num"], r["variant"]))

cols = ["name", "track", "num", "variant", "W", "H", "cells", "playable", "holes",
        "benches", "slots", "guests", "colours", "seatColours", "greySlots",
        "guestsPerColour", "density", "wideBenches", "maxBenchSize", "rotatedBenches",
        "bigGuests", "hiddenGuests", "hasGate", "timeLimit", "difficultLevel",
        "camSize", "camWinSize", "raw_len"]
with open("lv/levels.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in allrows: w.writerow(r)
print("wrote lv/levels.csv  rows=%d" % len(allrows))

camp = [r for r in allrows if r["track"] == "campaign"]
camp.sort(key=lambda r: r["num"])
with open("lv/campaign.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in camp: w.writerow(r)
print("wrote lv/campaign.csv rows=%d" % len(camp))

# ---- first appearance of each mechanic in the campaign ----
feat = {
    "grid 3x6":        lambda r: (r["W"], r["H"]) == (3, 6),
    "grid 4x6":        lambda r: (r["W"], r["H"]) == (4, 6),
    "grid 4x7":        lambda r: (r["W"], r["H"]) == (4, 7),
    "grid 4x8":        lambda r: (r["W"], r["H"]) == (4, 8),
    "grid 5x8":        lambda r: (r["W"], r["H"]) == (5, 8),
    "grid 6x10":       lambda r: (r["W"], r["H"]) == (6, 10),
    "grid 7x11":       lambda r: (r["W"], r["H"]) == (7, 11),
    "2 colours":       lambda r: r["colours"] >= 2,
    "3 colours":       lambda r: r["colours"] >= 3,
    "4 colours":       lambda r: r["colours"] >= 4,
    "5 colours":       lambda r: r["colours"] >= 5,
    "6 colours":       lambda r: r["colours"] >= 6,
    "7 colours":       lambda r: r["colours"] >= 7,
    "8 colours":       lambda r: r["colours"] >= 8,
    "grey seat":       lambda r: r["greySlots"] > 0,
    "hole in grid":    lambda r: r["holes"] > 0,
    "2-seat bench":    lambda r: r["maxBenchSize"] >= 2,
    "3-seat bench":    lambda r: r["maxBenchSize"] >= 3,
    "rotated bench":   lambda r: r["rotatedBenches"] > 0,
    "double guest":    lambda r: r["bigGuests"] > 0,
    "hidden guest":    lambda r: r["hiddenGuests"] > 0,
    "gate":            lambda r: r["hasGate"] == 1,
    "timer <= 180s":   lambda r: r["timeLimit"] <= 180,
    "timer <= 120s":   lambda r: r["timeLimit"] <= 120,
    "timer <= 90s":    lambda r: r["timeLimit"] <= 90,
    "timer <= 60s":    lambda r: r["timeLimit"] <= 60,
}
intro = {}
for k, fn in feat.items():
    hits = [r["num"] for r in camp if fn(r)]
    intro[k] = (min(hits), len(hits)) if hits else (None, 0)

with open("lv/mechanic_intro.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["mechanic", "first_campaign_level", "levels_using"])
    for k, (first, cnt) in sorted(intro.items(), key=lambda kv: (kv[1][0] is None, kv[1][0])):
        w.writerow([k, first, cnt])
print("wrote lv/mechanic_intro.csv")
json.dump(intro, open("lv/intro.json", "w"), indent=1)

print()
print("%-16s %6s %7s" % ("mechanic", "first", "#levels"))
for k, (first, cnt) in sorted(intro.items(), key=lambda kv: (kv[1][0] is None, kv[1][0])):
    print("%-16s %6s %7d" % (k, first, cnt))
