p = "game_tpl.html"
s = open(p, encoding="utf-8").read()

PAIRS = [
# ---- carry the intended bench alongside each guest, so a solution always exists ----
('  const pool = COLOURS.slice(0, p.colours);\n'
 '  const queue = [];\n'
 '  let greyBudget = Math.round(placed * p.greyPct);',
 '  const pool = COLOURS.slice(0, p.colours);\n'
 '  const entries = [];\n'
 '  let greyBudget = Math.round(placed * p.greyPct);'),

('    for (let k = 0; k < b.cap; k++) queue.push(wantGrey ? colour : b.colour);\n'
 '  }\n'
 '  for (let i = queue.length - 1; i > 0; i--) {\n'
 '    const j = Math.floor(rand() * (i + 1));\n'
 '    [queue[i], queue[j]] = [queue[j], queue[i]];\n'
 '  }\n'
 '  return { level: L, W, H, benches, queue, total: queue.length, colours: p.colours,',
 '    for (let k = 0; k < b.cap; k++)\n'
 '      entries.push({ colour: wantGrey ? colour : b.colour, bid: b.id });\n'
 '  }\n'
 '  for (let i = entries.length - 1; i > 0; i--) {\n'
 '    const j = Math.floor(rand() * (i + 1));\n'
 '    [entries[i], entries[j]] = [entries[j], entries[i]];\n'
 '  }\n'
 '  const queue = entries.map(e => e.colour), plan = entries.map(e => e.bid);\n'
 '  return { level: L, W, H, benches, queue, plan, total: queue.length, colours: p.colours,'),

('  S.queue.shift();\n',
 '  S.queue.shift();\n  S.plan.shift();\n'),

# ---- hint: the bench this guest was generated for, or any legal one ----
('function flash() {',
 'function hintBench() {\n'
 '  if (!S.queue.length) return null;\n'
 '  const c = S.queue[0];\n'
 '  const want = S.benches[S.plan[0]];\n'
 '  if (legal(want, c)) return want;\n'
 '  return S.benches.find(b => legal(b, c)) || null;\n'
 '}\n'
 'let hintUntil = 0;\n'
 'function showHint() {\n'
 '  const b = hintBench();\n'
 '  if (!b) return;\n'
 '  hintUntil = performance.now() + 1400;\n'
 '  S.hint = b.id;\n'
 '  draw();\n'
 '  setTimeout(() => { if (performance.now() >= hintUntil) { S.hint = null; draw(); } }, 1450);\n'
 '}\n'
 'function flash() {'),

# ---- draw the hint ring ----
('  // collect drawables, painter-sorted by view depth',
 '  if (S.hint != null) {\n'
 '    const b = S.benches[S.hint];\n'
 '    if (b && !b.gone) {\n'
 '      const [wx, , wz] = cellPos(b.c, b.r, b.w);\n'
 '      const [px, py] = P(wx, 0.012, wz);\n'
 '      ctx.save();\n'
 '      ctx.strokeStyle = "#ffd23f"; ctx.lineWidth = Math.max(3, LAY.s * .09);\n'
 '      ctx.beginPath();\n'
 '      ctx.ellipse(px, py, SX * .62 * b.w * LAY.s, SX * .62 * LAY.s * .42, 0, 0, Math.PI * 2);\n'
 '      ctx.stroke(); ctx.restore();\n'
 '    }\n'
 '  }\n\n'
 '  // collect drawables, painter-sorted by view depth'),

# ---- hint button ----
('    <button id="b-jump">Jump to level&hellip;</button>',
 '    <button id="b-hint">Hint</button>\n'
 '    <button id="b-jump">Jump to level&hellip;</button>'),

('document.getElementById("b-skip").onclick = () => load(S.level + 10);',
 'document.getElementById("b-hint").onclick = showHint;\n'
 'document.getElementById("b-skip").onclick = () => load(S.level + 10);'),

# ---- rules mention the hint ----
('      <li>Clear the board before the clock runs out. If the next guest has nowhere legal to sit, the run ends.</li>',
 '      <li>Clear the board before the clock runs out. If the next guest has nowhere legal to sit, the run ends &mdash;\n'
 '        every board is generated with a guaranteed solution, and <b>Hint</b> will point at it.</li>'),
]

for a, b in PAIRS:
    if a not in s:
        raise SystemExit("MISS:\n" + a[:170])
    s = s.replace(a, b)

open(p, "w", encoding="utf-8").write(s)
print("patched")
