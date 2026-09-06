p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

reps = [
# ---- the door is a fixed spot in the wall, and is usually blocked at the start ----
("""  // the data does not pin the door down, so take the free right-edge row that
  // opens onto the most floor
  let best = -1, bestN = -1;
  for (let r = 0; r < H; r++) {
    if (!isFree(g, W - 1, r)) continue;
    g.door = r;
    const n2 = reachRegion(g).reduce((a, v) => a + v, 0);
    if (n2 > bestN) { bestN = n2; best = r; }
  }
  g.door = best < 0 ? Math.floor(H / 2) : best;""",
"""  // The level data never records the door, so it is a fixed spot in the wall the
  // same way it is in the game - and it is normally blocked by a seat at the
  // start, which is what the opening drag is for. DOOR_ROW is adjustable.
  g.door = Math.max(0, Math.min(H - 1, DOOR_ROW));"""),

("let S = null;", "let S = null;\nlet DOOR_ROW = 1;          // right-hand wall, one row in from the front"),

# ---- tell the player when the doorway itself is what needs clearing ----
("""  const region = reachRegion(g);
  const nextCol = g.queue.length ? g.queue[0] : -1;""",
"""  const region = reachRegion(g);
  const nextCol = g.queue.length ? g.queue[0] : -1;
  const doorBlocked = !isFree(g, g.W - 1, g.door);"""),

# blocking seat gets a warning ring
("""    if (canSeat(g, b, nextCol, region)) {""",
"""    if (doorBlocked && b.id === g.occ[idx(g, g.W - 1, g.door)]) {
      const cs = cellsOf(b), mid = cs[Math.floor(cs.length / 2)];
      push(cellW(mid[0]), cellZ(mid[1]), () => {
        const [px, py] = P(cellW(mid[0]), .02, cellZ(mid[1]));
        ctx.save(); ctx.strokeStyle = "#ffcf3d"; ctx.lineWidth = Math.max(3, LAY.s * .075);
        ctx.setLineDash([LAY.s * .18, LAY.s * .12]);
        ctx.beginPath(); ctx.ellipse(px, py, SX * .5 * LAY.s, SX * .5 * LAY.s * .42, 0, 0, Math.PI * 2);
        ctx.stroke(); ctx.restore();
      }, -.05);
    }
    if (canSeat(g, b, nextCol, region)) {"""),

# ---- door controls + a live status line ----
("""    <button id="b-jump">Go to level&hellip;</button>""",
"""    <button id="b-jump">Go to level&hellip;</button>
    <button id="b-door-up">Door &uarr;</button>
    <button id="b-door-dn">Door &darr;</button>"""),

("""document.getElementById("b-jump").onclick = () => {""",
"""document.getElementById("b-door-up").onclick = () => { DOOR_ROW = Math.max(0, S.door - 1); load(S.level); };
document.getElementById("b-door-dn").onclick = () => { DOOR_ROW = Math.min(S.H - 1, S.door + 1); load(S.level); };
document.getElementById("b-jump").onclick = () => {"""),

# ---- status line reflects what is actually going on ----
("""  document.getElementById("method").textContent =
    "Board " + S.name + " exactly as shipped. The level data does not record where the door is, so the player "
    + "opens it on the free right-edge row with the most floor behind it - that is the one assumption here.";""",
"""  const blocked = !isFree(S, S.W - 1, S.door);
  const reach = reachRegion(S).reduce((a, v) => a + v, 0);
  const freeTotal = S.W * S.H - S.hole.reduce((a, v) => a + v, 0) - S.seats.reduce((a, b) => a + b.len, 0);
  document.getElementById("hint").textContent = blocked
    ? "A seat is blocking the door - drag it clear first."
    : "Drag a seat to slide it. Tap a seat to send the next passenger.";
  document.getElementById("method").textContent =
    "Board " + S.name + ", exactly as shipped: same grid, seats, colours, passenger list and clock. "
    + "The level data never records the door, so it sits at a fixed spot on the right wall (row "
    + S.door + " of " + S.H + ", adjustable with the Door buttons) and, as in the game, a seat is often "
    + "parked in front of it. Right now " + reach + " of the " + freeTotal + " empty floor tiles connect to the door"
    + (blocked ? " - none, because the doorway itself is blocked." : ".");"""),
]

for a, b in reps:
    if a not in s:
        raise SystemExit("MISS:\n" + a[:160])
    s = s.replace(a, b)

open(p, "w", encoding="utf-8").write(s)
print("door patched")
