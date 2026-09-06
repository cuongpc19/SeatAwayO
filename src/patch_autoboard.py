p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

# ---------- 1. boarding is automatic; dragging is the only input ----------
a = s.index("function sendTo(b, instant) {")
b = s.index("function checkStuck() {")
NEW = '''/** Walking distance from the door to a cell, through empty floor only. */
function floorDist(g) {
  const N = g.W * g.H, d = new Int32Array(N).fill(-1);
  if (!isFree(g, g.W - 1, g.door)) return d;
  const start = idx(g, g.W - 1, g.door);
  d[start] = 0;
  const q = [[g.W - 1, g.door]];
  while (q.length) {
    const [c, r] = q.shift();
    for (const [dc, dr] of DIRS) {
      const nc = c + dc, nr = r + dr;
      if (!isFree(g, nc, nr) || d[idx(g, nc, nr)] >= 0) continue;
      d[idx(g, nc, nr)] = d[idx(g, c, r)] + 1;
      q.push([nc, nr]);
    }
  }
  return d;
}

/** The seat the next passenger will walk to: the nearest one that will take them. */
function pickSeat(g, ci) {
  const d = floorDist(g);
  let best = null, bestD = Infinity;
  for (const seat of g.seats) {
    if (!accepts(seat, ci)) continue;
    for (const [c, r] of cellsOf(seat)) {
      for (const [dc, dr] of DIRS) {
        const nc = c + dc, nr = r + dr;
        if (!inBoard(g, nc, nr)) continue;
        const dist = d[idx(g, nc, nr)];
        if (dist >= 0 && dist < bestD) { bestD = dist; best = seat; }
      }
    }
  }
  return best;
}

/** Passengers board on their own, one after another, for as long as somebody
    can reach a seat. The player never taps a seat - they only slide seats. */
function autoBoard(instant) {
  if (!S || S.phase !== "play") return;
  if (S.boarding && !instant) return;
  const step = () => {
    if (S.phase !== "play" || !S.queue.length) { S.boarding = false; if (!S.queue.length && S.seated === S.total) finish(true); return; }
    const ci = S.queue[0];
    const seat = pickSeat(S, ci);
    if (!seat) { S.boarding = false; hud(); draw(); return; }
    S.queue.shift();
    const slot = seat.occ.length + seat.pending;
    seat.pending++;
    const cell = cellsOf(seat)[slot];
    if (instant) {
      seat.pending--; seat.occ.push(ci); S.seated++;
      step(); return;
    }
    const a = { ci, x: cellW(S.W - 1) + SX * 2.0, z: cellZ(S.door), y: 0 };
    S.anim.push(a);
    const sx = a.x, sz = a.z, t0 = performance.now(), dur = 330;
    const tick2 = now => {
      const t = Math.min(1, (now - t0) / dur);
      a.x = sx + (cellW(cell[0]) - sx) * t;
      a.z = sz + (cellZ(cell[1]) - .04 - sz) * t;
      a.y = Math.sin(t * Math.PI) * .3;
      draw();
      if (t < 1) requestAnimationFrame(tick2);
      else {
        S.anim.splice(S.anim.indexOf(a), 1);
        seat.pending--; seat.occ.push(ci); S.seated++;
        hud(); draw();
        step();
      }
    };
    S.boarding = true;
    requestAnimationFrame(tick2);
  };
  step();
}

'''
s = s[:a] + NEW + s[b:]

reps = [
# tapping a seat no longer does anything; a drag is the whole game
('''  if (d.moved) {
    const hover = S.drag && S.drag.hover;
    S.drag = null; S.dragTargets = null;
    if (hover) { place(S, d.b, hover[0], hover[1]); S.moves++; }
    hud(); draw();
    return;
  }
  sendTo(d.b);
});''',
 '''  const hover = S.drag && S.drag.hover;
  S.drag = null; S.dragTargets = null;
  if (d.moved && hover) {
    place(S, d.b, hover[0], hover[1]);
    S.moves++;
    hud(); draw();
    autoBoard();               // whoever can now reach a seat gets on
    return;
  }
  hud(); draw();
});'''),

# highlight what the next passenger is heading for, not what you may tap
('    if (canSeat(g, b, nextCol, region)) {',
 '    if (b === g.nextSeat) {'),

('  const doorBlocked = !isFree(g, g.W - 1, g.door);',
 '  const doorBlocked = !isFree(g, g.W - 1, g.door);\n'
 '  g.nextSeat = g.queue.length ? pickSeat(g, g.queue[0]) : null;'),

# board once the level is set up
('  S = g;\n  document.getElementById("ov").classList.remove("on");\n  hud(); draw();',
 '  S = g;\n  S.boarding = false;\n  document.getElementById("ov").classList.remove("on");\n'
 '  hud(); draw();\n  autoBoard();'),

# rules
('''      <li>Passengers board one at a time through the <b>door</b> on the right and walk across the empty floor.</li>
      <li><b>Drag a seat</b> to slide it through the empty floor &mdash; that is how you open a path to a buried seat.</li>
      <li><b>Tap a seat</b> to send the next passenger to it. A coloured seat only takes its own colour; a
        <b>grey seat</b> takes anyone.</li>
      <li>Seats stay put once someone sits, so the empty floor never grows. Seat everyone before the clock runs out.</li>''',
 '''      <li><b>Dragging seats is your only move.</b> Passengers board on their own, one at a time, the moment the
        one at the front can walk to a seat that will take them.</li>
      <li>They come in through the <b>door</b> on the right and walk across empty floor only &mdash; seats block the way.
        A coloured seat takes only its own colour; a <b>grey seat</b> takes anyone.</li>
      <li>A seat with somebody already on it still slides, passenger and all.</li>
      <li>The empty floor never grows, and in a real board it is broken into pockets. Sliding seats to join those
        pockets up is the whole puzzle. Seat everyone before the clock runs out.</li>'''),

('    ? "A seat is blocking the door - drag it clear first."\n'
 '    : "Drag a seat to slide it. Tap a seat to send the next passenger.";',
 '    ? "A seat is parked in the doorway - drag it clear so people can get on."\n'
 '    : (S.queue.length && !S.nextSeat\n'
 '        ? "Nobody at the front can reach a seat they fit - slide seats to open a path."\n'
 '        : "Drag a seat to slide it. Passengers board by themselves.");'),

('    <span class="hint" id="hint">Drag a seat to move it. Tap a seat to send the next passenger.</span>',
 '    <span class="hint" id="hint">Drag a seat to slide it. Passengers board by themselves.</span>'),
]
for x, y in reps:
    if x not in s:
        raise SystemExit("MISS:\n" + x[:170])
    s = s.replace(x, y)

open(p, "w", encoding="utf-8").write(s)
print("auto-boarding patched")
