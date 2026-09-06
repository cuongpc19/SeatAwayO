p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

# ---- 1. an alpha map of the seat atlas, so picking can test the sprite itself ----
old = 'const onLoad = () => { if (++loaded === 2) { ready = true; draw(); } };'
new = '''let ALPHA = null;                   // per-pixel opacity of the seat atlas
function buildAlpha() {
  const cv2 = document.createElement("canvas");
  cv2.width = atlas.naturalWidth; cv2.height = atlas.naturalHeight;
  const c2 = cv2.getContext("2d", { willReadFrequently: true });
  c2.drawImage(atlas, 0, 0);
  const d = c2.getImageData(0, 0, cv2.width, cv2.height).data;
  const a = new Uint8Array(cv2.width * cv2.height);
  for (let i = 0, j = 3; i < a.length; i++, j += 4) a[i] = d[j];
  ALPHA = { w: cv2.width, h: cv2.height, a };
}
const onLoad = () => { if (++loaded === 2) { buildAlpha(); ready = true; draw(); } };'''
assert old in s; s = s.replace(old, new)

# ---- 2. hit-test a drawn sprite by its own pixels ----
old = "function pickSeatAt(clientX, clientY) {"
new = '''/** Does a drawn sprite actually cover this canvas point? Mirrors blit() exactly,
    then asks the atlas whether that pixel is opaque - a box around the sprite is
    far too generous under this camera and grabs the seat behind. */
function spriteHit(frame, wx, wy, wz, X, Y) {
  const f = META.frames[frame]; if (!f || !ALPHA) return false;
  const [px, py] = P(wx, wy, wz);
  const k = LAY.s / META.scale;
  const u = Math.round(f[0] + (X - (px - f[4] * k)) / k);
  const v = Math.round(f[1] + (Y - (py - f[5] * k)) / k);
  if (u < f[0] || u >= f[0] + f[2] || v < f[1] || v >= f[1] + f[3]) return false;
  return ALPHA.a[v * ALPHA.w + u] > 24;
}

function pickSeatAt(clientX, clientY) {'''
assert old in s; s = s.replace(old, new, 1)

# ---- 3. picking: frontmost sprite whose pixels are under the pointer ----
old = s[s.index("function pickSeatAt(clientX, clientY) {\n  const [px, py] = toCanvas"):
        s.index("/* ---------------- picking a seat up and putting it down ----------------")]
new = '''function pickSeatAt(clientX, clientY) {
  const [X, Y] = toCanvas(clientX, clientY);
  let best = null, bestZ = -Infinity;
  const take = (b, z) => { if (z > bestZ) { bestZ = z; best = b; } };
  for (const b of S.seats) {
    const [sx, sz] = seatCentre(b);
    if (spriteHit(seatFrame(b), sx, 0, sz, X, Y)) take(b, view(sx, 0, sz)[2]);
    b.occ.forEach((ci, i) => {                  // a passenger counts as their seat
      if (ci == null) return;
      const [c, r] = cellsOf(b)[i];
      if (spriteHit(riderFrame(b, ci), cellW(c), .05, cellZ(r) - .04, X, Y))
        take(b, view(cellW(c), 0, cellZ(r))[2] + .3);
    });
  }
  if (best) return best;
  const cell = pickCell(clientX, clientY);          // fall back to the floor tile
  return cell ? seatAt(S, cell[0], cell[1]) : null;
}

'''
s = s.replace(old, new)

# ---- 4. never keep a seat in hand after the button is up ----
old = '''cv.addEventListener("pointermove", ev => {
  if (!HELD) return;
  if (!HELD.moved'''
new = '''cv.addEventListener("pointermove", ev => {
  if (!HELD) return;
  // A pointerup delivered outside the canvas used to be missed, leaving the seat
  // stuck to a cursor with no button down. No buttons means the gesture is over.
  if (ev.buttons === 0) { endDrag(ev); return; }
  if (!HELD.moved'''
assert old in s; s = s.replace(old, new)

old = '''cv.addEventListener("pointerup", endDrag);
cv.addEventListener("pointercancel", () => { releaseHeld(); draw(); });'''
new = '''cv.addEventListener("pointerup", endDrag);
addEventListener("pointerup", endDrag);          // also when released off-canvas
cv.addEventListener("pointercancel", () => { releaseHeld(); draw(); });
addEventListener("pointercancel", () => { if (HELD) { releaseHeld(); draw(); } });'''
assert old in s; s = s.replace(old, new)

open(p, "w", encoding="utf-8").write(s)
print("pixel-accurate picking + release on lost pointerup")
