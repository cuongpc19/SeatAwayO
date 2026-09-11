# -*- coding: utf-8 -*-
"""Boards for the 3D remake, in their ORIGINAL orientation.

⚠ Not transposed. The honey prototype turns 6x10 portrait into 10x6 landscape
because it is a different game wearing the same data; this one is the original
game rebuilt, so the board has to be the board - same shape, same door on the
right wall, same everything a player of the shipped game would recognise.
"""
import json, io, sys

B = json.load(io.open("src/lv/boards_163.json", encoding="utf-8"))
want = [int(a) for a in sys.argv[1:]] or [3, 10, 12, 19, 30]
out = {}
for n in want:
    b = B[n - 1]
    out[str(n)] = {
        "id": b["id"], "w": b["w"], "h": b["h"], "time": b["time"],
        "diff": b.get("diff", 0), "queue": list(b["queue"]),
        "door": [b["w"] - 1, b.get("door", 0)],     # the door every board has, right wall
        "seats": [list(s) for s in b["seats"]],
        "holes": list(b.get("holes", [])),
    }
    cap = sum(s[2] for s in b["seats"])
    print("level %-4d %dx%d  seats %-3d cap %-3d queue %-3d door %s"
          % (n, b["w"], b["h"], len(b["seats"]), cap, len(b["queue"]), out[str(n)]["door"]))
io.open("proto/boards_raw.json", "w", encoding="utf-8").write(json.dumps(out, separators=(",", ":")))
print("wrote proto/boards_raw.json")
