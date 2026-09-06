p = "game2_core.js"
s = open(p, encoding="utf-8").read()

start = s.index("/* ---------------- generation ---------------- */")
end = s.index("/* ---------------- board queries ---------------- */")

NEW = '''/* ---------------- generation ----------------
   The queue is not shuffled - it is *recorded from a playthrough*. We place the
   benches, then peel the board: repeatedly seat a guest on a bench the queue can
   currently walk to, sliding a bench out of the way when nothing is reachable.
   The order those guests were seated in becomes the queue, so the level ships
   with a proof that it can be cleared.                                        */

function makeLevel(L) {
  for (let attempt = 0; attempt < 24; attempt++) {
    const rand = rng(L * 2654435761 + 17 + attempt * 7919);
    const p = params(L, rng(L * 2654435761 + 17));
    const lv = tryBuild(L, p, rand);
    if (lv) { lv.attempt = attempt; return lv; }
  }
  return tryBuild(L, params(L, rng(L * 2654435761 + 17)), rng(99991), true);
}

function tryBuild(L, p, rand, force) {
  const W = p.W, H = p.H;
  const occ = new Int16Array(W * H).fill(-1);
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
  if (!benches.length) return null;

  const pool = COLOURS.slice(0, p.colours);
  let greyLeft = Math.round(placed * p.greyPct);
  for (const b of benches) {
    if (greyLeft >= b.len && rand() < .5) { b.colour = "grey"; greyLeft -= b.len; }
    else b.colour = pool[Math.floor(rand() * pool.length)];
  }

  // ---- peel the board to record a solvable queue ----
  const sim = {
    W, H, occ: Int16Array.from(occ),
    benches: benches.map(b => ({ id: b.id, c: b.c, r: b.r, len: b.len, colour: b.colour, occ: [], gone: false })),
  };
  const queue = [], plan = [];
  let guard = 0, moves = 0;
  const budget = placed * 8 + 80;
  while (sim.benches.some(b => !b.gone) && guard++ < budget) {
    const region = reachRegion(sim);
    const cand = sim.benches.filter(b => !b.gone && b.occ.length < b.len && benchTouches(sim, b, region));
    if (cand.length) {
      const b = cand[Math.floor(rand() * cand.length)];
      const colour = b.colour === "grey" ? pool[Math.floor(rand() * pool.length)] : b.colour;
      queue.push(colour); plan.push(b.id);
      b.occ.push(colour);
      if (b.occ.length >= b.len) clearBench(sim, b);
      continue;
    }
    // nothing reachable - slide one bench until something opens up
    let moved = false;
    const order = shuffle(sim.benches.filter(b => !b.gone), rand);
    for (const b of order) {
      for (const [c, r] of placements(sim, b, 160)) {
        const save = [b.c, b.r];
        moveBench(sim, b, c, r);
        const reg = reachRegion(sim);
        if (sim.benches.some(x => !x.gone && x.occ.length < x.len && benchTouches(sim, x, reg))) {
          moved = true; moves++; break;
        }
        moveBench(sim, b, save[0], save[1]);
      }
      if (moved) break;
    }
    if (!moved) return force ? finish() : null;
  }
  if (sim.benches.some(b => !b.gone) && !force) return null;

  function finish() {
    return {
      level: L, W, H, occ, benches,
      queue, plan, total: queue.length, colours: p.colours, seated: 0,
      minMoves: moves,
      time: p.time, left: p.time, phase: "play", anim: [], sel: null, hint: null,
    };
  }
  return finish();
}

'''

s = s[:start] + NEW + s[end:]
open(p, "w", encoding="utf-8").write(s)
print("rewrote generation")
