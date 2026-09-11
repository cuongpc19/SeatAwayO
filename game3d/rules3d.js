/* The board rules, ported from src/engine.js.

   This is the full set the shipped campaign actually needs, which is more than
   the prototypes carried: two doors, blocked cells, and seats padlocked until
   somebody sits in them. Everything here answers to the same laws the 2085
   boards were designed against - what a seat covers, which side you may enter
   from, what counts as reachable floor.

   ⚠ Nothing in here removes a seat when it fills. It stops being offered,
   because accepts() tests freeSlots, and it goes on being furniture. The `gone`
   flag that an earlier prototype copied lives only in src/bench_rush.html, an
   abandoned build that src/solvecheck.py still points at. */

const DIRS = [[0, -1], [1, 0], [0, 1], [-1, 0]];
const FACING = DIRS;                  // 0 up, 1 right, 2 down, 3 left
const GREY_TAKES = 2;                 // a grey seat only ever takes the first colour

const idx = (g, c, r) => r * g.W + c;
/** ⚠ `block` as well as `hole`. A hole is a cell with no floor at all; a blocked
    cell has floor with something bolted to it. Nobody walks through either, and
    no seat slides onto either, but only the hole skips being drawn. */
const inBoard = (g, c, r) => c >= 0 && c < g.W && r >= 0 && r < g.H
  && !g.hole[idx(g, c, r)] && !g.block[idx(g, c, r)];
const isFree = (g, c, r) => inBoard(g, c, r) && g.occ[idx(g, c, r)] < 0;

/** The grid cells a seat covers. Even facings run along x, odd along z. */
function cellsOf(b) {
  const a = [];
  for (let k = 0; k < b.len; k++) a.push(b.dir & 1 ? [b.c, b.r + k] : [b.c + k, b.r]);
  return a;
}
const placeCell = (b, k) => cellsOf(b)[k];        // len === cap in this data

/** Never in over the backrest, so the step directly behind a seat is not a way in. */
function entryDirs(b) {
  const f = FACING[b.dir];
  return DIRS.filter(d => !(d[0] === -f[0] && d[1] === -f[1]));
}
function cellEntries(g, b, k) {
  const own = new Set(cellsOf(b).map(p => p[0] + "," + p[1]));
  const pc = placeCell(b, k), out = [];
  for (const d of entryDirs(b)) {
    const nc = pc[0] + d[0], nr = pc[1] + d[1];
    if (!inBoard(g, nc, nr) || own.has(nc + "," + nr)) continue;
    out.push([nc, nr]);
  }
  return out;
}

function place(g, b, c, r) {
  for (const p of cellsOf(b)) g.occ[idx(g, p[0], p[1])] = -1;
  b.c = c; b.r = r;
  for (const p of cellsOf(b)) g.occ[idx(g, p[0], p[1])] = b.id;
}
const walkerAt = (g, c, r) => g.walkers.some(a => a.cell && a.cell[0] === c && a.cell[1] === r);

function fits(g, b, c, r) {
  const hc = b.c, hr = b.r;
  b.c = c; b.r = r; const cs = cellsOf(b); b.c = hc; b.r = hr;
  for (const p of cs) {
    if (!inBoard(g, p[0], p[1])) return false;
    const id = g.occ[idx(g, p[0], p[1])];
    if (id >= 0 && id !== b.id) return false;
    if (walkerAt(g, p[0], p[1])) return false;      // never drop a seat onto a person
  }
  return true;
}

/* ---- doors -------------------------------------------------------------
   Every board has one, on the right wall. A hundred and ten of them carry a
   second, facing it across the floor, with its own queue.

   ⚠ The two lines are not halves of one. Their colours differ on 77 of the 78
   boards that ship both, so somebody at the wrong door cannot stand in for
   somebody at the right one - they each have to be served where they are. */
const doorCell = (g, k) => g.doors[k || 0];
const queueOf = (g, k) => (k ? g.queue2 : g.queue);

function reachRegion(g, k) {
  const seen = new Uint8Array(g.W * g.H), d = doorCell(g, k || 0);
  if (!isFree(g, d[0], d[1])) return seen;
  seen[idx(g, d[0], d[1])] = 1;
  const st = [[d[0], d[1]]];
  while (st.length) {
    const p = st.pop();
    for (const dd of DIRS) {
      const nc = p[0] + dd[0], nr = p[1] + dd[1];
      if (isFree(g, nc, nr) && !seen[idx(g, nc, nr)]) { seen[idx(g, nc, nr)] = 1; st.push([nc, nr]); }
    }
  }
  return seen;
}
function floorDist(g, k) {
  const dist = new Int32Array(g.W * g.H).fill(-1), d = doorCell(g, k || 0);
  if (!isFree(g, d[0], d[1])) return dist;
  dist[idx(g, d[0], d[1])] = 0;
  const q = [[d[0], d[1]]];
  while (q.length) {
    const p = q.shift();
    for (const dd of DIRS) {
      const nc = p[0] + dd[0], nr = p[1] + dd[1];
      if (!isFree(g, nc, nr) || dist[idx(g, nc, nr)] >= 0) continue;
      dist[idx(g, nc, nr)] = dist[idx(g, p[0], p[1])] + 1;
      q.push([nc, nr]);
    }
  }
  return dist;
}

const freeSlots = b => b.occ.reduce((n, v) => n + (v == null ? 1 : 0), 0);
const accepts = (b, ci) => freeSlots(b) > (b.pending || 0)
  && (b.colour === 0 ? ci === GREY_TAKES : b.colour === ci);
/** Grey seats are fixtures: bolted down, and they only take the first colour. */
const FIXED = b => b.colour === 0;
/** ⚠ `chain`, not `locked`. This is the padlock on the back of the seat, and
    SITTING is what opens it - so accepts() must go on treating a chained seat as
    an ordinary seat of its colour, or nobody could ever sit there and it could
    never come free. */
const canDrag = b => !FIXED(b) && !b.chain;

function placements(g, b) {
  if (!canDrag(b)) return [];
  const seen = new Set([b.c + "," + b.r]), out = [], q = [[b.c, b.r]];
  while (q.length) {
    const p = q.shift();
    for (const d of DIRS) {
      const nc = p[0] + d[0], nr = p[1] + d[1], key = nc + "," + nr;
      if (seen.has(key)) continue;
      const hc = b.c, hr = b.r;
      b.c = p[0]; b.r = p[1];
      const ok = fits(g, b, nc, nr);
      b.c = hc; b.r = hr;
      if (!ok) continue;
      seen.add(key); out.push([nc, nr]); q.push([nc, nr]);
    }
  }
  return out;
}

/* ---- the jump booster ---------------------------------------------------
   A jump is not a seat that moves - it is a passenger that FLIES. The player
   picks a seat the front of a queue can sit in, and they go straight to it over
   the top of whatever is in the way. That is the whole point of it: the seat
   that would win the board is usually the one nothing can walk to, and a
   booster that only slides a seat is a booster that does what dragging already
   does for free.

   ⚠ engine.js has an `if (JUMP)` branch inside placements() that reads exactly
   like that second, wrong booster. It is dead code there - the shell answers
   the tap through onSeatPick() first - and copying it into this port is what
   broke the booster here.

   Everything except the route is ordinary boarding: the same claim on the
   place, the same pending count, the same landing through seatTaken(). So a
   jump into a queue that is already walking needs no bookkeeping of its own. */

/** The place the front of a queue could take on this seat, or -1. */
function freeSlot(b) {
  for (let k = 0; k < b.cap; k++) if (b.occ[k] == null && !b.claim.has(k)) return k;
  return -1;
}

/** Which door's queue can send somebody into this seat, or null. ⚠ Same
    turn-taking order as nextUp(), or an armed jump lets one line overtake the
    other and a two-door board empties lopsided. */
function jumpDoor(g, b) {
  const order = g.lastDoor === 0 ? [1, 0] : [0, 1];
  for (const k of order) {
    const q = queueOf(g, k);
    if (q.length && accepts(b, q[0])) return k;
  }
  return null;
}

/** Claim a place for a flight, or null when nobody can sit there.

    ⚠ Grey and padlocked seats are both legal targets, and neither is obvious.
    accepts() already says a grey fixture takes the first colour; a padlock is
    opened by somebody SITTING in the seat, which seatTaken() does on landing -
    so the booster opens it too.

    ⚠ null must leave the booster armed and the gold unspent. A booster that
    charges for a tap that did nothing is worse than no booster at all. */
function jumpBoard(g, b) {
  if (!g || g.phase !== "play" || !b) return null;
  const door = jumpDoor(g, b);
  if (door == null) return null;
  const k = freeSlot(b);
  if (k < 0) return null;
  const ci = queueOf(g, door).shift();
  g.lastDoor = door;
  b.claim.add(k); b.pending++;
  return { b: b, k: k, ci: ci, door: door };
}

/** The one place somebody can take without setting foot on the floor: a seat
    standing in the doorway itself. It is still a plug - nothing behind it is
    reachable while it sits there - but being told to move a seat you could
    simply have sat in reads as the game being broken. */
function doorSeat(g, ci, door) {
  const d = doorCell(g, door || 0);
  const id = g.occ[idx(g, d[0], d[1])];
  if (id < 0) return null;
  const b = g.seats[id];
  if (!b || !accepts(b, ci)) return null;
  for (let k = 0; k < b.cap; k++) {
    if (b.occ[k] != null || b.claim.has(k)) continue;
    const pc = placeCell(b, k);
    if (pc[0] === d[0] && pc[1] === d[1]) return { b: b, k: k, entry: null, door: door || 0 };
  }
  return null;
}
/** The nearest place this colour can actually reach from that door. */
function pickSeat(g, ci, door) {
  door = door || 0;
  const plug = doorSeat(g, ci, door);
  if (plug) return plug;
  const dist = floorDist(g, door);
  let best = null, bd = Infinity;
  for (const b of g.seats) {
    if (!accepts(b, ci)) continue;
    for (let k = 0; k < b.cap; k++) {
      if (b.occ[k] != null || b.claim.has(k)) continue;
      for (const e of cellEntries(g, b, k)) {
        const dd = dist[idx(g, e[0], e[1])];
        if (dd >= 0 && dd < bd) { bd = dd; best = { b: b, k: k, entry: e, door: door }; }
      }
    }
  }
  return best;
}
/** Which line moves next. ⚠ They take turns where both can move, so one door
    does not empty while the other stands still. */
function nextUp(g) {
  const order = g.lastDoor === 0 ? [1, 0] : [0, 1];
  for (const k of order) {
    const q = queueOf(g, k);
    if (!q.length) continue;
    const spot = pickSeat(g, q[0], k);
    if (spot) return spot;
  }
  return null;
}

/** Door -> corridor -> the place itself, rebuilt from the same search that
    decided reachability, so the route walked is the route the rules used. */
function walkPath(g, b, k, entry, door) {
  if (!entry) return [];
  const dist = floorDist(g, door || 0);
  let c = entry[0], r = entry[1];
  const path = [[c, r]];
  let guard = 0;
  while (dist[idx(g, c, r)] > 0 && guard++ < 600) {
    for (const d of DIRS) {
      const nc = c + d[0], nr = r + d[1];
      if (inBoard(g, nc, nr) && dist[idx(g, nc, nr)] === dist[idx(g, c, r)] - 1) { c = nc; r = nr; break; }
    }
    path.push([c, r]);
  }
  path.reverse();
  path.push(placeCell(b, k));
  return path;
}

/** Somebody has taken place k. Returns true if that seat's padlock just opened. */
function seatTaken(g, b, k, ci) {
  b.occ[k] = ci;
  b.claim.delete(k);
  b.pending--;
  g.seated++;
  if (!b.chain) return false;
  b.chain = false;                    // sitting in it is what unlocks it
  return true;
}

function loadLevel(n) {
  const raw = LEVELS[Math.max(0, Math.min(LEVELS.length - 1, n - 1))];
  const W = raw.w, H = raw.h;
  const hole = new Uint8Array(W * H);
  for (const i of (raw.hl || [])) hole[i] = 1;
  const block = new Uint8Array(W * H);
  const fixtures = (raw.fx || []).filter(f => f[0] >= 0 && f[0] < W && f[1] >= 0 && f[1] < H);
  for (const f of fixtures) block[f[1] * W + f[0]] = 1;
  const locked = new Set(raw.lk || []);
  const occ = new Int16Array(W * H).fill(-1);
  const seats = raw.s.map(function (s, i) {
    return {
      id: i, c: s[0], r: s[1], cap: s[2], len: s[2], colour: s[3], dir: s[4] | 0,
      occ: new Array(s[2]).fill(null), claim: new Set(), pending: 0,
      chain: locked.has(i),
    };
  });
  const q2 = raw.q2 || [];
  const g = {
    W: W, H: H, hole: hole, block: block, fixtures: fixtures, occ: occ, seats: seats,
    queue: raw.q.slice(), queue2: q2.slice(),
    doors: q2.length ? [[W - 1, raw.dr], [0, raw.dr2]] : [[W - 1, raw.dr]],
    lastDoor: 1,                      // so the first person comes from door 0
    total: raw.q.length + q2.length, seated: 0, walkers: [],
    time: raw.t, left: raw.t, diff: raw.d | 0, phase: "play", level: n, cool: 0,
  };
  for (const b of seats) for (const p of cellsOf(b)) occ[idx(g, p[0], p[1])] = b.id;
  return g;
}

/** The add-line booster: a whole new column down the left, and everything
    already on the board steps one cell right to make room.

    ⚠ The doorway steps right with everything else. A near door left on the old
    W-1 is an interior cell with a seat now standing on it - reachRegion finds
    the door blocked, nobody can walk in, and the booster the player just paid
    for is what made the board unwinnable. The far door is already on column 0
    and stays there; the new lane becomes the outer edge on that side. */
function addLine(g) {
  const W = g.W + 1;
  const hole = new Uint8Array(W * g.H), block = new Uint8Array(W * g.H);
  for (let r = 0; r < g.H; r++) for (let c = 0; c < g.W; c++) {
    hole[r * W + c + 1] = g.hole[r * g.W + c];
    block[r * W + c + 1] = g.block[r * g.W + c];
  }
  for (const f of g.fixtures) f[0]++;
  for (const b of g.seats) b.c++;
  for (const d of g.doors) if (d[0] === g.W - 1) d[0] = W - 1;
  g.W = W; g.hole = hole; g.block = block;
  g.occ = new Int16Array(W * g.H).fill(-1);
  for (const b of g.seats) for (const p of cellsOf(b)) g.occ[idx(g, p[0], p[1])] = b.id;
  return true;
}

/** Stars come off the clock, the one thing the level data itself scores.
    Lifted from src/game_shell.js so a level scores here exactly as it ships. */
const starsFor = g => { const f = g.left / g.time; return f >= .55 ? 3 : f >= .25 ? 2 : 1; };
