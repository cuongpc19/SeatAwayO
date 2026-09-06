p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

reps = [
# ---- second atlas ----
('const ATLAS_SRC = "data:image/png;base64,/*__ATLAS__*/";',
 'const ATLAS_SRC = "data:image/png;base64,/*__ATLAS__*/";\n'
 'const WMETA = /*__WMETA__*/;\n'
 'const WALK_SRC = "data:image/png;base64,/*__WALK__*/";'),

('let atlas = new Image(), ready = false, LAY = null;\natlas.onload = () => { ready = true; draw(); };\natlas.src = ATLAS_SRC;',
 'let atlas = new Image(), walkAtlas = new Image(), LAY = null;\n'
 'let loaded = 0, ready = false;\n'
 'const onLoad = () => { if (++loaded === 2) { ready = true; draw(); } };\n'
 'atlas.onload = onLoad; walkAtlas.onload = onLoad;\n'
 'atlas.src = ATLAS_SRC; walkAtlas.src = WALK_SRC;'),

# ---- draw from the walk sheet ----
('function quad(pts, fill) {',
 '''/** One frame of the walk cycle: facing d/r/u/l, phase 0-3. */
function blitWalk(colour, facing, phase, wx, wy, wz) {
  const f = WMETA.frames["w" + facing + phase + "_" + colour];
  if (!f) return blit("idle_" + colour, wx, wy, wz, 1, .74);
  const [px, py] = P(wx, wy, wz);
  const k = LAY.s / WMETA.scale * .74;
  ctx.drawImage(walkAtlas, f[0], f[1], WMETA.tile, WMETA.tile,
                px - WMETA.pivot[0] * k, py - WMETA.pivot[1] * k,
                WMETA.tile * k, WMETA.tile * k);
}

function quad(pts, fill) {'''),

('  for (const a of g.anim)\n'
 '    push(a.x, a.z, () => { shadow(a.x, a.z, .3); blit("walk_" + (SPRITE[colName(a.ci)] || "grey"), a.x, a.y || 0, a.z, 1, .74); }, 1.5);',
 '  for (const a of g.anim)\n'
 '    push(a.x, a.z, () => {\n'
 '      shadow(a.x, a.z, .3);\n'
 '      blitWalk(SPRITE[colName(a.ci)] || "grey", a.facing || "d", a.phase || 0, a.x, a.y || 0, a.z);\n'
 '    }, 1.5);'),

# ---- track facing and stride while walking ----
('    const a = { ci, x: pts[0][0], z: pts[0][1], y: 0, route: path };',
 '    const a = { ci, x: pts[0][0], z: pts[0][1], y: 0, route: path, facing: "d", phase: 0 };'),

('      a.x = pts[i][0] + (pts[i+1][0] - pts[i][0]) * f;\n'
 '      a.z = pts[i][1] + (pts[i+1][1] - pts[i][1]) * f;\n'
 '      a.y = Math.abs(Math.sin(t * Math.PI * Math.max(2, seg.length))) * .13;   // a walking bob',
 '      a.x = pts[i][0] + (pts[i+1][0] - pts[i][0]) * f;\n'
 '      a.z = pts[i][1] + (pts[i+1][1] - pts[i][1]) * f;\n'
 '      const dx = pts[i+1][0] - pts[i][0], dz = pts[i+1][1] - pts[i][1];\n'
 '      if (Math.abs(dx) > 1e-6 || Math.abs(dz) > 1e-6)\n'
 '        a.facing = Math.abs(dx) > Math.abs(dz) ? (dx > 0 ? "r" : "l") : (dz > 0 ? "d" : "u");\n'
 '      a.phase = Math.floor((t * total) / STRIDE) % WMETA.phases;   // legs cycle with distance\n'
 '      a.y = Math.abs(Math.sin(t * Math.PI * Math.max(2, seg.length))) * .10;'),

('const BASE_GAP_MS = 260;                            // pause between passengers',
 'const BASE_GAP_MS = 260;                            // pause between passengers\n'
 'const STRIDE = 0.52;                                // world units per animation frame'),
]

for a, b in reps:
    if a not in s:
        raise SystemExit("MISS:\n" + a[:170])
    s = s.replace(a, b)

open(p, "w", encoding="utf-8").write(s)

# builder injects the walk sheet too
q = "build_game3.py"
t = open(q, encoding="utf-8").read()
t = t.replace('.replace("/*__ATLAS__*/", open(ART / "atlas_b64.txt", encoding="utf-8").read().strip()))',
              '.replace("/*__ATLAS__*/", open(ART / "atlas_b64.txt", encoding="utf-8").read().strip())\n'
              '          .replace("/*__WMETA__*/", open(ART / "walk_atlas.json", encoding="utf-8").read())\n'
              '          .replace("/*__WALK__*/", open(ART / "walk_atlas_b64.txt", encoding="utf-8").read().strip()))')
open(q, "w", encoding="utf-8").write(t)
print("walk cycle wired in")
