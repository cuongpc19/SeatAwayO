p = "game_tpl.html"
s = open(p, encoding="utf-8").read()

OLD = """function seatPos(b, i) {
  const cell = Math.floor(i / 2), sub = i % 2;
  return [LAY.x0 + (b.c + cell) * SX + (sub ? .30 : -.30),
          LAY.z0 + b.r * SZ - .30];
}"""
NEW = """let SEAT_DX = .30, SEAT_DZ = -.30, SEAT_SC = .82;
function seatPos(b, i) {
  const cell = Math.floor(i / 2), sub = i % 2;
  return [LAY.x0 + (b.c + cell) * SX + (sub ? SEAT_DX : -SEAT_DX),
          LAY.z0 + b.r * SZ + SEAT_DZ];
}"""
if OLD not in s: raise SystemExit("seatPos not found")
s = s.replace(OLD, NEW)
s = s.replace('push(gx, 0, gz, () => blit((b.clearing ? "cheer_" : "sit_") + who, gx, 0.06, gz, 1, .82), 0.3);',
              'push(gx, 0, gz, () => blit((b.clearing ? "cheer_" : "sit_") + who, gx, 0.06, gz, 1, SEAT_SC), 0.3);')
open(p, "w", encoding="utf-8").write(s)
print("patched")
