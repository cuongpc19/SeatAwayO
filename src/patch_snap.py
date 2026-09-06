p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

old = '''function dropCell() {
  if (!HELD) return null;
  const b = HELD.seat;
  const c = Math.round((cellW(b.c) + HELD.dx - LAY.x0) / SX);
  const r = Math.round((cellZ(b.r) + HELD.dz - LAY.z0) / SZ);
  return [c, r];
}
function dropIsLegal() {
  const cell = dropCell();
  return !!(cell && HELD.targets.some(([c, r]) => c === cell[0] && r === cell[1]));
}'''
new = '''/** Where the held seat is hovering, in fractional cells. */
function dropAt() {
  const b = HELD.seat;
  return [(cellW(b.c) + HELD.dx - LAY.x0) / SX, (cellZ(b.r) + HELD.dz - LAY.z0) / SZ];
}
/** The legal destination nearest the cursor. Demanding an exact cell made tight
    boards feel like the seat refused to move: on most of them a seat has only one
    or two places to go, and rounding to the wrong one dropped it back home. */
function dropCell() {
  if (!HELD) return null;
  const [cf, rf] = dropAt();
  let best = null, bestD = SNAP * SNAP;
  for (const [c, r] of HELD.targets) {
    const d = (c - cf) * (c - cf) + (r - rf) * (r - rf);
    if (d < bestD) { bestD = d; best = [c, r]; }
  }
  return best;
}
const SNAP = 1.4;                 // how far from a legal cell a drop still counts'''
assert old in s; s = s.replace(old, new)

# the held seat should render where it will actually land, not under the raw cursor
old = '''  const cell = h.moved && dropIsLegal() ? dropCell() : null;'''
new = '''  const cell = h.moved ? dropCell() : null;'''
assert old in s; s = s.replace(old, new)

# tell the player when a seat genuinely has nowhere to go
old = '''  if (seat.locked) { bump(); releaseHeld(); draw(); return; }   // a passenger is on their way
  const w = pickWorld(ev.clientX, ev.clientY);
  HELD = { seat, w0: w, dx: 0, dz: 0, moved: false,
           x: ev.clientX, y: ev.clientY, targets: placements(S, seat) };'''
new = '''  if (seat.locked) { bump(); say("Somebody is already walking to that seat."); releaseHeld(); draw(); return; }
  const targets = placements(S, seat);
  if (!targets.length) {                      // boxed in on every side
    bump(); say("That seat is boxed in - free up a path beside it first.");
    releaseHeld(); draw(); return;
  }
  const w = pickWorld(ev.clientX, ev.clientY);
  HELD = { seat, w0: w, dx: 0, dz: 0, moved: false,
           x: ev.clientX, y: ev.clientY, targets };'''
assert old in s; s = s.replace(old, new)

# a one-line message channel that reverts to the standing hint
old = 'function bump() {'
new = '''let sayTimer = 0;
function say(msg) {
  const el = document.getElementById("hint");
  el.textContent = msg;
  clearTimeout(sayTimer);
  sayTimer = setTimeout(hud, 2600);
}
function bump() {'''
assert old in s; s = s.replace(old, new)

open(p, "w", encoding="utf-8").write(s)
print("drop snaps to the nearest legal cell; a boxed-in seat says so")
