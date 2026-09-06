p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

reps = [
# ---- a seat somebody is already walking to is pinned until they sit down ----
('    S.queue.shift();\n'
 '    const slot = seat.occ.length + seat.pending;\n'
 '    seat.pending++;\n'
 '    const cell = cellsOf(seat)[slot];',
 '    S.queue.shift();\n'
 '    const slot = seat.occ.length + seat.pending;\n'
 '    seat.pending++;\n'
 '    const cell = cellsOf(seat)[slot];\n'
 '    seat.locked = true;             // no dragging a seat out from under a walker'),

('    if (instant) {\n'
 '      seat.pending--; seat.occ.push(ci); S.seated++;\n'
 '      step(); return;\n'
 '    }',
 '    if (instant) {\n'
 '      seat.pending--; seat.locked = false; seat.occ.push(ci); S.seated++;\n'
 '      step(); return;\n'
 '    }'),

('          S.anim.splice(S.anim.indexOf(a), 1);\n'
 '          seat.pending--; seat.occ.push(ci); S.seated++;',
 '          S.anim.splice(S.anim.indexOf(a), 1);\n'
 '          S.walkCells = null;\n'
 '          seat.pending--; seat.locked = false; seat.occ.push(ci); S.seated++;'),

# the floor they are crossing is off limits too, or a seat could be slid through them
('    const a = { ci, x: pts[0][0], z: pts[0][1], y: 0, route: path, facing: "d", phase: 0 };\n'
 '    S.anim.push(a);',
 '    const a = { ci, x: pts[0][0], z: pts[0][1], y: 0, route: path, facing: "d", phase: 0 };\n'
 '    S.anim.push(a);\n'
 '    S.walkCells = new Set(path.map(([c, r]) => c + "," + r));'),

# ---- honour both in the rules that decide where a seat may go ----
('function placements(g, b) {\n'
 '  const seen = new Set([b.c + "," + b.r]), out = [], q = [[b.c, b.r]];',
 'function placements(g, b) {\n'
 '  if (b.locked) return [];\n'
 '  const seen = new Set([b.c + "," + b.r]), out = [], q = [[b.c, b.r]];'),

('  while (q.length) {\n'
 '    const [c, r] = q.shift();\n'
 '    for (const [dc, dr] of DIRS) {\n'
 '      const nc = c + dc, nr = r + dr, k = nc + "," + nr;\n'
 '      if (seen.has(k)) continue;',
 '  while (q.length) {\n'
 '    const [c, r] = q.shift();\n'
 '    for (const [dc, dr] of DIRS) {\n'
 '      const nc = c + dc, nr = r + dr, k = nc + "," + nr;\n'
 '      if (seen.has(k)) continue;\n'
 '      if (g.walkCells && g.walkCells.has(k)) continue;   // somebody is crossing it'),

# ---- and refuse to pick it up in the first place ----
('cv.addEventListener("pointerdown", ev => {\n'
 '  if (!S || S.phase !== "play") return;\n'
 '  const b = pickSeatAt(ev.clientX, ev.clientY);\n'
 '  if (b) {',
 'cv.addEventListener("pointerdown", ev => {\n'
 '  if (!S || S.phase !== "play") return;\n'
 '  const b = pickSeatAt(ev.clientX, ev.clientY);\n'
 '  if (b && b.locked) { bump(); clearSel(); return; }   // a passenger is on their way\n'
 '  if (b) {'),

# ---- reset the flags on load ----
('  g.seated = 0; g.phase = "play"; g.moves = 0;',
 '  g.seated = 0; g.phase = "play"; g.moves = 0; g.walkCells = null;'),
('                                           occ: [], pending: 0 }));',
 '                                           occ: [], pending: 0, locked: false }));'),

# ---- say so ----
('      <li>A seat with somebody already on it still slides, passenger and all.</li>',
 '      <li>A seat with somebody already on it still slides, passenger and all &mdash; but a seat someone is\n'
 '        currently walking to is pinned until they sit down.</li>'),
]

for a, b in reps:
    if a not in s:
        raise SystemExit("MISS:\n" + a[:150])
    s = s.replace(a, b)

open(p, "w", encoding="utf-8").write(s)
print("target seat locked while a passenger is en route")
