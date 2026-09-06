p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

# ---------- canvas takes the shape of the board ----------
OLD = s[s.index("function layout() {"):s.index("function P(x, y, z) {")]
NEW = '''/** World extents of everything we draw: the bus, plus the stop beside it. */
function extents(g) {
  const pad = 1.4;
  const x0 = -(g.W - 1) / 2 * SX, z0 = -(g.H - 1) / 2 * SZ;
  const pts = [];
  for (const [cc, rr] of [[-pad, -pad], [g.W - 1 + pad + 2.6, -pad],
                          [-pad, g.H - 1 + pad], [g.W - 1 + pad + 2.6, g.H - 1 + pad]])
    pts.push(view(x0 + cc * SX, 0, z0 + rr * SZ));
  pts.push(view(x0, 2.2, z0 - pad * SZ));
  const xs = pts.map(p => p[0]), ys = pts.map(p => -p[1]);
  return { x0, z0, minX: Math.min(...xs), maxX: Math.max(...xs),
           minY: Math.min(...ys), maxY: Math.max(...ys) };
}

/** Boards are tall and narrow; a fixed wide canvas would strand them in a sea of
    background. Give the canvas the board's own aspect instead. */
function fitCanvas(g) {
  const e = extents(g);
  const aspect = (e.maxX - e.minX) / (e.maxY - e.minY);
  const TARGET = 1250000;
  let w = Math.round(Math.sqrt(TARGET * aspect));
  let h = Math.round(TARGET / Math.max(w, 1));
  w = Math.max(620, Math.min(1900, w));
  h = Math.max(520, Math.min(1560, h));
  if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
}

function layout() {
  const g = S, e = extents(g);
  const s = Math.min((cv.width - 30) / (e.maxX - e.minX), (cv.height - 30) / (e.maxY - e.minY));
  const usedW = (e.maxX - e.minX) * s, usedH = (e.maxY - e.minY) * s;
  return { s,
           ox: (cv.width - usedW) / 2 - e.minX * s,
           oy: (cv.height - usedH) / 2 - e.minY * s,
           x0: e.x0, z0: e.z0 };
}

'''
s = s.replace(OLD, NEW)
s = s.replace("  S = g;\n  S.boarding = false;\n  LAY = layout();",
              "  S = g;\n  S.boarding = false;\n  fitCanvas(g);\n  LAY = layout();")
s = s.replace("function draw() {\n  if (!S) return;\n  const g = S;\n  LAY = layout();",
              "function draw() {\n  if (!S) return;\n  const g = S;\n  fitCanvas(g);\n  LAY = layout();")

# ---------- the Level readout should name the board, not its index ----------
s = s.replace('  document.getElementById("s-level").textContent = S.level;',
              '  const m = /Level_0*(\\d+)(?:_(\\d+))?(?:#(\\d+))?/.exec(S.name);\n'
              '  document.getElementById("s-level").textContent = m\n'
              '    ? m[1] + (m[2] ? "-" + m[2] : "") + (m[3] ? "\\u00b7" + m[3] : "")\n'
              '    : S.level;')
s = s.replace('<div class="stat"><div class="k">Level</div>',
              '<div class="stat"><div class="k">Campaign level</div>')

open(p, "w", encoding="utf-8").write(s)
print("fit patched")
