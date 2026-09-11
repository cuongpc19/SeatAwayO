# -*- coding: utf-8 -*-
"""The whole campaign, trimmed to what the 3D build actually reads.

⚠ Original orientation, not transposed. The 3D build turns the ROOM when it
wants landscape, so the data never needs mirroring - see the honey prototype for
what transposing costs.

⚠ `time` is taken as it stands. src/convert_163.py has already applied the
hybrid ladder (levels 1-14 at 240s, the APK's own clock from 15 on), so a second
opinion here would be a second source of truth for the one number a level is
scored against.
"""
import json, io, collections, pathlib

SRC = pathlib.Path("src/lv/boards_163.json")
OUT = pathlib.Path("game3d/levels.json")

B = json.load(io.open(SRC, encoding="utf-8"))
out, feat = [], collections.Counter()
for b in B:
    W = b["w"]
    lv = {"w": W, "h": b["h"], "t": b["time"], "d": b.get("diff", 0),
          "dr": b.get("door", 0), "q": b["queue"], "s": b["seats"]}
    if b.get("holes"):
        lv["hl"] = b["holes"]; feat["holes"] += 1
    if b.get("fixtures"):
        # [c, r, kind] -> the cell is blocked and something stands on it
        lv["fx"] = [[f[0], f[1], (f[2] if len(f) > 2 else 0)] for f in b["fixtures"]]
        feat["fixtures"] += 1
    if b.get("secondDoor") and b.get("queue2"):
        lv["q2"] = b["queue2"]
        lv["dr2"] = b.get("door2") if b.get("door2") is not None else max(0, b["h"] - 2)
        feat["second door"] += 1
    locked = sorted(int(k) for k, v in (b.get("mods") or {}).items() if (v or {}).get("isLocked"))
    if locked:
        lv["lk"] = locked; feat["locked seats"] += 1
    out.append(lv)

io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, separators=(",", ":")))
print("%d levels -> %s  %.2f MB" % (len(out), OUT, OUT.stat().st_size / 1048576))
for k, v in feat.most_common():
    print("  %-14s on %d boards" % (k, v))
cap_ok = sum(1 for i, b in enumerate(B)
             if sum(s[2] for s in b["seats"]) == len(b["queue"]) + len(b.get("queue2") or []))
print("  capacity == queue on %d of %d" % (cap_ok, len(B)))
