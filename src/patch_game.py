p = "game_tpl.html"
s = open(p, encoding="utf-8").read()

PAIRS = [
# ---- benches hold two guests per cell, so filling one is a real commitment ----
('    benches.push({ id: benches.length, c, r, w: wide, colour: null, locked: false, occ: [] });\n'
 '    placed += wide;',
 '    benches.push({ id: benches.length, c, r, w: wide, cap: wide * 2,\n'
 '                   colour: null, locked: false, occ: [], pending: 0 });\n'
 '    placed += wide * 2;'),

('    if (wantGrey) { b.colour = "grey"; greyBudget -= b.w; } else { b.colour = colour; }\n'
 '    for (let k = 0; k < b.w; k++) queue.push(wantGrey ? colour : b.colour);',
 '    if (wantGrey) { b.colour = "grey"; greyBudget -= b.cap; } else { b.colour = colour; }\n'
 '    for (let k = 0; k < b.cap; k++) queue.push(wantGrey ? colour : b.colour);'),

('    const wantGrey = greyBudget >= b.w && rand() < 0.55;',
 '    const wantGrey = greyBudget >= b.cap && rand() < 0.55;'),

# a wide bench needs the neighbouring cell AND two more seats of budget
('    if (rand() < p.widePct && c + 1 < W && !occupied[r * W + c + 1] && placed + 2 <= p.slots) wide = 2;',
 '    if (rand() < p.widePct && c + 1 < W && !occupied[r * W + c + 1] && placed + 4 <= p.slots) wide = 2;'),

# ---- legality: reserve the slot the moment a guest is sent, not when they arrive ----
('function legal(b, colour) {\n'
 '  if (!b || b.gone || b.occ.length >= b.w) return false;',
 'function taken(b) { return b.occ.length + b.pending; }\n'
 'function legal(b, colour) {\n'
 '  if (!b || b.gone || taken(b) >= b.cap) return false;'),

# ---- seating: reserve, then land in the reserved seat ----
('  const startZ = LAY.z0 + (S.H - 1) * SZ + 1.6;\n'
 '  const [tx, , tz] = cellPos(b.c, b.r, b.w);\n'
 '  const slot = b.occ.length;\n'
 '  const a = { colour, x: LAY.laneX, z: startZ, tx: LAY.x0 + (b.c + slot) * SX, tz: tz, t: 0 };',
 '  const startZ = LAY.z0 + (S.H - 1) * SZ + 1.6;\n'
 '  const slot = taken(b);\n'
 '  b.pending++;\n'
 '  const [sx, sz] = seatPos(b, slot);\n'
 '  const a = { colour, x: LAY.laneX, z: startZ, tx: sx, tz: sz, t: 0 };'),

('      S.anim.splice(S.anim.indexOf(a), 1);\n'
 '      b.occ.push(colour);\n'
 '      S.seated++;\n'
 '      if (b.occ.length >= b.w) {',
 '      S.anim.splice(S.anim.indexOf(a), 1);\n'
 '      b.pending--;\n'
 '      b.occ.push(colour);\n'
 '      S.seated++;\n'
 '      if (b.occ.length >= b.cap) {'),

# ---- draw two guests per bench cell ----
('    for (let k = 0; k < b.w; k++) {\n'
 '      const sx = LAY.x0 + (b.c + k) * SX;\n'
 '      push(sx, 0, wz, () => { shadow(sx, wz, .5); blit("bench_" + tint, sx, 0, wz, 1); });\n'
 '      const who = b.occ[k];\n'
 '      if (who) push(sx, 0, wz, () => blit((b.clearing ? "cheer_" : "sit_") + who, sx, 0.06, wz - .05), 0.3);\n'
 '    }',
 '    for (let k = 0; k < b.w; k++) {\n'
 '      const sx = LAY.x0 + (b.c + k) * SX;\n'
 '      push(sx, 0, wz, () => { shadow(sx, wz, .55); blit("bench_" + tint, sx, 0, wz, 1); });\n'
 '    }\n'
 '    for (let i = 0; i < b.cap; i++) {\n'
 '      const who = b.occ[i];\n'
 '      if (!who) continue;\n'
 '      const [gx, gz] = seatPos(b, i);\n'
 '      push(gx, 0, gz, () => blit((b.clearing ? "cheer_" : "sit_") + who, gx, 0.06, gz, 1, .82), 0.3);\n'
 '    }'),

# ---- seat geometry helper ----
('function cellPos(c, r, w) {',
 'function seatPos(b, i) {\n'
 '  const cell = Math.floor(i / 2), sub = i % 2;\n'
 '  return [LAY.x0 + (b.c + cell) * SX + (sub ? .34 : -.34),\n'
 '          LAY.z0 + b.r * SZ - .06];\n'
 '}\n'
 'function cellPos(c, r, w) {'),

# ---- a bit more room between queue guests ----
('    const wz = LAY.z0 + (S.H - 1) * SZ + 1.6 - i * 1.0;',
 '    const wz = LAY.z0 + (S.H - 1) * SZ + 1.6 - i * 1.16;'),

# ---- tighter apron so the board fills the frame ----
('  const gq = [[-pad, -pad], [S.W - 1 + pad + 3.6, -pad], [S.W - 1 + pad + 3.6, S.H - 1 + pad + .6], [-pad, S.H - 1 + pad + .6]]',
 '  const gq = [[-pad, -pad - .4], [S.W - 1 + pad + 2.9, -pad - .4], [S.W - 1 + pad + 2.9, S.H - 1 + pad + .5], [-pad, S.H - 1 + pad + .5]]'),

('  for (const [cx, cz] of [[-pad, -pad], [S.W - 1 + pad, -pad], [-pad, S.H - 1 + pad], [S.W - 1 + pad, S.H - 1 + pad]])\n'
 '    pts.push(view(x0 + cx * SX, 0, z0 + cz * SZ));\n'
 '  const laneX = x0 + (S.W - 1) * SX + 3.1;\n'
 '  pts.push(view(laneX + 1.2, 0, z0 + (S.H - 1) * SZ + 2));\n'
 '  pts.push(view(laneX + 1.2, 2.4, z0 - pad * SZ));',
 '  for (const [cx, cz] of [[-pad, -pad], [S.W - 1 + pad, -pad], [-pad, S.H - 1 + pad], [S.W - 1 + pad, S.H - 1 + pad]])\n'
 '    pts.push(view(x0 + cx * SX, 0, z0 + cz * SZ));\n'
 '  const laneX = x0 + (S.W - 1) * SX + 2.9;\n'
 '  pts.push(view(laneX + .9, 0, z0 + (S.H - 1) * SZ + 1.9));\n'
 '  pts.push(view(laneX + .9, 2.4, z0 - pad * SZ));'),

# blit gains a scale multiplier already; make the signature explicit for seated guests
('function blit(frame, wx, wy, wz, alpha, scaleMul) {',
 'function blit(frame, wx, wy, wz, alpha, scaleMul) {  // scaleMul shrinks seated guests'),

# ---- rules copy now matches the real capacity ----
('      <li>Fill every seat on a bench and the whole bench clears out, freeing the space.</li>',
 '      <li>Every bench seats <b>two</b> guests (a wide bench, four). Fill it and the whole bench clears out.</li>'),
]

for a, b in PAIRS:
    if a not in s:
        raise SystemExit("MISS:\n" + a[:160])
    s = s.replace(a, b)

open(p, "w", encoding="utf-8").write(s)
print("patched game_tpl.html")
