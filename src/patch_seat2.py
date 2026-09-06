p = "game_tpl.html"
s = open(p, encoding="utf-8").read()

OLD = """let SEAT_DX = .30, SEAT_DZ = -.30, SEAT_SC = .82;
function seatPos(b, i) {
  const cell = Math.floor(i / 2), sub = i % 2;
  return [LAY.x0 + (b.c + cell) * SX + (sub ? SEAT_DX : -SEAT_DX),
          LAY.z0 + b.r * SZ + SEAT_DZ];
}"""

NEW = """let SEAT_DX = .33, SEAT_DZ = -.05, SEAT_SC = 1;
// Guests pair up per bench cell. A cell holding one guest seats them centred -
// a lone guest shoved to one side reads as standing beside the bench, not on it.
function seatPos(b, i, occ) {
  const cell = Math.floor(i / 2), sub = i % 2;
  const n = occ == null ? b.cap : occ;
  const inCell = Math.max(0, Math.min(2, n - cell * 2));   // guests landing in this cell
  const dx = inCell <= 1 ? 0 : (sub ? SEAT_DX : -SEAT_DX);
  return [LAY.x0 + (b.c + cell) * SX + dx, LAY.z0 + b.r * SZ + SEAT_DZ];
}"""

if OLD not in s:
    raise SystemExit("seatPos block not found")
s = s.replace(OLD, NEW)

# draw each seated guest against the bench's current occupancy
s = s.replace("      const [gx, gz] = seatPos(b, i);",
              "      const [gx, gz] = seatPos(b, i, b.occ.length);")

# the walker aims at where they will actually end up (occupancy after they land)
s = s.replace("  const [sx, sz] = seatPos(b, slot);",
              "  const [sx, sz] = seatPos(b, slot, slot + 1);")

open(p, "w", encoding="utf-8").write(s)
print("patched")
