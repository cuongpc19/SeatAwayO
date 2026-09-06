p = "game2_core.js"
s = open(p, encoding="utf-8").read()

OLD = """  const occ = new Int16Array(W * H).fill(-1);
  const benches = [];
  const spots = [];
  for (let r = 0; r < H; r++) for (let c = 0; c < W; c++) spots.push([c, r]);
  shuffle(spots, rand);
  let placed = 0;
  for (const [c, r] of spots) {
    if (placed >= p.slots) break;
    if (occ[r * W + c] >= 0) continue;
    let len = 1;
    if (rand() < p.widePct && c + 1 < W && occ[r * W + c + 1] < 0 && placed + 2 <= p.slots) len = 2;
    const b = { id: benches.length, c, r, len, colour: null, occ: [], gone: false };
    for (let k = 0; k < len; k++) occ[r * W + c + k] = b.id;
    benches.push(b); placed += len;
  }
  if (!benches.length) return null;"""

NEW = """  // Carve the empty space as ONE connected blob touching the right edge, then
  // pack benches into everything else. Scattered holes would leave most benches
  // already reachable and the sliding would never matter.
  const nFree = W * H - p.slots;
  const hole = new Uint8Array(W * H);
  {
    const seedR = Math.floor(rand() * H);
    hole[seedR * W + (W - 1)] = 1;
    let carved = 1;
    const frontier = [[W - 1, seedR]];
    while (carved < nFree && frontier.length) {
      const i = Math.floor(rand() * frontier.length);
      const [c, r] = frontier[i];
      const dirs = shuffle([[1, 0], [-1, 0], [0, 1], [0, -1]], rand);
      let grew = false;
      for (const [dc, dr] of dirs) {
        const nc = c + dc, nr = r + dr;
        if (nc < 0 || nc >= W || nr < 0 || nr >= H) continue;
        if (hole[nr * W + nc]) continue;
        hole[nr * W + nc] = 1; carved++; frontier.push([nc, nr]); grew = true;
        break;
      }
      if (!grew) frontier.splice(i, 1);
    }
    if (carved < nFree) return null;
  }

  const occ = new Int16Array(W * H).fill(-1);
  const benches = [];
  let placed = 0;
  for (let r = 0; r < H; r++) {
    for (let c = 0; c < W; c++) {
      if (hole[r * W + c] || occ[r * W + c] >= 0) continue;
      let len = 1;
      if (rand() < p.widePct && c + 1 < W && !hole[r * W + c + 1] && occ[r * W + c + 1] < 0) len = 2;
      const b = { id: benches.length, c, r, len, colour: null, occ: [], gone: false };
      for (let k = 0; k < len; k++) occ[r * W + c + k] = b.id;
      benches.push(b); placed += len;
      c += len - 1;
    }
  }
  if (!benches.length) return null;"""

if OLD not in s:
    raise SystemExit("placement block not found")
s = s.replace(OLD, NEW)

# solvability gate: replay the recorded plan, which is the actual proof
OLD2 = s[s.index("/** Replay a level headlessly to prove the queue can be cleared. */"):]
NEW2 = """/** Replay the recorded plan - the proof the level shipped with. */
function replayPlan(lv) {
  const g = {
    W: lv.W, H: lv.H, occ: Int16Array.from(lv.occ),
    benches: lv.benches.map(b => ({ id: b.id, c: b.c, r: b.r, len: b.len,
                                    colour: b.colour, occ: [], gone: false })),
  };
  let moves = 0;
  for (let i = 0; i < lv.queue.length; i++) {
    const b = g.benches[lv.plan[i]], colour = lv.queue[i];
    if (!accepts(b, colour)) return { ok: false, at: i, why: "bench will not take this guest" };
    if (!benchTouches(g, b, reachRegion(g))) {
      let done = false;
      for (const [c, r] of placements(g, b)) {
        const save = [b.c, b.r];
        moveBench(g, b, c, r);
        if (benchTouches(g, b, reachRegion(g))) { done = true; moves++; break; }
        moveBench(g, b, save[0], save[1]);
      }
      if (!done) return { ok: false, at: i, why: "cannot be reached" };
    }
    b.occ.push(colour);
    if (b.occ.length >= b.len) clearBench(g, b);
  }
  return { ok: true, moves };
}

/** How far a plain greedy player gets - this is what the Hint button uses. */
function greedySolves(lv) {
  const g = {
    W: lv.W, H: lv.H, occ: Int16Array.from(lv.occ),
    benches: lv.benches.map(b => ({ id: b.id, c: b.c, r: b.r, len: b.len,
                                    colour: b.colour, occ: [], gone: false })),
    queue: lv.queue.slice(),
  };
  let guard = 0;
  const budget = lv.total * 6 + 60;
  while (g.queue.length && guard++ < budget) {
    const step = planStep(g);
    if (!step) return false;
    if (step.seat) {
      const b = step.seat;
      b.occ.push(g.queue.shift());
      if (b.occ.length >= b.len) clearBench(g, b);
    } else moveBench(g, step.move, step.to[0], step.to[1]);
  }
  return g.queue.length === 0;
}
"""
s = s.replace(OLD2, NEW2)
s = s.replace("    const lv = tryBuild(L, p, rand);\n    if (lv) { lv.attempt = attempt; return lv; }",
              "    const lv = tryBuild(L, p, rand);\n"
              "    if (lv && replayPlan(lv).ok) { lv.attempt = attempt; return lv; }")
open(p, "w", encoding="utf-8").write(s)
print("patched: carved free space + plan replay as the solvability gate")
