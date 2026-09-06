p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

a = s.index("let down = null;")
b = s.index("/** Walking distance from the door to a cell, through empty floor only. */")

NEW = '''/* ---------------- picking a seat up and putting it down ----------------
   One state, one gesture: press a seat, it follows the pointer, release to drop
   it. There is deliberately no sticky selection - carrying one over from the
   last press is what made it feel like the old seat was still in hand.        */

let HELD = null;   // { seat, w0, dx, dz, moved }

function dropCell() {
  if (!HELD) return null;
  const b = HELD.seat;
  const c = Math.round((cellW(b.c) + HELD.dx - LAY.x0) / SX);
  const r = Math.round((cellZ(b.r) + HELD.dz - LAY.z0) / SZ);
  return [c, r];
}
function dropIsLegal() {
  const cell = dropCell();
  return !!(cell && HELD.targets.some(([c, r]) => c === cell[0] && r === cell[1]));
}
function releaseHeld() { HELD = null; S.sel = null; S.dragTargets = null; }

cv.addEventListener("pointerdown", ev => {
  if (!S || S.phase !== "play") return;
  const seat = pickSeatAt(ev.clientX, ev.clientY);
  if (!seat) { releaseHeld(); draw(); return; }
  if (seat.locked) { bump(); releaseHeld(); draw(); return; }   // a passenger is on their way
  const w = pickWorld(ev.clientX, ev.clientY);
  HELD = { seat, w0: w, dx: 0, dz: 0, moved: false,
           x: ev.clientX, y: ev.clientY, targets: placements(S, seat) };
  S.sel = seat;
  try { cv.setPointerCapture(ev.pointerId); } catch (e) {}
  draw();
});

cv.addEventListener("pointermove", ev => {
  if (!HELD) return;
  if (!HELD.moved && Math.hypot(ev.clientX - HELD.x, ev.clientY - HELD.y) > 3) HELD.moved = true;
  const w = pickWorld(ev.clientX, ev.clientY);
  if (w && HELD.w0) { HELD.dx = w[0] - HELD.w0[0]; HELD.dz = w[1] - HELD.w0[1]; }
  draw();
});

function endDrag(ev) {
  if (!HELD) return;
  const h = HELD;
  const cell = h.moved && dropIsLegal() ? dropCell() : null;
  releaseHeld();
  if (cell) {
    place(S, h.seat, cell[0], cell[1]);
    S.moves++;
    hud(); draw();
    autoBoard();                       // whoever can now reach a seat gets on
  } else {
    draw();
  }
}
cv.addEventListener("pointerup", endDrag);
cv.addEventListener("pointercancel", () => { releaseHeld(); draw(); });
addEventListener("blur", () => { if (HELD) { releaseHeld(); draw(); } });

'''
s = s[:a] + NEW + s[b:]

# the renderer reads the held seat off HELD now
s = s.replace("  const held = g.drag && g.drag.ghost ? g.drag.b : null;\n"
              "  const gdx = held ? g.drag.ghost[0] : 0, gdz = held ? g.drag.ghost[1] : 0;",
              "  const held = HELD && HELD.moved ? HELD.seat : null;\n"
              "  const gdx = held ? HELD.dx : 0, gdz = held ? HELD.dz : 0;")

# a soft glow marks where it came from, nothing else lights up
s = s.replace("""  if (g.sel) {
    for (const [c, r] of cellsOf(g.sel)) {
      ctx.save(); ctx.globalAlpha = .34;
      quad(tileQuad(c, r, .016), "#ffe9a8"); ctx.restore();
    }
  }""",
"""  if (g.sel) {
    for (const [c, r] of cellsOf(g.sel)) {
      ctx.save(); ctx.globalAlpha = .30;
      quad(tileQuad(c, r, .016), "#ffe9a8"); ctx.restore();
    }
  }""")

s = s.replace("  const drag = g.sel === b;\n    if (b === held) continue;",
              "    if (b === held) continue;")
s = s.replace('blit("bench_" + nm, wx, 0, wz, drag ? .82 : 1, .78);',
              'blit("bench_" + nm, wx, 0, wz, 1, .78);')

s = s.replace("""      <li><b>Moving seats is your only move.</b> Grab a seat anywhere on it - the seat itself or the passenger
        sitting on it - and drag, or tap it once and then tap the tile you want it on. Passengers board on
        their own, one at a time, the moment the one at the front can walk to a seat that will take them.</li>""",
"""      <li><b>Moving seats is your only move.</b> Press a seat anywhere on it &mdash; the seat itself or the
        passenger sitting on it &mdash; and it follows the pointer until you let go. Passengers board on their own,
        one at a time, the moment the one at the front can walk to a seat that will take them.</li>""")

open(p, "w", encoding="utf-8").write(s)
print("drag rewritten as a single gesture")
