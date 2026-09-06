p = "game_tpl.html"
s = open(p, encoding="utf-8").read()

PAIRS = [
# guests sit ON the bench, not in front of it
('  return [LAY.x0 + (b.c + cell) * SX + (sub ? .34 : -.34),\n'
 '          LAY.z0 + b.r * SZ - .06];',
 '  return [LAY.x0 + (b.c + cell) * SX + (sub ? .30 : -.30),\n'
 '          LAY.z0 + b.r * SZ - .30];'),

# queue needs real spacing between bodies
('    const wz = LAY.z0 + (S.H - 1) * SZ + 1.6 - i * 1.16;',
 '    const wz = LAY.z0 + (S.H - 1) * SZ + 1.7 - i * 1.38;'),
('  const shown = Math.min(S.queue.length, 9);',
 '  const shown = Math.min(S.queue.length, 7);'),

# trim the apron on the lane side so the plot sits centred in the frame
('  const gq = [[-pad, -pad - .4], [S.W - 1 + pad + 2.9, -pad - .4], [S.W - 1 + pad + 2.9, S.H - 1 + pad + .5], [-pad, S.H - 1 + pad + .5]]',
 '  const gq = [[-pad - .3, -pad - .4], [S.W - 1 + pad + 2.3, -pad - .4], [S.W - 1 + pad + 2.3, S.H - 1 + pad + .5], [-pad - .3, S.H - 1 + pad + .5]]'),

('  const laneX = x0 + (S.W - 1) * SX + 2.9;\n'
 '  pts.push(view(laneX + .9, 0, z0 + (S.H - 1) * SZ + 1.9));\n'
 '  pts.push(view(laneX + .9, 2.4, z0 - pad * SZ));',
 '  const laneX = x0 + (S.W - 1) * SX + 2.7;\n'
 '  pts.push(view(laneX + .55, 0, z0 + (S.H - 1) * SZ + 2.1));\n'
 '  pts.push(view(laneX + .55, 2.4, z0 - pad * SZ));'),

# the walking guest should land where they will sit
('    a.y = Math.sin(t * Math.PI) * 0.35;',
 '    a.y = Math.sin(t * Math.PI) * 0.32;'),
]

for a, b in PAIRS:
    if a not in s:
        raise SystemExit("MISS:\n" + a[:150])
    s = s.replace(a, b)

open(p, "w", encoding="utf-8").write(s)
print("patched")
