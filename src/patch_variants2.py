p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

# ---------- seats carry their direction and one slot per place ----------
old = s[s.index("  const seats = raw.seats.map((s, i) => ({"):s.index("  const g = { W, H, hole, occ, seats,")]
new = '''  const seats = raw.seats.map((s, i) => ({
    id: i, c: s[0], r: s[1], len: s[2], colour: s[3],
    dir: s[5] != null ? s[5] : (s[4] ? 1 : 0),      // SeatDirect 0..3
    occ: new Array(s[2]).fill(null),                // one place per cell
    pending: 0, locked: false,
  }));
'''
s = s[:s.index("  const seats = raw.seats.map((s, i) => ({")] + new + s[s.index("  const g = { W, H, hole, occ, seats,"):]

# ---------- boarding takes a specific place ----------
reps = [
('    const ci = S.queue[0];\n'
 '    const seat = pickSeat(S, ci);\n'
 '    if (!seat) { S.boarding = false; hud(); draw(); return; }\n'
 '    S.queue.shift();\n'
 '    const slot = seat.occ.length + seat.pending;\n'
 '    seat.pending++;\n'
 '    const cell = cellsOf(seat)[slot];\n'
 '    seat.locked = true;             // no dragging a seat out from under a walker\n'
 '    if (instant) {\n'
 '      seat.pending--; seat.locked = false; seat.occ.push(ci); S.seated++;\n'
 '      step(); return;\n'
 '    }',
 '    const ci = S.queue[0];\n'
 '    const spot = pickSeat(S, ci);\n'
 '    if (!spot) { S.boarding = false; hud(); draw(); return; }\n'
 '    const seat = spot.seat, slot = spot.k;\n'
 '    S.queue.shift();\n'
 '    seat.pending++;\n'
 '    (seat.claim || (seat.claim = new Set())).add(slot);   // nobody else takes this place\n'
 '    const cell = cellsOf(seat)[slot];\n'
 '    seat.locked = true;             // no dragging a seat out from under a walker\n'
 '    const sitDown = () => {\n'
 '      seat.pending--; seat.locked = false;\n'
 '      if (seat.claim) seat.claim.delete(slot);\n'
 '      seat.occ[slot] = ci; S.seated++;\n'
 '    };\n'
 '    if (instant) { sitDown(); step(); return; }'),

('    const path = walkPath(S, seat) || [cell];',
 '    const path = walkPath(S, seat, slot, spot.entry) || [cell];'),

('          S.anim.splice(S.anim.indexOf(a), 1);\n'
 '          S.walkCells = null;\n'
 '          seat.pending--; seat.locked = false; seat.occ.push(ci); S.seated++;',
 '          S.anim.splice(S.anim.indexOf(a), 1);\n'
 '          S.walkCells = null;\n'
 '          sitDown();'),

# ---------- one sprite per seat, riders facing the way the seat does ----------
('''  for (const b of g.seats) {
    const nm = SPRITE[colName(b.colour)] || "grey";
      if (b === held) continue;               // drawn last, riding the cursor
    for (const [c, r] of cellsOf(b)) {
      const wx = cellW(c), wz = cellZ(r);
      push(wx, wz, () => { shadow(wx, wz, .5); blit("bench_" + nm, wx, 0, wz, 1, .78); });
    }''',
 '''  for (const b of g.seats) {
    if (b === held) continue;                 // drawn last, riding the cursor
    const [sx, sz] = seatCentre(b);
    push(sx, sz, () => { shadow(sx, sz, .45 * b.len); blit(seatFrame(b), sx, 0, sz, 1); });'''),

('''    if (b === held) continue;
    b.occ.forEach((ci, i) => {
      const cell = cellsOf(b)[i]; if (!cell) return;
      const [c, r] = cell;
      push(cellW(c), cellZ(r), () => blit("sit_" + (SPRITE[colName(ci)] || "grey"),
                                          cellW(c), .05, cellZ(r) - .04, 1, .74), .3);
    });
  }''',
 '''    b.occ.forEach((ci, i) => {
      if (ci == null) return;
      const [c, r] = cellsOf(b)[i];
      push(cellW(c), cellZ(r), () => blit(riderFrame(b, ci), cellW(c), .05, cellZ(r) - .04), .3);
    });
  }'''),

# the ring guides key off the returned spot
('    if (GUIDES && b === g.nextSeat) {', '    if (GUIDES && g.nextSeat && b === g.nextSeat.seat) {'),

# the held seat, drawn last
('''  if (held) {
    const nm = SPRITE[colName(held.colour)] || "grey";
    const A = .72;                          // lighter than a seat that is put down
    for (const [c, r] of cellsOf(held)) {
      const wx = cellW(c) + gdx, wz = cellZ(r) + gdz;
      shadow(wx, wz, .5);
      blit("bench_" + nm, wx, 0, wz, A, .78);
    }
    held.occ.forEach((ci, i) => {
      const cell = cellsOf(held)[i]; if (!cell) return;
      blit("sit_" + (SPRITE[colName(ci)] || "grey"),
           cellW(cell[0]) + gdx, .05, cellZ(cell[1]) + gdz - .04, A, .74);
    });
  }''',
 '''  if (held) {
    const A = .72;                          // lighter than a seat that is put down
    const [sx, sz] = seatCentre(held);
    shadow(sx + gdx, sz + gdz, .45 * held.len);
    blit(seatFrame(held), sx + gdx, 0, sz + gdz, A);
    held.occ.forEach((ci, i) => {
      if (ci == null) return;
      const [c, r] = cellsOf(held)[i];
      blit(riderFrame(held, ci), cellW(c) + gdx, .05, cellZ(r) + gdz - .04, A);
    });
  }'''),

# queue and walkers use the new frame names
('    push(laneX, wz, () => { shadow(laneX, wz, .3); blit("idle_" + nm, laneX, 0, wz, i ? Math.max(.4, 1 - i * .11) : 1, .74); });',
 '    push(laneX, wz, () => { shadow(laneX, wz, .3); blit("idle_" + nm, laneX, 0, wz, i ? Math.max(.4, 1 - i * .11) : 1); });'),
('  if (!f) return blit("idle_" + colour, wx, wy, wz, 1, .74);',
 '  if (!f) return blit("idle_" + colour, wx, wy, wz, 1);'),
]

for a, b in reps:
    if a not in s:
        raise SystemExit("MISS:\n" + a[:150])
    s = s.replace(a, b)

# ---------- helpers the drawing now needs ----------
s = s.replace("/** Frames carry their own size and origin:",
"""/** Where a seat's sprite is centred: long seats span several cells. */
function seatCentre(b) {
  const n = (b.len - 1) / 2;
  return b.dir & 1 ? [cellW(b.c), cellZ(b.r) + n * SZ]
                   : [cellW(b.c) + n * SX, cellZ(b.r)];
}
const seatFrame = b => "s" + b.len + "_" + b.dir + "_" + (SPRITE[colName(b.colour)] || "grey");
const riderFrame = (b, ci) => "r" + b.dir + "_" + (SPRITE[colName(ci)] || "grey");

/** Frames carry their own size and origin:""")

open(p, "w", encoding="utf-8").write(s)
print("draw + boarding updated for seat variants")
