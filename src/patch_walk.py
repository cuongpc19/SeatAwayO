p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

# ---------- 1. a real path through the corridor, instead of a straight hop ----------
s = s.replace("""/** The seat the next passenger will walk to: the nearest one that will take them. */""",
"""/** The tiles a passenger actually walks: door -> corridor -> the seat itself.
    Rebuilt from the same BFS that decides reachability, so the route on screen
    is the route the rules used. */
function walkPath(g, seat) {
  const d = floorDist(g);
  let entry = null, best = Infinity, last = null;
  for (const [c, r] of cellsOf(seat)) {
    for (const [dc, dr] of DIRS) {
      const nc = c + dc, nr = r + dr;
      if (!inBoard(g, nc, nr)) continue;
      const dist = d[idx(g, nc, nr)];
      if (dist >= 0 && dist < best) { best = dist; entry = [nc, nr]; last = [c, r]; }
    }
  }
  if (!entry) return null;
  const path = [entry];
  let [c, r] = entry;
  while (d[idx(g, c, r)] > 0) {                    // walk the distances back downhill
    for (const [dc, dr] of DIRS) {
      const nc = c + dc, nr = r + dr;
      if (!inBoard(g, nc, nr)) continue;
      if (d[idx(g, nc, nr)] === d[idx(g, c, r)] - 1) { c = nc; r = nr; path.push([c, r]); break; }
    }
  }
  path.reverse();                                  // door first
  path.push(last);                                 // and finally onto the seat
  return path;
}

/** The seat the next passenger will walk to: the nearest one that will take them. */""")

# ---------- 2. animate along that path, paced so it can be followed ----------
OLD = s[s.index("    const a = { ci, x: cellW(S.W - 1) + SX * 2.0, z: cellZ(S.door), y: 0 };"):
        s.index("    S.boarding = true;")]
NEW = '''    const path = walkPath(S, seat) || [cell];
    const pts = [[cellW(S.W - 1) + SX * 2.0, cellZ(S.door)]];        // waiting at the stop
    for (const [c, r] of path) pts.push([cellW(c), cellZ(r)]);
    pts[pts.length - 1] = [cellW(cell[0]), cellZ(cell[1]) - .04];    // settle onto the seat

    let total = 0;
    const seg = [];
    for (let i = 1; i < pts.length; i++) {
      const L = Math.hypot(pts[i][0] - pts[i-1][0], pts[i][1] - pts[i-1][1]);
      seg.push(L); total += L;
    }
    const a = { ci, x: pts[0][0], z: pts[0][1], y: 0 };
    S.anim.push(a);
    const dur = Math.max(520, total * WALK_MS_PER_UNIT);
    const t0 = performance.now();
    const tick2 = now => {
      const t = Math.min(1, (now - t0) / dur);
      let want = t * total, i = 0;
      while (i < seg.length - 1 && want > seg[i]) { want -= seg[i]; i++; }
      const f = seg[i] ? Math.min(1, want / seg[i]) : 1;
      a.x = pts[i][0] + (pts[i+1][0] - pts[i][0]) * f;
      a.z = pts[i][1] + (pts[i+1][1] - pts[i][1]) * f;
      a.y = Math.abs(Math.sin(t * Math.PI * Math.max(2, seg.length))) * .13;   // a walking bob
      draw();
      if (t < 1) requestAnimationFrame(tick2);
      else {
        S.anim.splice(S.anim.indexOf(a), 1);
        seat.pending--; seat.occ.push(ci); S.seated++;
        hud(); draw();
        setTimeout(step, BOARD_GAP_MS);            // a beat between passengers
      }
    };
'''
s = s.replace(OLD, NEW)

# ---------- 3. pacing knobs + a speed control ----------
s = s.replace('let INSTANT = false;       // headless play-throughs skip the walk animation',
              'let INSTANT = false;       // headless play-throughs skip the walk animation\n'
              'let SPEED = 1;             // 1 = normal, 2 = double\n'
              'const BASE_MS_PER_UNIT = 260;                       // ms per grid unit walked\n'
              'const BASE_GAP_MS = 260;                            // pause between passengers')
s = s.replace("    const dur = Math.max(520, total * WALK_MS_PER_UNIT);",
              "    const dur = Math.max(520, total * BASE_MS_PER_UNIT) / SPEED;")
s = s.replace("        setTimeout(step, BOARD_GAP_MS);            // a beat between passengers",
              "        setTimeout(step, BASE_GAP_MS / SPEED);     // a beat between passengers")

s = s.replace('    <button id="b-door-auto">Door auto</button>',
              '    <button id="b-door-auto">Door auto</button>\n    <button id="b-speed">Speed 1&times;</button>')
s = s.replace('document.getElementById("b-door-auto").onclick = () => { DOOR_ROW = null; load(S.level); };',
              'document.getElementById("b-door-auto").onclick = () => { DOOR_ROW = null; load(S.level); };\n'
              'document.getElementById("b-speed").onclick = ev => {\n'
              '  SPEED = SPEED === 1 ? 2 : SPEED === 2 ? 0.5 : 1;\n'
              '  ev.target.textContent = "Speed " + (SPEED === 0.5 ? "\\u00bd" : SPEED) + "\\u00d7";\n'
              '};')

# ---------- 4. show the route while somebody is walking ----------
s = s.replace("""  const items = [];
  const push = (wx, wz, fn, bias) => items.push({ z: view(wx, 0, wz)[2] + (bias || 0), fn });""",
"""  for (const a of g.anim) {
    if (!a.route) continue;
    ctx.save(); ctx.globalAlpha = .30;
    for (const [c, r] of a.route) quad(tileQuad(c, r, .014), "#ffffff");
    ctx.restore();
  }

  const items = [];
  const push = (wx, wz, fn, bias) => items.push({ z: view(wx, 0, wz)[2] + (bias || 0), fn });""")
s = s.replace("    const a = { ci, x: pts[0][0], z: pts[0][1], y: 0 };",
              "    const a = { ci, x: pts[0][0], z: pts[0][1], y: 0, route: path };")

open(p, "w", encoding="utf-8").write(s)
print("walk patched")
