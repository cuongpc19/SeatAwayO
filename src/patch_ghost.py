p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

reps = [
# ---- continuous ground-plane position under the cursor ----
('function pickCell(clientX, clientY) {\n  const [px, py] = toCanvas(clientX, clientY);',
 '''/** Where the cursor is on the floor, in world units - not snapped to a tile. */
function pickWorld(clientX, clientY) {
  const [px, py] = toCanvas(clientX, clientY);
  const o = P(0, 0, 0);
  const a = BX[0] * LAY.s, b = BZ[0] * LAY.s, c2 = -BX[1] * LAY.s, d = -BZ[1] * LAY.s;
  const det = a * d - b * c2;
  if (!det) return null;
  const dx = px - o[0], dy = py - o[1];
  return [(dx * d - b * dy) / det, (a * dy - dx * c2) / det];
}

function pickCell(clientX, clientY) {
  const [px, py] = toCanvas(clientX, clientY);'''),

# ---- remember where on the seat it was grabbed, so it does not jump ----
('    down = { b, x: ev.clientX, y: ev.clientY, moved: false, wasSel: S.sel === b };\n'
 '    selectSeat(b);                  // targets light up the moment you press\n'
 '    S.drag = { b, hover: null };',
 '    const w = pickWorld(ev.clientX, ev.clientY);\n'
 '    down = { b, x: ev.clientX, y: ev.clientY, moved: false, wasSel: S.sel === b,\n'
 '             grab: w ? [w[0] - cellW(b.c), w[1] - cellZ(b.r)] : [0, 0] };\n'
 '    selectSeat(b);\n'
 '    S.drag = { b, hover: null, ghost: null };'),

# ---- the seat rides along with the cursor ----
('''cv.addEventListener("pointermove", ev => {
  if (!down) return;
  if (!down.moved && Math.hypot(ev.clientX - down.x, ev.clientY - down.y) > 4) down.moved = true;
  const cell = pickCell(ev.clientX, ev.clientY);
  const ok = cell && S.dragTargets.some(([c, r]) => c === cell[0] && r === cell[1]);
  S.drag.hover = ok ? cell : null;      // remembered for the drop, never drawn
});''',
 '''cv.addEventListener("pointermove", ev => {
  if (!down) return;
  if (!down.moved && Math.hypot(ev.clientX - down.x, ev.clientY - down.y) > 4) down.moved = true;
  const cell = pickCell(ev.clientX, ev.clientY);
  const ok = cell && S.dragTargets.some(([c, r]) => c === cell[0] && r === cell[1]);
  S.drag.hover = ok ? cell : null;      // remembered for the drop, never drawn
  if (down.moved) {
    const w = pickWorld(ev.clientX, ev.clientY);
    // offset from where it was grabbed, so the seat does not snap to the pointer
    S.drag.ghost = w ? [w[0] - down.grab[0] - cellW(down.b.c),
                        w[1] - down.grab[1] - cellZ(down.b.r)] : null;
    draw();
  }
});'''),

('  const hover = S.drag && S.drag.hover;\n  S.drag = null;',
 '  const hover = S.drag && S.drag.hover;\n  S.drag = null; S.dragGhost = null;'),

# ---- draw it: home copy hidden, a slightly see-through copy under the cursor ----
('''  for (const b of g.seats) {
    const nm = SPRITE[colName(b.colour)] || "grey";
    const drag = g.sel === b;
    for (const [c, r] of cellsOf(b)) {
      const wx = cellW(c), wz = cellZ(r);
      push(wx, wz, () => { shadow(wx, wz, .5); blit("bench_" + nm, wx, 0, wz, drag ? .82 : 1, .78); });
    }''',
 '''  const held = g.drag && g.drag.ghost ? g.drag.b : null;
  const gdx = held ? g.drag.ghost[0] : 0, gdz = held ? g.drag.ghost[1] : 0;

  for (const b of g.seats) {
    const nm = SPRITE[colName(b.colour)] || "grey";
    const drag = g.sel === b;
    if (b === held) continue;               // drawn last, riding the cursor
    for (const [c, r] of cellsOf(b)) {
      const wx = cellW(c), wz = cellZ(r);
      push(wx, wz, () => { shadow(wx, wz, .5); blit("bench_" + nm, wx, 0, wz, drag ? .82 : 1, .78); });
    }'''),

('''    b.occ.forEach((ci, i) => {
      const cell = cellsOf(b)[i]; if (!cell) return;
      const [c, r] = cell;''',
 '''    if (b === held) continue;
    b.occ.forEach((ci, i) => {
      const cell = cellsOf(b)[i]; if (!cell) return;
      const [c, r] = cell;'''),

# the held seat, on top of everything, a touch translucent
('  items.sort((p, q) => p.z - q.z);\n  for (const it of items) it.fn();',
 '''  items.sort((p, q) => p.z - q.z);
  for (const it of items) it.fn();

  if (held) {
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
  }'''),
]

for a, b in reps:
    if a not in s:
        raise SystemExit("MISS:\n" + a[:150])
    s = s.replace(a, b)

open(p, "w", encoding="utf-8").write(s)
print("drag ghost added")
