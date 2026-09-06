p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

# ---------- 1. hit-test the drawn sprite, not the floor tile under it ----------
OLD_PICK = s[s.index("function pickCell(clientX, clientY) {"):s.index("let down = null;")]
NEW_PICK = '''function toCanvas(clientX, clientY) {
  const rect = cv.getBoundingClientRect();
  return [(clientX - rect.left) / rect.width * cv.width,
          (clientY - rect.top) / rect.height * cv.height];
}
function pickCell(clientX, clientY) {
  const [px, py] = toCanvas(clientX, clientY);
  const o = P(0, 0, 0);
  const a = BX[0] * LAY.s, b = BZ[0] * LAY.s, c2 = -BX[1] * LAY.s, d = -BZ[1] * LAY.s;
  const det = a * d - b * c2;
  if (!det) return null;
  const dx = px - o[0], dy = py - o[1];
  const wx = (dx * d - b * dy) / det, wz = (a * dy - dx * c2) / det;
  const col = Math.round((wx - LAY.x0) / SX), row = Math.round((wz - LAY.z0) / SZ);
  if (col < 0 || col >= S.W || row < 0 || row >= S.H) return null;
  return [col, row];
}

/** A seat sprite - and the passenger on it - is drawn well above its floor tile,
    so hit-testing the tile means you have to aim at the ground under the seat.
    Test the drawn box instead and take the frontmost one. */
function pickSeatAt(clientX, clientY) {
  const [px, py] = toCanvas(clientX, clientY);
  let best = null, bestZ = -Infinity;
  for (const b of S.seats) {
    for (const [c, r] of cellsOf(b)) {
      const [sx, sy, sz] = P(cellW(c), 0, cellZ(r));
      const halfW = SX * .60 * LAY.s;
      const up = SX * (b.occ.length ? 1.15 : .70) * LAY.s;   // riders make it taller
      const down = SX * .28 * LAY.s;
      if (px >= sx - halfW && px <= sx + halfW && py >= sy - up && py <= sy + down && sz > bestZ) {
        bestZ = sz; best = b;
      }
    }
  }
  if (best) return best;
  const cell = pickCell(clientX, clientY);          // fall back to the floor tile
  return cell ? seatAt(S, cell[0], cell[1]) : null;
}

'''
s = s.replace(OLD_PICK, NEW_PICK)

# ---------- 2. pick up on press, show targets straight away, allow click-click ----------
OLD_IN = s[s.index("let down = null;"):s.index("/** Walking distance from the door")]
NEW_IN = '''let down = null;

function selectSeat(b) {
  S.sel = b;
  S.dragTargets = b ? placements(S, b) : null;
  draw();
}
function clearSel() { S.sel = null; S.dragTargets = null; S.drag = null; draw(); }

function tryMove(b, cell) {
  if (!cell || !S.dragTargets) return false;
  if (!S.dragTargets.some(([c, r]) => c === cell[0] && r === cell[1])) return false;
  place(S, b, cell[0], cell[1]);
  S.moves++;
  clearSel();
  hud(); draw();
  autoBoard();                      // whoever can now reach a seat gets on
  return true;
}

cv.addEventListener("pointerdown", ev => {
  if (!S || S.phase !== "play") return;
  const b = pickSeatAt(ev.clientX, ev.clientY);
  if (b) {
    down = { b, x: ev.clientX, y: ev.clientY, moved: false, wasSel: S.sel === b };
    selectSeat(b);                  // targets light up the moment you press
    S.drag = { b, hover: null };
    cv.setPointerCapture(ev.pointerId);
    draw();
    return;
  }
  // pressed empty floor: if a seat is selected, treat it as "put it here"
  if (S.sel && tryMove(S.sel, pickCell(ev.clientX, ev.clientY))) return;
  clearSel();
});

cv.addEventListener("pointermove", ev => {
  if (!down) return;
  if (!down.moved && Math.hypot(ev.clientX - down.x, ev.clientY - down.y) > 4) down.moved = true;
  const cell = pickCell(ev.clientX, ev.clientY);
  S.drag.hover = cell && S.dragTargets.some(([c, r]) => c === cell[0] && r === cell[1]) ? cell : null;
  draw();
});

cv.addEventListener("pointerup", ev => {
  if (!down) return;
  const d = down; down = null;
  const hover = S.drag && S.drag.hover;
  S.drag = null;
  if (d.moved) {
    if (hover) tryMove(d.b, hover); else { draw(); }
    return;
  }
  // a plain tap: keep it selected so it can be placed with a second tap,
  // and tapping the same seat again lets go of it
  if (d.wasSel) clearSel(); else draw();
});

cv.addEventListener("pointercancel", () => { down = null; S.drag = null; draw(); });

'''
s = s.replace(OLD_IN, NEW_IN)

# ---------- 3. draw the selection, not just an in-flight drag ----------
s = s.replace("""  if (g.drag) {
    for (const [c, r] of g.dragTargets) {
      ctx.save(); ctx.globalAlpha = .5;
      quad(tileQuad(c, r, .012), "#ffffff"); ctx.restore();
    }
  } else {""",
"""  if (g.sel && g.dragTargets) {
    for (const [c, r] of g.dragTargets) {
      ctx.save(); ctx.globalAlpha = .5;
      quad(tileQuad(c, r, .012), "#ffffff"); ctx.restore();
    }
  } else {""")

s = s.replace("    const drag = g.drag && g.drag.b === b;",
              "    const drag = g.sel === b;")

# a ring under the seat you are holding
s = s.replace("""  if (g.drag && g.drag.hover) {""",
"""  if (g.sel) {
    for (const [c, r] of cellsOf(g.sel)) {
      ctx.save(); ctx.globalAlpha = .55;
      quad(tileQuad(c, r, .016), "#ffd76a"); ctx.restore();
    }
  }
  if (g.drag && g.drag.hover) {""")

# ---------- 4. say how it works ----------
s = s.replace('<span class="hint" id="hint">Drag a seat to slide it. Passengers board by themselves.</span>',
              '<span class="hint" id="hint">Drag a seat, or tap it then tap where it should go.</span>')
s = s.replace('        : "Drag a seat to slide it. Passengers board by themselves.");',
              '        : "Drag a seat, or tap it then tap where it should go. Passengers board by themselves.");')
s = s.replace('<li><b>Dragging seats is your only move.</b> Passengers board on their own, one at a time, the moment the\n'
              '        one at the front can walk to a seat that will take them.</li>',
              '<li><b>Moving seats is your only move.</b> Grab a seat anywhere on it - the seat itself or the passenger\n'
              '        sitting on it - and drag, or tap it once and then tap the tile you want it on. Passengers board on\n'
              '        their own, one at a time, the moment the one at the front can walk to a seat that will take them.</li>')

open(p, "w", encoding="utf-8").write(s)
print("input patched")
