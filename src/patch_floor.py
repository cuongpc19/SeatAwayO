p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

reps = [
# ---- the coaching overlays are off unless you ask for them ----
('let GUIDES = true;         // the coaching overlays - none of these are in the real game',
 'let GUIDES = false;        // the coaching overlays - none of these are in the real game'),
('    <button id="b-guides">Guides on</button>',
 '    <button id="b-guides">Guides off</button>'),

# ---- floor and shell colours sampled off the recording ----
('    quad(tileQuad(c, r, .006), (r + c) % 2 ? "#9d9b95" : "#8a8882");',
 '    quad(tileQuad(c, r, .006), (r + c) % 2 ? "#95948c" : "#545354");'),
('        P(cellW(g.W - 1 + pad), 0, cellZ(g.H - 1 + pad)), P(cellW(-pad), 0, cellZ(g.H - 1 + pad))], "#f0b21f");',
 '        P(cellW(g.W - 1 + pad), 0, cellZ(g.H - 1 + pad)), P(cellW(-pad), 0, cellZ(g.H - 1 + pad))], "#f8bf1a");'),
('        P(cellW(g.W - 1 + inner), .002, cellZ(g.H - 1 + inner)), P(cellW(-inner), .002, cellZ(g.H - 1 + inner))], "#d8480f");',
 '        P(cellW(g.W - 1 + inner), .002, cellZ(g.H - 1 + inner)), P(cellW(-inner), .002, cellZ(g.H - 1 + inner))], "#d2452c");'),
('  grad.addColorStop(0, "#dfe6ec"); grad.addColorStop(1, "#cbd4dc");',
 '  grad.addColorStop(0, "#fdfdfc"); grad.addColorStop(1, "#ececeb");'),

# ---- the doorway is an opening in the wall, not a painted floor tile ----
('''  // doorway
  quad(tileQuad(g.W - 1, g.door, .008), "#7fd2f2");
  const dq''',
 '''  // doorway: an opening in the wall, the floor under it stays plain
  const dq'''),
]
for a, b in reps:
    if a not in s:
        raise SystemExit("MISS:\\n" + a[:130])
    s = s.replace(a, b)

s = s.replace('.stage { position: relative; border-radius: 12px; overflow: hidden; border: 1px solid var(--line);\n'
              '         box-shadow: var(--shadow); background: #cfd6dd; }',
              '.stage { position: relative; border-radius: 12px; overflow: hidden; border: 1px solid var(--line);\n'
              '         box-shadow: var(--shadow); background: #f4f4f3; }')

open(p, "w", encoding="utf-8").write(s)
print("floor + shell recoloured, guides default off")
