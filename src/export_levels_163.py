"""Normalise the 1.63.1 level dump into an explicit, self-contained board list.

The shipped JSON omits every default-valued field, so a bare `{}` seat means
slot 0 with no modifiers.  This fills the defaults in, resolves each seat to
its panel coordinates, and writes one record per level.
"""
import json, os, collections

RAW = "lv/levels_163_raw.json"
PANELS = "lv/panels_163.json"
OUT = "lv/levels_163.json"

# seatData flags that ship as `true` only when set
FLAGS = ("staticSeat", "doubleSeat", "tripleSeat", "fourSeater", "isLocked",
         "vanish", "split", "transparentSeat", "firstClass")

levels = json.load(open(RAW))
panels = json.load(open(PANELS))

out = []
for lid in sorted(levels, key=int):
    d = levels[lid]
    pn = d.get("seatPanelNumber", 0)
    areas = panels[str(pn)]
    seats = []
    for s in d.get("seatData", []):
        slot = s.get("seatNumber", 0)
        pos = areas[str(slot)]
        seats.append({
            "slot": slot,
            "colour": s.get("colorNumber", 0),
            "turn": s.get("turnNumber", 0),
            "ice": s.get("iceCount", 0),
            "x": pos["x"], "y": pos["y"], "z": pos["z"], "rotZ": pos["rotZ"],
            **{f: bool(s.get(f, False)) for f in FLAGS},
        })
    rec = {
        "id": d["ID"],
        "panel": pn,
        "moveCount": d.get("moveCount", 0),
        "secondDoor": bool(d.get("secondDoor", False)),
        "queue": [c.get("customerSiralistesi", 0) for c in d.get("customerSiralistesi", [])],
        "queueIds": [c.get("id", 0) for c in d.get("customerSiralistesi", [])],
        "queue2": [c.get("customerSiralistesi", 0) for c in d.get("customerSiralistesi2", [])],
        "seats": seats,
        "obstacles": [{"slot": o.get("seatAreaNumber", 0), "kind": o.get("obstackleNumber", 0)}
                      for o in d.get("obstacleList", [])],
        "holeObstacles": d.get("holeObstacles", []),
        "colouredGrid": [{"slot": g.get("seatNumber", 0), "colour": g.get("colorIndex", 0)}
                         for g in d.get("coloredGridDatas", [])],
        "seatArms": {
            "left": d.get("seatLeftArmList", []),
            "right": d.get("seatRightArmList", []),
            "alt": d.get("seatAltList", []),
        },
    }
    out.append(rec)

json.dump(out, open(OUT, "w"), separators=(",", ":"))
print("levels exported :", len(out))
print("id range        :", out[0]["id"], "-", out[-1]["id"])
print("seats total     :", sum(len(r["seats"]) for r in out))
print("riders total    :", sum(len(r["queue"]) for r in out))
print("panels used     :", sorted(collections.Counter(r['panel'] for r in out)))
print("colours seen    :", sorted({s['colour'] for r in out for s in r['seats']}))
print("wrote", OUT, "%.0f KB" % (os.path.getsize(OUT) / 1024))
