p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

reps = [
# a flag, on by default, that turns off every coaching overlay at once
('let INSTANT = false;       // headless play-throughs skip the walk animation',
 'let INSTANT = false;       // headless play-throughs skip the walk animation\n'
 'let GUIDES = true;         // the coaching overlays - none of these are in the real game'),

# 1. blue tint on floor the queue can currently walk
('      if (region[idx(g, c, r)]) { ctx.save(); ctx.globalAlpha = .22; quad(tileQuad(c, r, .012), "#bfe9ff"); ctx.restore(); }',
 '      if (GUIDES && region[idx(g, c, r)]) { ctx.save(); ctx.globalAlpha = .22; quad(tileQuad(c, r, .012), "#bfe9ff"); ctx.restore(); }'),

# 2. the route a passenger is walking
('  for (const a of g.anim) {\n    if (!a.route) continue;',
 '  for (const a of g.anim) {\n    if (!GUIDES || !a.route) continue;'),

# 3. yellow dashed ring on the seat blocking the doorway
('    if (doorBlocked && b.id === g.occ[idx(g, g.W - 1, g.door)]) {',
 '    if (GUIDES && doorBlocked && b.id === g.occ[idx(g, g.W - 1, g.door)]) {'),

# 4. white ring under the seat the next passenger is heading for
('    if (b === g.nextSeat) {',
 '    if (GUIDES && b === g.nextSeat) {'),

# toggle button
('    <button id="b-speed">Speed 1&times;</button>',
 '    <button id="b-speed">Speed 1&times;</button>\n    <button id="b-guides">Guides on</button>'),

('document.getElementById("b-speed").onclick = ev => {',
 'document.getElementById("b-guides").onclick = ev => {\n'
 '  GUIDES = !GUIDES;\n'
 '  ev.target.textContent = GUIDES ? "Guides on" : "Guides off";\n'
 '  draw();\n'
 '};\n'
 'document.getElementById("b-speed").onclick = ev => {'),

# say what they are
('    <p class="note" id="method"></p>',
 '    <p class="note">The blue floor tint, the white ring under a seat, the walking route and the yellow dashed\n'
 '      ring on a door-blocking seat are all coaching overlays added here &mdash; the shipped game draws none of\n'
 '      them. <b>Guides off</b> hides the lot. The yellow tile under a seat you have picked up, and the white\n'
 '      tiles showing where it may go, stay either way.</p>\n'
 '    <p class="note" id="method"></p>'),
]

for a, b in reps:
    if a not in s:
        raise SystemExit("MISS:\n" + a[:140])
    s = s.replace(a, b)

open(p, "w", encoding="utf-8").write(s)
print("guides made optional")
