p = "game2_core.js"
s = open(p, encoding="utf-8").read()

a = s.index("/** Slide seats until `target` can be walked to.")
b = s.index("/* ================= solver / hint ================= */")

NEW = '''/* ================= generation =================
   Levels are built BACKWARDS from a full bus.

   Searching forwards for "how do I dig a corridor to that seat" is expensive and
   often fails. Run the tape backwards instead: everyone is already seated, and we
   repeatedly stand somebody up from a seat the door can reach, sliding a seat
   around when nothing is reachable. Every backward step is trivially legal, and
   reversing the recording gives a forward solution - so the level ships with a
   proof, and generation costs no search at all.                                */

function cloneBoard(lv) {
  return { W: lv.W, H: lv.H, door: lv.door, occ: Int16Array.from(lv.occ),
           seats: lv.seats.map(b => ({ id: b.id, c: b.c, r: b.r, len: b.len,
                                       colour: b.colour, occ: [] })) };
}

function makeLevel(L) {
  const p = params(L, rng(L * 2654435761 + 17));
  for (let attempt = 0; attempt < 14; attempt++) {
    const lv = tryBuild(L, p, rng(L * 2654435761 + 17 + attempt * 7919));
    if (lv) { lv.attempt = attempt; return lv; }
  }
  return tryBuild(L, Object.assign({}, p, { slots: Math.max(2, p.slots - 4) }), rng(31337), true);
}

function tryBuild(L, p, rand, force) {
  const W = p.W, H = p.H;
  const nFree = W * H - p.slots;
  if (nFree < 2) return null;

  // one connected pocket of empty floor, opening at the door
  const hole = new Uint8Array(W * H);
  const door = Math.floor(rand() * H);
  hole[door * W + (W - 1)] = 1;
  let carved = 1;
  while (carved < nFree) {
    let best = null, bestScore = -1;
    for (let r = 0; r < H; r++) for (let c = 0; c < W; c++) {
      if (hole[r * W + c]) continue;
      let n = 0;
      for (const [dc, dr] of DIRS) {
        const nc = c + dc, nr = r + dr;
        if (nc >= 0 && nc < W && nr >= 0 && nr < H && hole[nr * W + nc]) n++;
      }
      if (!n) continue;
      // grow compactly - a snaking pocket leaves every seat already reachable
      const score = n * 4 + rand();
      if (score > bestScore) { bestScore = score; best = [c, r]; }
    }
    if (!best) break;
    hole[best[1] * W + best[0]] = 1; carved++;
  }
  if (carved < nFree) return null;

  const occ = new Int16Array(W * H).fill(-1);
  const seats = [];
  for (let r = 0; r < H; r++) {
    for (let c = 0; c < W; c++) {
      if (hole[r * W + c] || occ[r * W + c] >= 0) continue;
      let len = 1;
      if (rand() < p.widePct && c + 1 < W && !hole[r * W + c + 1] && occ[r * W + c + 1] < 0) len = 2;
      const b = { id: seats.length, c, r, len, colour: null, occ: [] };
      for (let k = 0; k < len; k++) occ[r * W + c + k] = b.id;
      seats.push(b); c += len - 1;
    }
  }
  if (seats.length < 1) return null;

  const pool = COLOURS.slice(0, p.colours);
  let greyLeft = Math.round(p.slots * p.greyPct);
  for (const b of seats) {
    if (greyLeft >= b.len && rand() < .5) { b.colour = "grey"; greyLeft -= b.len; }
    else b.colour = pool[Math.floor(rand() * pool.length)];
  }

  // ---- run the tape backwards from a full bus ----
  const sim = { W, H, door, occ: Int16Array.from(occ),
                seats: seats.map(b => ({ id: b.id, c: b.c, r: b.r, len: b.len,
                                         colour: b.colour, occ: [] })) };
  for (const b of sim.seats) {
    for (let k = 0; k < b.len; k++) {
      b.occ.push(b.colour === "grey" ? pool[Math.floor(rand() * pool.length)] : b.colour);
    }
  }

  const back = [];
  let guard = 0;
  const budget = p.slots * 14 + 200;
  while (sim.seats.some(b => b.occ.length) && guard++ < budget) {
    const region = reachRegion(sim);
    const full = sim.seats.filter(b => b.occ.length && seatTouches(sim, b, region));
    const movers = [];
    for (const b of sim.seats) {
      if (!seatTouches(sim, b, region)) continue;
      for (const [dc, dr] of DIRS) {
        const c = b.c + dc, r = b.r + dr;
        if (r < 0 || r >= H || c < 0 || c + b.len > W) continue;
        let ok = true;
        for (let k = 0; k < b.len; k++) {
          const id = sim.occ[r * W + c + k];
          if (id >= 0 && id !== b.id) { ok = false; break; }
        }
        if (ok) movers.push([b, c, r]);
      }
    }
    const wantSlide = movers.length && (!full.length || rand() < p.slideBias);
    if (wantSlide) {
      const [b, c, r] = movers[Math.floor(rand() * movers.length)];
      const from = [b.c, b.r];
      moveSeat(sim, b, c, r);
      back.push({ t: "move", id: b.id, from, to: [c, r] });
      continue;
    }
    if (!full.length) break;
    const b = full[Math.floor(rand() * full.length)];
    back.push({ t: "seat", id: b.id, colour: b.occ.pop() });
  }
  if (sim.seats.some(b => b.occ.length)) return force ? null : null;

  // the board as the backward pass left it is where the level starts
  const startOcc = Int16Array.from(sim.occ);
  const startSeats = seats.map((b, i) => Object.assign({}, b, {
    c: sim.seats[i].c, r: sim.seats[i].r, occ: [],
  }));

  const script = [];
  for (let i = back.length - 1; i >= 0; i--) {
    const op = back[i];
    if (op.t === "seat") script.push({ t: "seat", id: op.id, colour: op.colour });
    else script.push({ t: "move", id: op.id, c: op.from[0], r: op.from[1] });
  }
  const queue = script.filter(o => o.t === "seat").map(o => o.colour);
  const plan = script.filter(o => o.t === "seat").map(o => o.id);
  if (!queue.length) return null;

  return { level: L, W, H, door, occ: startOcc, seats: startSeats,
           queue, plan, script, total: queue.length, colours: p.colours, seated: 0,
           digs: script.filter(o => o.t === "move").length,
           time: p.time, left: p.time, phase: "play",
           anim: [], sel: null, hint: null };
}

'''
s = s[:a] + NEW + s[b:]

# solver section: replace with a script-driven hint + a replay check
c = s.index("/* ================= solver / hint ================= */")
NEW2 = '''/* ================= solver / hint ================= */
/** Replay the recorded script - the proof the level shipped with. */
function replayScript(lv) {
  const g = cloneBoard(lv);
  let qi = 0, moves = 0;
  for (const op of lv.script) {
    const b = g.seats[op.id];
    if (op.t === "move") {
      const legal = placements(g, b).some(([c, r]) => c === op.c && r === op.r);
      if (!legal) return { ok: false, why: "recorded slide is not legal", at: qi };
      moveSeat(g, b, op.c, op.r); moves++;
    } else {
      if (!accepts(b, op.colour)) return { ok: false, why: "seat will not take passenger", at: qi };
      if (!seatTouches(g, b, reachRegion(g))) return { ok: false, why: "seat not reachable", at: qi };
      b.occ.push(op.colour); qi++;
    }
  }
  const done = g.seats.every(b => b.occ.length === b.len);
  return { ok: done && qi === lv.queue.length, moves, seated: qi };
}

/** Next thing to do, for the Hint button: follow the recorded script from
    wherever the board actually is, falling back to any legal seating. */
function planStep(g, queue, script, cursor) {
  if (!queue.length) return null;
  const colour = queue[0];
  const region = reachRegion(g);
  for (let i = cursor; i < script.length; i++) {
    const op = script[i];
    if (op.t !== "seat") continue;
    const b = g.seats[op.id];
    if (accepts(b, colour) && seatTouches(g, b, region)) return { seat: b, cursor: i };
    break;
  }
  for (const b of g.seats) if (accepts(b, colour) && seatTouches(g, b, region)) return { seat: b };
  // nothing reachable: suggest the next recorded slide
  for (let i = cursor; i < script.length; i++) {
    const op = script[i];
    if (op.t !== "move") continue;
    const b = g.seats[op.id];
    if (placements(g, b).some(([c, r]) => c === op.c && r === op.r)) return { move: b, to: [op.c, op.r] };
    break;
  }
  return null;
}
'''
s = s[:c] + NEW2
open(p, "w", encoding="utf-8").write(s)
print("generation rewritten backwards")
