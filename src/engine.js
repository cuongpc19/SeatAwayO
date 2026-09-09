/* Index to colour, and the order is the shipped game's, not ours: level 1 is
   index 2 and it is sky blue there, the second colour to turn up (level 4) is
   index 4 and it is green. The level data carries only these indices - it has no
   colours in it at all - so this table is the whole of the game's palette.

   ⚠ 5 and 6 moved with 2, they were not re-chosen. 2 shares a board with 5 on
   490 of the 600 levels and with 6 on 13, and 5 was a teal cyan and 6 a blue:
   put a sky blue at index 2 and those boards have two blues on them that have to
   be told apart at a glance. 5 takes the orange index 2 gave up, 6 takes purple. */
const NAMES = ["grey", "red", "sky", "yellow", "green", "orange", "purple", "blue", "pink", "lime", "teal", "brown", "navy"];
const CSS = { grey: "#969ca8", red: "#e83e48", orange: "#fa822a", yellow: "#fac42e", green: "#4ac65c",
              sky: "#239be1", blue: "#2e92f2", purple: "#a25cea", pink: "#f470b0",
              lime: "#a8d94a", teal: "#25a89b", brown: "#b0784a", navy: "#3b56a8" };
const SPRITE = { grey: "grey", red: "red", orange: "orange", yellow: "yellow", green: "green",
                 sky: "sky", blue: "blue", purple: "purple", pink: "pink",
                 lime: "green", teal: "sky", brown: "orange", navy: "blue" };
const colName = i => NAMES[i] || "grey";

const SX = 1.60, SZ = 1.60;
const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];

/* ---------------- projection (matches how the atlas was baked) ---------------- */
function rotM(yaw, pitch) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cx = Math.cos(pitch), sx = Math.sin(pitch);
  return [[cy, 0, sy], [sx * sy, cx, -sx * cy], [-cx * sy, sx, cx * cy]];
}
const R = rotM(META.yaw, META.pitch);
const view = (x, y, z) => [R[0][0]*x + R[0][1]*y + R[0][2]*z,
                           R[1][0]*x + R[1][1]*y + R[1][2]*z,
                           R[2][0]*x + R[2][1]*y + R[2][2]*z];
const BX = view(1, 0, 0), BZ = view(0, 0, 1);

/* ---------------- model ---------------- */
let S = null;
let DOOR_ROW = null;       // null = pick it automatically, see load()
let INSTANT = false;       // headless play-throughs skip the walk animation
let LOAD_TOKEN = 0;        // animation callbacks hold the global S, so a reload
                           // mid-walk would let the old chain seat people into
                           // the new board. Every load stamps a fresh token.
let GUIDES = false;        // the coaching overlays - none of these are in the real game
let SPEED = 1;             // 1 = normal, 2 = double
/* The pause between a board appearing and the queue starting. It exists for one
   reason - so a first-time player sees the first passenger hop on rather than
   finding them already sitting - so the shell turns it off once that lesson is
   over. Zero is a board that starts boarding on the frame it opens. */
let OPEN_MS = 2000;
/* Walking pace. 260, 300 and 520 are the numbers measured off the recording, and
   each constant is that measurement divided by how much quicker the game runs -
   always recomputed from the original rather than from the last value, or the
   rounding creeps further off with every pass.

   ⚠ The floor and the hop no longer share a divisor, and that is deliberate. The
   walk is at 1.15 x 1.20 x 1.20 x 1.10 = 1.8216; the hop is one notch back down
   the same ladder, at 1.38, so it is a fifth slower than the pace that carried
   the passenger to the seat. Speeding the two together is what made the landing
   read as a twitch: crossing the floor is travel and can be brisk, but the jump
   onto the seat is the beat the whole walk was for, and it is the only moment
   the eye is actually asked to follow.

   The two still have to be moved as a pair even so - taking the floor without
   the hop gives a passenger who strides across the room and then dawdles onto
   the seat, which is the same fault in the other direction.

   MIN_WALK_MS keeps the floor's divisor: it is a walk, just a short one.

   The walk cycle needs nothing here: `a.phase` counts STRIDE off the distance
   covered, so the legs step faster on their own and stay in step with the floor
   rather than skating over it. */
const BASE_MS_PER_UNIT = 143;                       // ms per grid unit walked
const MIN_WALK_MS = 285;                            // a walk is never snappier than this

/* ⚠ The ROOM decides the pace, not the walk. Big boards read as slow and small
   ones do not, and it is not the pace that differs - that is 143ms a cell
   everywhere - it is that a 7x11 asks for a five-cell crossing where a 3x6 asks
   for one. The first attempt at this keyed off the length of each walk, which
   is wrong in a way that only shows up mid-game: a 4x6 with half its seats
   moved throws up a seven-cell crossing too, that walk got shortened along with
   the big ones, and level 11 came out hurried.

   So it is read off W + H, once, and every walk in a room shares it. 4x6 and
   under keep the measured original exactly; it tapers to BIG_PACE at 7x11, the
   largest vehicle in the game.

   `?pace=N` forces one value everywhere, for a side-by-side. */
const SMALL_SPAN = 10;         // 4x6 - the opening, untouched
const BIG_SPAN = 18;           // 7x11 - the party bus and the coach
const BIG_PACE = 0.72;
let PACE_FORCED = 0;           // ?pace=, 0 = off

function walkPace(g) {
  if (PACE_FORCED) return PACE_FORCED;
  const span = g.W + g.H;
  if (span <= SMALL_SPAN) return 1;
  if (span >= BIG_SPAN) return BIG_PACE;
  return 1 - (1 - BIG_PACE) * (span - SMALL_SPAN) / (BIG_SPAN - SMALL_SPAN);
}
// The little jump onto the seat. 217 was measured off the recording and is the
// one beat in the sequence worth stretching: it is the moment the move pays off,
// and at walking speed it went by before it read as a jump at all.
const HOP_MS = 300;

const BASE_GAP_MS = 260;                            // pause between passengers - waiting, not walking
const STRIDE = 0.52;                                // world units per animation frame
const QUEUE_PITCH = 1.15;                           // world units between two people in line
const QUEUE_STEP_MS = QUEUE_PITCH * BASE_MS_PER_UNIT;   // one place up the line, at walking pace
const QUEUE_GAP_MS = 110;                           // before the person behind follows
const idx = (g, c, r) => r * g.W + c;
const inBoard = (g, c, r) => c >= 0 && c < g.W && r >= 0 && r < g.H && !g.hole[idx(g, c, r)];
const isFree = (g, c, r) => inBoard(g, c, r) && g.occ[idx(g, c, r)] < 0;

/** The grid cells a seat covers. SeatDirect 0 and 2 lie along x, 1 and 3 along z.
    `len` is the footprint in cells, which is not the same as how many people fit:
    see placeCell. */
function cellsOf(b) {
  const a = [];
  for (let k = 0; k < b.len; k++) a.push(b.dir & 1 ? [b.c, b.r + k] : [b.c + k, b.r]);
  return a;
}

/** The cell place k sits in. In the binary levels a bench covered one cell per
    person, so the two numbers were interchangeable and the code used `len` for
    both. 1.63.1 packs two, three or four places into a single cell instead, so a
    place maps onto the footprint rather than being it. */
function placeCell(b, k) {
  const j = b.len === b.cap ? k : Math.floor(k * b.len / b.cap);
  return b.dir & 1 ? [b.c, b.r + j] : [b.c + j, b.r];
}
/** Which way the seat faces, as a grid step. 0 up, 1 right, 2 down, 3 left. */
const FACING = [[0, -1], [1, 0], [0, 1], [-1, 0]];

/** The three ways into a seat: over the cushion, or from either side. Never over
    the backrest, so the step directly behind the seat is not one of them. */
function entryDirs(b) {
  const [fx, fz] = FACING[b.dir];
  return DIRS.filter(([dc, dr]) => !(dc === -fx && dr === -fz));
}

/** Floor tiles from which a passenger could take seat `b`'s k-th place.
    Each place is entered on its own - nobody walks through one seat to reach
    the next place along. */
function cellEntries(g, b, k) {
  const own = new Set(cellsOf(b).map(([c, r]) => c + "," + r));
  const [c, r] = placeCell(b, k);
  const out = [];
  for (const [dc, dr] of entryDirs(b)) {
    const nc = c + dc, nr = r + dr;
    if (!inBoard(g, nc, nr) || own.has(nc + "," + nr)) continue;
    out.push([nc, nr]);
  }
  return out;
}
function entryCells(g, b) {
  const seen = new Set(), out = [];
  for (let k = 0; k < b.cap; k++)
    for (const [c, r] of cellEntries(g, b, k)) {
      const key = c + "," + r;
      if (seen.has(key)) continue;
      seen.add(key); out.push([c, r]);
    }
  return out;
}

function place(g, b, c, r) {
  for (const [cc, rr] of cellsOf(b)) g.occ[idx(g, cc, rr)] = -1;
  b.c = c; b.r = r;
  for (const [cc, rr] of cellsOf(b)) g.occ[idx(g, cc, rr)] = b.id;
}
/** A cell somebody is standing in right now. Their whole remaining route used to
    be off-limits, which froze seats all over the board; only the tile actually
    under their feet is. */
function walkerAt(g, c, r) {
  for (const a of g.anim) {
    const ac = Math.round((a.x - LAY.x0) / SX), ar = Math.round((a.z - LAY.z0) / SZ);
    if (ac === c && ar === r) return true;
  }
  return false;
}

function fits(g, b, c, r) {
  const save = [b.c, b.r];
  b.c = c; b.r = r;
  const cs = cellsOf(b);
  b.c = save[0]; b.r = save[1];
  for (const [cc, rr] of cs) {
    if (!inBoard(g, cc, rr)) return false;
    // The doorway is NOT reserved. Keeping it clear was my own invention and it
    // quietly walled off the board: on a 4-wide grid the door cell is often the
    // only link between the top row and the right-hand column, so seats had two
    // legal cells where they should have had a dozen. A seat parked in the door
    // is the normal starting state of this game - clearing it is the puzzle.
    const id = g.occ[idx(g, cc, rr)];
    if (id >= 0 && id !== b.id) return false;
    if (walkerAt(g, cc, rr)) return false;        // never drop a seat onto a person
  }
  return true;
}
/** The cell a door stands in. Door 0 is the one every board has, on the right
    wall; door 1 exists only where the level ships a second queue. */
const doorCell = (g, k) => (g.doors && g.doors[k]) || [g.W - 1, g.door];
const queueOf = (g, k) => (k ? (g.queue2 || []) : g.queue);
/** Where the line for a door waits, in world units - outside the wall it is on. */
/* How far off the wall each line stands. The far one is pulled in a little: it
   is the difference between a board that keeps its size and one that shrinks to
   make room, and nobody reads a queue by how much air is behind it. */
const LANE_NEAR = 2.0, LANE_FAR = 1.55;
function stopAt(g, k) {
  const [dc, dr] = doorCell(g, k);
  return [cellW(dc) + (dc === 0 ? -SX * LANE_FAR : SX * LANE_NEAR), cellZ(dr)];
}
/** Which way a line trails back from its door: away from the board, so a door at
    the front has its queue running off the back and one at the back has it
    running off the front. Both trailing the same way would lay the far line
    across the board it is waiting to get into. */
const queueDir = (g, k) => (doorCell(g, k)[1] * 2 < g.H ? 1 : -1);

function reachRegion(g, k) {
  const seen = new Uint8Array(g.W * g.H);
  const [DC, DR] = doorCell(g, k || 0);
  if (!isFree(g, DC, DR)) return seen;
  seen[idx(g, DC, DR)] = 1;
  const st = [[DC, DR]];
  while (st.length) {
    const [c, r] = st.pop();
    for (const [dc, dr] of DIRS) {
      const nc = c + dc, nr = r + dr;
      if (isFree(g, nc, nr) && !seen[idx(g, nc, nr)]) { seen[idx(g, nc, nr)] = 1; st.push([nc, nr]); }
    }
  }
  return seen;
}
function touches(g, b, region) {
  for (const [c, r] of entryCells(g, b)) if (region[idx(g, c, r)]) return true;
  return false;
}
const freeSlots = b => b.occ.reduce((n, v) => n + (v == null ? 1 : 0), 0);

/** What a grey seat will take.

    ⚠ Not a wildcard. It reads like one - a seat with no colour on it - and this
    was written as one, but the shipped game only ever seats the FIRST colour in
    a grey seat, and every screenshot of it shows the same: grey seats with sky
    blue in them and nothing else. Checked against the boards before changing it:
    with grey tied to colour 2 there is still a place for every passenger on all
    600 campaign levels, which is the condition the wildcard was hiding.

    The number is index 2 because that is the colour level 1 opens with - see the
    note on NAMES. */
const GREY_TAKES = 2;
const accepts = (b, ci) =>
  freeSlots(b) > (b.pending || 0) && (b.colour === 0 ? ci === GREY_TAKES : b.colour === ci);
function canSeat(g, b, ci, region) { return accepts(b, ci) && touches(g, b, region || reachRegion(g)); }

/** Where this seat can slide to, one cell at a time through the empty floor. */
/** Grey seats are fixtures: they never move, and they only take the first colour
    (see `accepts`). They are the fixed walls of the puzzle - 568 of the 600
    boards have at least one. */
const FIXED = b => b.colour === 0;

/** The jump booster lifts a seat over everything instead of sliding it, so the
    reachable set becomes every cell it simply fits in. */
let JUMP = false;

function placements(g, b) {
  if (b.locked || FIXED(b)) return [];
  if (JUMP) {
    const out = [];
    for (let r = 0; r < g.H; r++) for (let c = 0; c < g.W; c++)
      if (!(c === b.c && r === b.r) && fits(g, b, c, r)) out.push([c, r]);
    return out;
  }
  const seen = new Set([b.c + "," + b.r]), out = [], q = [[b.c, b.r]];
  while (q.length) {
    const [c, r] = q.shift();
    for (const [dc, dr] of DIRS) {
      const nc = c + dc, nr = r + dr, k = nc + "," + nr;
      if (seen.has(k)) continue;
      const home = [b.c, b.r];
      b.c = c; b.r = r;
      const ok = fits(g, b, nc, nr);
      b.c = home[0]; b.r = home[1];
      if (!ok) continue;
      seen.add(k); out.push([nc, nr]); q.push([nc, nr]);
    }
  }
  return out;
}

function load(n) {
  const raw = LEVELS[Math.max(0, Math.min(LEVELS.length - 1, n - 1))];
  const W = raw.w, H = raw.h;
  const hole = new Uint8Array(W * H);
  for (const i of raw.holes) hole[i] = 1;
  const occ = new Int16Array(W * H).fill(-1);
  const seats = raw.seats.map((s, i) => ({
    id: i, c: s[0], r: s[1], cap: s[2], colour: s[3],
    dir: s[4] | 0,                                  // SeatDirect 0..3, straight from the APK
    len: s.length > 5 ? s[5] : s[2],                // footprint; the binary levels had none
    occ: new Array(s[2]).fill(null),                // one entry per place
    pending: 0, locked: false,
  }));
  const g = { W, H, hole, occ, seats, door: 0, level: n, name: raw.id || raw.name,
              token: ++LOAD_TOKEN };
  for (const b of seats) for (const [c, r] of cellsOf(b)) occ[idx(g, c, r)] = b.id;

  // The shipped level data never records the door. In the recording it sits on
  // the right wall just past the front-most seats, so take the first free
  // right-edge cell counting from the front of the bus. The Door buttons win
  // over everything; failing those, a board exported from the editor carries the
  // row it was saved with, which is the only way a `door` key gets into a board.
  if (DOOR_ROW != null) {
    g.door = Math.max(0, Math.min(H - 1, DOOR_ROW));
  } else if (raw.door != null) {
    g.door = Math.max(0, Math.min(H - 1, raw.door));
  } else {
    let pick = -1;
    for (let r = 0; r < H; r++) if (isFree(g, W - 1, r)) { pick = r; break; }
    g.door = pick < 0 ? 0 : pick;
  }

  g.queue = raw.queue.slice();
  /* A second line, on the boards that ship one. Where its door stands is read
     a choice rather than a reading: Cadillac and Limo are the only panels that
     use this and neither carries a second door object - theirs is in the vehicle
     mesh - so nothing in the bundle says. Facing the first across the floor is
     what draws two lines a player can tell apart; both on one wall would have
     them running into each other, and the near one is 20 deep on these boards.

     The two lines are not halves of one. Their colours differ on 77 of the 78
     boards - each carries a colour the other has none of - so a passenger at the
     wrong door cannot stand in for one at the right door. */
  g.queue2 = (raw.queue2 || []).slice();
  const d2 = raw.door2 == null ? Math.max(0, H - 2)
                               : Math.max(0, Math.min(H - 1, raw.door2));
  g.doors = g.queue2.length ? [[W - 1, g.door], [0, d2]] : [[W - 1, g.door]];
  g.lastDoor = 1;                        // so the first launch comes from door 0
  g.total = g.queue.length + g.queue2.length;
  g.colours = new Set(raw.queue.concat(g.queue2)).size;
  g.time = raw.time; g.left = raw.time;
  g.seated = 0; g.phase = "play"; g.moves = 0; g.walkCells = null;
  g.sel = null; g.drag = null; g.anim = []; g.qsteps = [null, null];
  g.lines = 0;                  // add-line booster: one spare lane per board
  S = g;
  S.boarding = false; S.launching = false;
  FIN = null; SHIFT = [0, 0];   // the last room's ending stops here
  fitCanvas(g);
  LAY = layout();
  onNewLevel();                 // each shell clears its own end-of-level card
  onHud(); draw();
  /* A beat before anybody moves, on the boards that teach. Boarding used to
     start on the same frame the board appeared, so on a level where the queue
     can walk straight in - level 1 is one - the first passenger was already
     sitting down before the player had looked at the screen, and the hop that
     teaches the whole game went unseen.

     Only where there is something to see: a beat on a board whose queue cannot
     reach a seat yet is two seconds of a still picture, so that one starts at
     once. INSTANT keeps its synchronous path - headless play-throughs read
     S.seated on the next line and cannot wait out a timer. */
  const beat = OPEN_MS && nextUp(g) ? OPEN_MS : 0;
  if (INSTANT || !beat) autoBoard();
  else {
    const token = S.token;
    setTimeout(() => { if (S && S.token === token) autoBoard(); }, beat / SPEED);
  }
}

/* ---------------- the line at the stop ---------------- */
/** The distance one person still has to walk, in places.

    Reading it back mid-walk is what lets the next shuffle start from wherever
    this one had got to: passengers leave every BASE_GAP_MS, which is less than
    a step takes, so the line is usually still moving when the next place opens
    and somebody can be carrying two or three places at once.

    Hence `from` setting the duration rather than dividing a fixed one: the pace
    is what has to stay put, and a walk of three places takes three times as
    long. Timed the other way, the same code covered a quarter of a place in one
    frame - the jump this was written to remove, only smeared over four frames.
    Flat, too, and not eased: a queue shuffling up is a dozen little walks that
    run into each other, and easing each one out and in again puts a stutter at
    every join. What sells it as walking is the legs, which the draw runs off
    this same distance. */
function placesBack(st, now) {
  const t = (now - st.t0) / (st.from * QUEUE_STEP_MS / SPEED);
  return t <= 0 ? st.from : t >= 1 ? 0 : st.from * (1 - t);
}

/** Everyone left in the line steps up one place.

    The line used to be drawn straight off the queue index, so the moment the
    head of it walked away, all six behind them slid forward a full place inside
    one frame. Now each keeps the distance they are still carrying and walks it
    off, and they start one after another - the person behind you does not move
    until you have. */
function shuffleUp(g, k) {
  k = k || 0;
  const steps = g.qsteps || (g.qsteps = [null, null]);
  const now = performance.now(), was = steps[k];
  //  was[i + 1] is this same person a moment ago: the line has already shifted,
  //  so what is now place i held place i + 1 when that state was written.
  steps[k] = queueOf(g, k).map((_, i) => {
    const carry = was && was[i + 1] ? placesBack(was[i + 1], now) : 0;
    return {
      from: carry + 1,
      // Standing still, you wait for the person in front to move off first. Still
      // walking, you carry straight on - stopping to take your turn again is how
      // a walk of two places turns into two stutters.
      t0: carry > 1e-3 ? now : now + i * QUEUE_GAP_MS / SPEED,
    };
  });
  if (g.qraf) return;                 // one loop is enough; it reads whatever is current
  g.qraf = true;
  const tick = () => {
    if (S !== g || !g.qsteps) { g.qraf = false; return; }
    const now2 = performance.now();
    // both lines share the one loop: it runs while either still has ground to cover
    const busy = g.qsteps.some(ss => ss && ss.some(st => placesBack(st, now2) > 1e-3));
    if (busy) { draw(); requestAnimationFrame(tick); }
    else { g.qsteps = [null, null]; g.qraf = false; draw(); }
  };
  requestAnimationFrame(tick);
}

/* ---------------- rendering ---------------- */
const cv = document.getElementById("board"), ctx = cv.getContext("2d");
let atlas = new Image(), walkAtlas = new Image(), LAY = null;
let loaded = 0, ready = false;
let ALPHA = null;                   // per-pixel opacity of the seat atlas
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
const onLoad = () => { if (++loaded === 2) { buildAlpha(); ready = true; draw(); } };
atlas.onload = onLoad; walkAtlas.onload = onLoad;
atlas.src = ATLAS_SRC; walkAtlas.src = WALK_SRC;

/** World extents of everything we draw: the bus, plus the stop beside it. */
function extents(g) {
  // The editor leaves room around the board to read it; the game wants the
  // carriage as large as the screen allows, so it reserves only the wall, the
  // step and the head of the queue - the platform behind that can run off-screen.
  const pad = RICH ? .72 : 1.4;
  const right = RICH ? 2.45 : pad + 2.6;
  // A second line stands the same distance off the far wall, so the view has to
  // reach as far that way as it does towards the stop. Without this the whole
  // lane is outside the frame and the players in it are simply not drawn.
  const left = (g.doors && g.doors.length > 1) ? right : pad;
  const high = RICH ? 1.55 : 2.2;
  const x0 = -(g.W - 1) / 2 * SX, z0 = -(g.H - 1) / 2 * SZ;
  const pts = [];
  for (const [cc, rr] of [[-left, -pad], [g.W - 1 + right, -pad],
                          [-left, g.H - 1 + pad], [g.W - 1 + right, g.H - 1 + pad]])
    pts.push(view(x0 + cc * SX, 0, z0 + rr * SZ));
  pts.push(view(x0, high, z0 - pad * SZ));
  const xs = pts.map(p => p[0]), ys = pts.map(p => -p[1]);
  return { x0, z0, minX: Math.min(...xs), maxX: Math.max(...xs),
           minY: Math.min(...ys), maxY: Math.max(...ys) };
}

/** Boards are tall and narrow; a fixed wide canvas would strand them in a sea of
    background. Give the canvas the board's own aspect instead. */
function fitCanvas(g) {
  if (RICH) {
    // The dressed-up view has ground running to every edge, so the canvas takes
    // the shape of its box rather than the board's: letterboxing it would cut
    // the platform off in a straight line and give the seam away.
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.max(320, Math.round(cv.clientWidth * dpr));
    const h = Math.max(320, Math.round(cv.clientHeight * dpr));
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    return;
  }
  const e = extents(g);
  const aspect = (e.maxX - e.minX) / (e.maxY - e.minY);
  const TARGET = 1250000;
  let w = Math.round(Math.sqrt(TARGET * aspect));
  let h = Math.round(TARGET / Math.max(w, 1));
  w = Math.max(620, Math.min(1900, w));
  h = Math.max(520, Math.min(1560, h));
  if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
}

/* Where the grid sits inside the canvas, as fractions of it. A painted backdrop
   is a fixed picture, so the grid has to land in a fixed place or the aisle in
   the picture drifts away from the queue every time the window changes shape. */
function frame() {
  const wide = cv.width / cv.height > 1.05;
  // Off the edges on every side, so the room reads as sitting in a place rather
  // than being cropped by the window.
  const head = themeNow().head;
  // Two lines want room on both sides, so the grid gives some back rather than
  // running to the edge. It costs the board a little width; a queue nobody can
  // see costs the player the level.
  // A two-line board is a wider picture, so it gets the whole window rather than
  // the usual margin - the board keeps its size and the extra goes to the lanes.
  const two = !!(S && S.doors && S.doors.length > 1);
  if (two) return wide ? { left: .22, right: .82, top: head, bottom: .93 }
                       : { left: .01, right: .99, top: head - .02, bottom: .94 };
  return wide ? { left: .26, right: .78, top: head, bottom: .93 }
              : { left: .04, right: .95, top: head - .02, bottom: .94 };
}

function layout() {
  const g = S, e = extents(g);
  if (RICH) {
    // The grid's own corners, at unit scale.
    // Out to the OUTER FACE OF THE WALLS, not the grid: the walls stand almost a
    // cell proud of it, so fitting the grid alone pushed them off the edge. And
    // out to where the queue stands, or a small board throws the head of the line
    // past the right-hand side.
    const WALL = .90;
    const gx = g.W * SX / 2 + WALL, gz = g.H * SZ / 2 + WALL;
    const qx = (g.W - 1) * SX / 2 + SX * 2.45;
    const rx = Math.max(gx, qx);
    // and out to the far line as well, where there is one - it stands outside
    // the far wall, so fitting to the wall leaves it off the canvas entirely
    const lx = (g.doors && g.doors.length > 1)
      ? Math.max(gx, (g.W - 1) * SX / 2 + SX * (LANE_FAR + .5)) : gx;
    const c = [view(-lx, 0, -gz), view(rx, 0, -gz), view(-lx, 0, gz), view(rx, 0, gz)];
    const xs = c.map(p => p[0]), ys = c.map(p => -p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const F = frame();
    const s = Math.min((F.right - F.left) * cv.width / (maxX - minX),
                       (F.bottom - F.top) * cv.height / (maxY - minY));
    // Centred, so the room and the queue sit in the middle of the window and the
    // panels can come in beside them. A painted plate is the one case that still
    // pins the right edge, because the aisle drawn into the picture has to line
    // up with the queue whatever the board.
    const ox = BG ? F.right * cv.width - maxX * s
                  : (F.left + F.right) / 2 * cv.width - (minX + maxX) / 2 * s;
    return { s,
             ox,
             oy: (F.top + F.bottom) / 2 * cv.height - (minY + maxY) / 2 * s,
             x0: e.x0, z0: e.z0 };
  }
  const m = 30;
  const s = Math.min((cv.width - m) / (e.maxX - e.minX), (cv.height - m) / (e.maxY - e.minY));
  const usedW = (e.maxX - e.minX) * s, usedH = (e.maxY - e.minY) * s;
  return { s,
           ox: (cv.width - usedW) / 2 - e.minX * s,
           oy: (cv.height - usedH) / 2 - e.minY * s,
           x0: e.x0, z0: e.z0 };
}

function P(x, y, z) {
  const v = view(x + SHIFT[0], y, z + SHIFT[1]);
  return [LAY.ox + v[0] * LAY.s, LAY.oy - v[1] * LAY.s, v[2]];
}
const cellW = (c) => LAY.x0 + c * SX;
const cellZ = (r) => LAY.z0 + r * SZ;

/** Where a seat's sprite is centred: long seats span several cells. */
function seatCentre(b) {
  const n = (b.len - 1) / 2;
  return b.dir & 1 ? [cellW(b.c), cellZ(b.r) + n * SZ]
                   : [cellW(b.c) + n * SX, cellZ(b.r)];
}
const seatFrame = b => "s" + b.len + "_" + b.dir + "_" + (SPRITE[colName(b.colour)] || "grey");

/** How many places share one cell: 1 for the binary levels, 2-4 for 1.63.1. */
const packing = b => b.cap / b.len;
/** Where place k sits, in world units. Places that share a cell sit side by side
    inside it, spread along the seat's own axis so a bench still reads as a bench. */
function placeAt(b, k) {
  const [c, r] = placeCell(b, k), per = packing(b);
  if (per <= 1) return [cellW(c), cellZ(r)];
  const off = ((k % per) - (per - 1) / 2) / per;
  return b.dir & 1 ? [cellW(c), cellZ(r) + off * SZ]
                   : [cellW(c) + off * SX, cellZ(r)];
}
const riderFrame = (b, ci) => "r" + b.dir + "_" + (SPRITE[colName(ci)] || "grey");

/** Frames carry their own size and origin: [x, y, w, h, pivotX, pivotY]. */
function blit(frame, wx, wy, wz, alpha, scale) {
  const f = META.frames[frame]; if (!f) return;
  const [px, py] = P(wx, wy, wz);
  const k = LAY.s / META.scale * (scale == null ? 1 : scale);
  ctx.globalAlpha = alpha == null ? 1 : alpha;
  ctx.drawImage(atlas, f[0], f[1], f[2], f[3],
                px - f[4] * k, py - f[5] * k, f[2] * k, f[3] * k);
  ctx.globalAlpha = 1;
}
/** One frame of the walk cycle: facing d/r/u/l, phase 0-3. */
function blitWalk(colour, facing, phase, wx, wy, wz) {
  const f = WMETA.frames["w" + facing + phase + "_" + colour];
  if (!f) return blit("idle_" + colour, wx, wy, wz, 1);
  const [px, py] = P(wx, wy, wz);
  const k = LAY.s / WMETA.scale * .74;
  ctx.drawImage(walkAtlas, f[0], f[1], WMETA.tile, WMETA.tile,
                px - WMETA.pivot[0] * k, py - WMETA.pivot[1] * k,
                WMETA.tile * k, WMETA.tile * k);
}

function quad(pts, fill) {
  ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
}
function tileQuad(c, r, y) {
  return [P(cellW(c) - SX / 2, y, cellZ(r) - SZ / 2), P(cellW(c) + SX / 2, y, cellZ(r) - SZ / 2),
          P(cellW(c) + SX / 2, y, cellZ(r) + SZ / 2), P(cellW(c) - SX / 2, y, cellZ(r) + SZ / 2)];
}
function shadow(wx, wz, rx) {
  const [px, py] = P(wx, 0, wz);
  ctx.save(); ctx.globalAlpha = .16; ctx.fillStyle = "#12203a";
  ctx.beginPath(); ctx.ellipse(px, py, rx * LAY.s, rx * LAY.s * .42, 0, 0, Math.PI * 2);
  ctx.fill(); ctx.restore();
}

/* ---------------- the blockers ----------------
   Seat colour 12 is not a colour. It stands on the decoded boards 508 times and
   appears in a queue NOT ONCE, and the decode's own header puts passenger
   colours at 1..8 - so nobody can ever sit in one. They are movable obstacles: a
   wall to be shuffled out of the way, and on two boards a full nine of them run
   down the middle column.

   ⚠ Drawn as a crate, not as a seat. Through the seat sprite they came out in
   the palette's blue, all but indistinguishable from a sky seat, so those two
   boards read as nine seats that could not be filled - and because every level's
   usable places match its queue exactly, with nothing spare, a seat that cannot
   be used reads as a seat that is missing. Nothing about how they behave changes
   here: `accepts` already turns every passenger away, since no passenger is ever
   colour 12. This is what they look like and nothing else. */
const BLOCK = 12;
const isBlock = b => b.colour === BLOCK;

const CRATE = { face: "#7c6145", top: "#9d7f5d", edge: "#3d2f22", strap: "#5c4732" };

/** A crate standing in one cell.

    ⚠ Two faces, not six. The camera's yaw is zero, so a wall at a constant x is
    seen exactly edge-on and projects to a line of no width - drawing the sides
    puts nothing on the screen but a seam. The front and the lid are the whole
    box, which is the same pair of faces the seat sprites were baked with. */
function drawBlock(wx, wz, alpha) {
  const a = SX * .37, d = SZ * .37, h = .52;
  ctx.save();
  ctx.globalAlpha = alpha == null ? 1 : alpha;
  ctx.lineJoin = "round"; ctx.lineCap = "round";
  ctx.strokeStyle = CRATE.edge;
  ctx.lineWidth = Math.max(1, LAY.s * .026);
  const face = (pts, fill) => {
    ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); ctx.stroke();
  };
  face([P(wx - a, 0, wz + d), P(wx + a, 0, wz + d),
        P(wx + a, h, wz + d), P(wx - a, h, wz + d)], CRATE.face);
  face([P(wx - a, h, wz - d), P(wx + a, h, wz - d),
        P(wx + a, h, wz + d), P(wx - a, h, wz + d)], CRATE.top);
  // the straps across the lid: what says crate rather than plinth
  ctx.strokeStyle = CRATE.strap;
  ctx.lineWidth = Math.max(1, LAY.s * .045);
  const c = [P(wx - a, h, wz - d), P(wx + a, h, wz - d),
             P(wx + a, h, wz + d), P(wx - a, h, wz + d)];
  ctx.beginPath();
  ctx.moveTo(c[0][0], c[0][1]); ctx.lineTo(c[2][0], c[2][1]);
  ctx.moveTo(c[1][0], c[1][1]); ctx.lineTo(c[3][0], c[3][1]);
  ctx.stroke();
  ctx.restore();
}

/** A seat, or a crate where the board carries one instead. */
function paintPiece(b, wx, wz, alpha) {
  if (isBlock(b)) return drawBlock(wx, wz, alpha);
  if (HARD && RICH) seatSheen(b, wx, wz, alpha);
  const per = packing(b);
  if (per <= 1) {
    blit(seatFrame(b), wx, 0, wz, alpha);
    return;
  }
  // A bench that covers one cell is drawn as its own places, side by side and
  // scaled to fit, rather than as one wide cushion that would cover its
  // neighbours. There is no atlas frame for a four-seater, and this needs none.
  for (let i = 0; i < per; i++) {
    const off = (i - (per - 1) / 2) / per;
    blit(seatFrame(b), wx + (b.dir & 1 ? 0 : off * SX), 0,
         wz + (b.dir & 1 ? off * SZ : 0), alpha, 1 / per);
  }
}

/* ---------------- the room ----------------
   The editor draws the board flat, because what it is for is reading the level
   data. The game draws a carriage around it: walls with real thickness, windows
   along the far side, a lit doorway with a step, and a rail where the queue
   waits. Same grid underneath - only the dressing differs.                    */
let RICH = false;
let BG = null;          // a painted room to use instead of the procedural one
let THEME = "station";  // any key of THEMES, below
let MOVIE = null;       // the still showing on the cinema screen
let NOW = 0;            // seconds, fed by the shell, for anything that moves

/* ---------------- the finale ----------------
   The beat between the last passenger sitting down and the result card, played
   out in the room itself: the train pulls out, the film starts, the teacher
   turns to the board. Each theme owns its own ending, the same way it owns its
   own outside - see THEMES, below.

   ⚠ Kept, not cleared, when the clock runs out. The card that follows dims the
   board rather than covering it, so an ending that snapped back to the opening
   frame would be seen doing it through the dim. FIN stays at f = 1 until the
   next board loads.

   `SHIFT` is the one ending that moves the room: a world offset every point of
   the carriage and its contents is drawn at. The ground outside is drawn with
   it zeroed, because a platform that leaves with the train is no departure. */
let FIN = null;            // { t0, ms, f } from the win until the next board loads
let SHIFT = [0, 0];        // world offset the carriage and its contents are drawn at
let ROOME = null;          // drawRoom's geometry, kept for the stage drawn over the board
let SCREEN = null;         // the cinema sheet's box on the canvas, from screenWash

const clamp01 = t => t < 0 ? 0 : t > 1 ? 1 : t;
const ease = t => { t = clamp01(t); return t * t * (3 - 2 * t); };
/** 0 before `a`, 1 after `b`, eased in between. */
const span = (f, a, b) => ease((f - a) / (b - a));

/** Play the room's ending over the next `ms`. Redraws itself; stops on its own,
    or the moment another board is loaded under it. */
function finale(ms) {
  if (!S) return;
  const g = S;
  FIN = { t0: performance.now(), ms, f: 0 };
  const step = () => {
    if (S !== g || !FIN) return;          // a new board has taken over
    draw();
    if (FIN.f < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/** How high a seated passenger is bounced by the win: a wave that runs across
    the seats, column by column, so a full house reads as a crowd rather than
    as one piston. Per-theme amplitude - a class does not do a Mexican wave. */
function cheerLift(c, r) {
  if (!FIN || FIN.f < .05) return 0;
  const amp = themeNow().cheer || 0;
  const w = Math.sin(Math.PI * 2 * (FIN.f * 2.4 - c * .11 - r * .05));
  return Math.max(0, w) * amp;
}

const ROOM = {
  ground: "#7e8288", ballastA: "#888c92", ballastB: "#6d7177",
  sleeper: "#6a6054", sleeperLip: "#7b7164",
  rail: "#c3c7cd", railLip: "#8b9098",
  platform: "#bcb5a7", platformLip: "#a0977f", platformEdge: "#8e856f",
  safety: "#e8c33a", tactile: "#a89b7d",
  bench: "#b0763e", benchLip: "#8c5a2c", case1: "#3f6ea8", case2: "#b4483f", lamp: "#6b7280",
  floorA: "#e9e4d8", floorB: "#d4cdbd", grout: "#bdb5a3",
  livery: "#f8bf1a", liveryLip: "#c9910f", liveryTop: "#ffd75a",
  trim: "#d8452c", post: "#8c6a12",
  glass: "#c6e8f6", glassBar: "#9ecfe3",
  mat: "#f6e2a8",
};

/** Gravel, drawn once into a tile and repeated in screen space. Chippings as
    individual world-space quads came to nearly two thousand fills a frame, and
    at that size they read as a checkerboard rather than as stones. */
let BALLAST = null;
function ballast() {
  if (BALLAST) return BALLAST;
  const t = document.createElement("canvas");
  t.width = t.height = 96;
  const c = t.getContext("2d");
  c.fillStyle = ROOM.ground; c.fillRect(0, 0, 96, 96);
  let seed = 1;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  for (let i = 0; i < 620; i++) {
    c.fillStyle = rnd() < .5 ? ROOM.ballastA : ROOM.ballastB;
    c.beginPath(); c.arc(rnd() * 96, rnd() * 96, .8 + rnd() * 1.7, 0, 7); c.fill();
  }
  BALLAST = ctx.createPattern(t, "repeat");
  return BALLAST;
}

/** A flat quad in world space, given two opposite corners at height y. */
const slab = (x0, z0, x1, z1, y, fill) =>
  quad([P(x0, y, z0), P(x1, y, z0), P(x1, y, z1), P(x0, y, z1)], fill);

/** The same rectangle as a path, for when it needs a gradient rather than a colour. */
function slabPath(x0, z0, x1, z1, y) {
  const c = [P(x0, y, z0), P(x1, y, z0), P(x1, y, z1), P(x0, y, z1)];
  ctx.beginPath(); ctx.moveTo(c[0][0], c[0][1]);
  for (let i = 1; i < 4; i++) ctx.lineTo(c[i][0], c[i][1]);
  ctx.closePath();
  return c;
}

/* One brown, told apart only by how light it is. The red trim, the two-tone
   carpet and the blue aisle lights were four hues fighting the one picture that
   is meant to carry colour in this room. */
const CINEMA = {
  outside: "#221a17",
  wall: "#3a2c26", wallLip: "#46362e", trim: "#2a201c", grout: "#241c19",
  carpetA: "#332721", carpetB: "#2d221d",
  mask: "#140f0d",
};

/** What is on the screen. A still, lit by a projector. It used to push in and
    drift, which read as the room moving rather than a film playing and pulled the
    eye off the board. It hangs still now. With no still loaded it falls back to
    washes of light, which is at least the right colour. */
function screenWash(x0, z0, x1, z1) {
  const c = slabPath(x0, z0, x1, z1, .02);
  const L = Math.min(...c.map(p => p[0])), R = Math.max(...c.map(p => p[0]));
  const T = Math.min(...c.map(p => p[1])), B = Math.max(...c.map(p => p[1]));
  const W = R - L, H = B - T;
  ctx.save(); ctx.clip();
  if (MOVIE && MOVIE.complete && MOVIE.naturalWidth) {
    // cover-fit, centred, and left alone
    const k = Math.max(W / MOVIE.naturalWidth, H / MOVIE.naturalHeight);
    const iw = MOVIE.naturalWidth * k, ih = MOVIE.naturalHeight * k;
    ctx.drawImage(MOVIE, L + (W - iw) / 2, T + (H - ih) / 2, iw, ih);
  } else {
    const base = ctx.createLinearGradient(L, T, L, B);
    base.addColorStop(0, "#3d4a63"); base.addColorStop(1, "#1d2330");
    ctx.fillStyle = base; ctx.fillRect(L, T, W, H);
  }
  // the beam falls off towards the edges of the sheet
  const vig = ctx.createRadialGradient(L + W / 2, T + H / 2, H * .25,
                                       L + W / 2, T + H / 2, Math.max(W, H) * .62);
  vig.addColorStop(0, "rgba(0,0,0,0)"); vig.addColorStop(1, "rgba(0,0,0,.45)");
  ctx.fillStyle = vig; ctx.fillRect(L, T, W, H);
  ctx.restore();
  SCREEN = [T, B, L, R];
  return SCREEN;
}

function drawCinema(E) {
  const { x0, x1, z0, T, gx0, gx1, gz0, gz1 } = E;
  ctx.fillStyle = CINEMA.wall; ctx.fillRect(0, 0, cv.width, cv.height);
  slab(gx0, gz0, gx1, gz1, -.05, CINEMA.outside);

  // the screen, beyond the far wall, with its masking border
  const sx0 = x0 + SX * .10, sx1 = x1 - SX * .10;
  const sz1 = z0 - T * .95, sz0 = sz1 - SZ * 2.15;
  slab(sx0 - .2, sz0 - .2, sx1 + .2, sz1 + .2, .01, CINEMA.mask);
  const [scrT, scrB, sxL, sxR] = screenWash(sx0, sz0, sx1, sz1);

  // Its light falling into the room. This used to be a band across the full width
  // of the canvas, which put a hard-edged lighter rectangle over half the screen
  // with nothing to explain it. A soft pool under the sheet does the same job and
  // has no edges to notice.
  const cx = (sxL + sxR) / 2, w = sxR - sxL;
  const glow = ctx.createRadialGradient(cx, scrB, w * .03, cx, scrB, w * .48);
  glow.addColorStop(0, "rgba(226,196,168,.15)");
  glow.addColorStop(1, "rgba(226,196,168,0)");
  ctx.save(); ctx.fillStyle = glow;
  ctx.fillRect(cx - w * .5, scrB, w, w * .5); ctx.restore();
}

/* ===========================  THEMES  ===========================
   A theme is three things: how much headroom the frame leaves above the room,
   the colours the room itself is skinned in, and what gets drawn OUTSIDE it.
   The grid, the walls, the doorway and the door cut are shared - they have to
   line up with the board to the pixel, so no theme may move them. Adding one
   means a palette, an outside painter, and an entry in THEMES; nothing else in
   the engine needs to learn the name.                                        */

function drawStation(E) {
  const { x0, x1, z0, T, OX, gx0, gx1, gz0, gz1 } = E;

  ctx.fillStyle = ballast();
  ctx.fillRect(0, 0, cv.width, cv.height);

  // sleepers across the track, then the two rails running the length of it
  for (let z = gz0; z < gz1; z += SZ * .80) {
    slab(gx0, z, OX - SX * .18, z + SZ * .21, -.042, ROOM.sleeper);
    slab(gx0, z, OX - SX * .18, z + SZ * .05, -.040, ROOM.sleeperLip);
  }
  const mid = (x0 + x1) / 2, gauge = (x1 - x0) * .30;
  for (const rx of [mid - gauge, mid + gauge]) {
    slab(rx - .11, gz0, rx + .11, gz1, -.034, ROOM.railLip);
    slab(rx - .07, gz0, rx + .04, gz1, -.032, ROOM.rail);
  }

  // the platform: a dark edge where it drops to the track, then the deck
  slab(OX, gz0, gx1, gz1, -.030, ROOM.platformEdge);
  slab(OX + SX * .13, gz0, gx1, gz1, -.028, ROOM.platform);
  slab(OX + SX * .30, gz0, OX + SX * .42, gz1, -.026, ROOM.safety);
  for (let z = gz0; z < gz1; z += SZ * .34)   // the strip you feel underfoot
    slab(OX + SX * .50, z, OX + SX * .58, z + SZ * .17, -.026, ROOM.tactile);

  // The name board, so the place says what it is. Up past the far end of the
  // carriage, where nobody in the line ever stands, and level with the wall
  // top so it clears the HUD on a phone.
  // The party hangs its own, lit, in this spot - see partyStation.
  if (!HARD) nameBoard("STATION", OX + SX * .85, z0 - T * .2);
}

/** A sign on a post, drawn as a billboard in canvas space the way the sprites
    are: at this pitch a board stood up in world units would come out a quarter
    of a cell tall. */
function nameBoard(text, wx, wz) {
  const [px, py] = P(wx, 0, wz);
  const s = LAY.s;
  const size = Math.max(9, s * .26);
  ctx.save();
  ctx.font = '800 ' + size + 'px "Baloo 2", "Trebuchet MS", sans-serif';
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const w = ctx.measureText(text).width + size * 1.1, h = size * 1.5;
  const cy = py - s * .95;                     // the board's centre, up the post
  shadow(wx, wz, .14);
  ctx.strokeStyle = ROOM.post; ctx.lineCap = "round"; ctx.lineWidth = Math.max(2, s * .06);
  ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px, cy); ctx.stroke();
  const r = size * .35, L = px - w / 2, T = cy - h / 2;
  ctx.beginPath();
  ctx.moveTo(L + r, T); ctx.arcTo(L + w, T, L + w, T + h, r); ctx.arcTo(L + w, T + h, L, T + h, r);
  ctx.arcTo(L, T + h, L, T, r); ctx.arcTo(L, T, L + w, T, r); ctx.closePath();
  ctx.fillStyle = "#1d3f7a"; ctx.fill();
  ctx.strokeStyle = "#f3f6fb"; ctx.lineWidth = Math.max(1, s * .035); ctx.stroke();
  ctx.fillStyle = "#ffffff"; ctx.fillText(text, px, cy + size * .05);
  ctx.restore();
}

/* Terracing under a floodlit pitch. The grass is the one saturated thing in any
   of these rooms, so it is kept beyond the far wall, where no seat ever sits on
   it and it cannot fight the pieces for attention. */
const STADIUM = {
  night: "#2b3630", concourse: "#8b928c", nosing: "#c6b061", rail: "#aeb5b0",
  turfA: "#3f6d40", turfB: "#376237", line: "#e2e8df", track: "#8f4b36",
  wall: "#98a19a", wallLip: "#aab3ab", trim: "#6d7871", grout: "#69736d",
  deckA: "#bcc2bb", deckB: "#acb3ab",
};

function drawStadium(E) {
  const { z0, T, OX, gx0, gx1, gz0, gz1 } = E;
  ctx.fillStyle = STADIUM.night; ctx.fillRect(0, 0, cv.width, cv.height);
  slab(gx0, gz0, gx1, gz1, -.05, STADIUM.concourse);

  // The pitch, beyond the far wall. Depth compresses hard under this camera, so
  // the track is a thin band and the grass comes right up behind it: pushed out
  // to where a real track sits, the pitch shrank to a green line along the top.
  const tz1 = z0 - T * .6, tz0 = tz1 - SZ * .75;
  slab(gx0, gz0, gx1, tz0, -.046, STADIUM.turfA);
  // the mow runs AWAY from the camera. Banded across it instead, the stripes
  // stack up at the horizon and turn into one flat green.
  for (let x = gx0, i = 0; x < gx1; x += SX * 1.7, i++)
    if (i % 2) slab(x, gz0, Math.min(x + SX * 1.7, gx1), tz0, -.045, STADIUM.turfB);
  slab(gx0, tz0 - .10, gx1, tz0, -.044, STADIUM.line);
  slab(gx0, tz0, gx1, tz1, -.042, STADIUM.track);

  // The concourse, on the door side. The queue stands at OX + SX * 0.94, so
  // everything here starts outside that: dressing drawn under the people the
  // player is reading is just noise over the one thing they need to see.
  for (let z = gz0; z < gz1; z += SZ * 1.6)
    slab(OX + SX * 1.75, z, gx1, z + SZ * .08, -.040, STADIUM.nosing);
  slab(OX + SX * 1.62, gz0, OX + SX * 1.70, gz1, -.030, STADIUM.rail);
}

/* A seated tier facing a stage. Everything is near-black except the footlights,
   which is the point: the warm line along the stage front is the only thing in
   the room the eye is asked to find. */
const CONCERT = {
  dark: "#15181e", floor: "#1c2027",
  wall: "#2a303b", wallLip: "#39404e", trim: "#1f232b", grout: "#1a1e25",
  parqA: "#6a4a2f", parqB: "#5d4028",
  stage: "#14171c", stageLip: "#262c36", foot: "#ffc978",
  cable: "#6f747d", post: "#8b9099",
};

function drawConcert(E) {
  const { z0, T, OX, gx0, gx1, gz0, gz1 } = E;
  ctx.fillStyle = CONCERT.dark; ctx.fillRect(0, 0, cv.width, cv.height);
  slab(gx0, gz0, gx1, gz1, -.05, CONCERT.floor);

  // The stage: just beyond the far wall and only a couple of cells deep. Run
  // back to the far edge of the ground it flattens into a stripe, the same way
  // the stadium pitch does.
  const sz1 = z0 - T * .9, sz0 = sz1 - SZ * 2.4;
  const sx0 = gx0 + SX * 2.0, sx1 = gx1 - SX * 2.0;
  slab(sx0, sz0, sx1, sz1, -.030, CONCERT.stage);
  slab(sx0, sz1 - .14, sx1, sz1, -.028, CONCERT.stageLip);
  // One continuous line, not a row of lamps: at this size separate dashes read
  // as a painted road marking rather than as light.
  slab(sx0 + SX * .2, sz1 - .06, sx1 - SX * .2, sz1 + .02, -.026, CONCERT.foot);
  // the spill it throws forward, as two washes rather than one band: the pit
  // floor is flat colour, so a single hard edge would be the only edge in it
  slab(sx0, sz1, sx1, sz1 + SZ * .45, -.024, "rgba(255,201,120,.11)");
  slab(sx0, sz1, sx1, sz1 + SZ * 1.00, -.023, "rgba(255,201,120,.05)");

  // the walkway, kept outside the queue lane at OX + SX * 0.94
  slab(OX + SX * 1.70, gz0, OX + SX * 1.86, gz1, -.034, CONCERT.cable);
  for (let z = gz0; z < gz1; z += SZ * 2.2)
    slab(OX + SX * 2.25, z, OX + SX * 2.42, z + SZ * .22, -.030, CONCERT.post);
}

/* Desks in a classroom. The one theme with daylight in it, which is why the
   board is so dark: with nothing heavy at the front, the room reads washed out
   under a camera this close to overhead. */
const CLASSROOM = {
  lino: "#c4b99f",
  wall: "#d6cdb6", wallLip: "#e7e0cd", trim: "#a4967a", grout: "#b0a58b",
  linoA: "#e8e1cd", linoB: "#dcd4be",
  board: "#2f4a3b", boardTrim: "#8a6f47", tray: "#b5975f", shelf: "#c9a86f",
  locker: "#4e7d78", lockerLip: "#5f918b", sun: "rgba(255,238,180,.26)",
};

function drawClassroom(E) {
  const { x0, x1, z0, T, OX, gx0, gx1, gz0, gz1 } = E;
  ctx.fillStyle = CLASSROOM.lino; ctx.fillRect(0, 0, cv.width, cv.height);
  slab(gx0, gz0, gx1, gz1, -.05, CLASSROOM.lino);

  // the board at the front of the class, framed, chalk tray along the bottom
  const bz1 = z0 - T * .95, bz0 = bz1 - SZ * 1.5;
  slab(x0 - .30, bz0 - .18, x1 + .30, bz1 + .18, .010, CLASSROOM.boardTrim);
  slab(x0, bz0, x1, bz1, .012, CLASSROOM.board);
  slab(x0, bz1 - .10, x1, bz1, .014, CLASSROOM.tray);
  // a low bookshelf beside it, so the front is not one flat rectangle
  slab(gx0 + SX * 1.2, bz0 + SZ * .3, x0 - SX * .4, bz1, -.020, CLASSROOM.shelf);

  // cubbies down the door side, outside the queue lane at OX + SX * 0.94, and
  // muted: teal at full strength out-shouted the seats it sits next to
  for (let z = gz0; z < gz1; z += SZ * 1.4) {
    slab(OX + SX * 1.75, z, OX + SX * 2.45, z + SZ * 1.1, -.030, CLASSROOM.locker);
    slab(OX + SX * 1.75, z, OX + SX * 2.45, z + SZ * .14, -.028, CLASSROOM.lockerLip);
  }
  slab(OX + SX * 2.75, gz0 + SZ * 3, gx1, gz0 + SZ * 8, -.034, CLASSROOM.sun);
}

/* ===========================  ENDINGS  ===========================
   One per theme, a second and a half long, drawn in three passes so each piece
   lands in the right layer:
     "back"  - right after the outside, before the walls: anything beyond the
               far wall, where the walls occlude its feet the way they should
     "room"  - the end of drawRoom, with the carriage: the door leaf
     "over"  - the end of draw(), over the seats and passengers: light in the air
   `f` runs 0..1 over the beat. Everything here is a function of f and nothing
   else, so a dropped frame skips ahead instead of stalling the ending.       */

/** The train leaves. The doors close over the first third, then it pulls out
    along the track - away from the camera, up the screen - gathering speed. The
    platform stays where it is: see SHIFT. */
function finStation(E, f, stage) {
  if (stage !== "room") return;
  const { x1, OX, dz0, dz1, H, SKIN } = E;
  const k = span(f, .04, .34);
  if (k <= 0) return;
  const zEnd = dz0 + (dz1 - dz0) * k;
  slab(x1 - .02, dz0, OX + .02, zEnd, H + .005, SKIN.wall);               // the leaf
  slab(x1 - .02, Math.max(dz0, zEnd - .09), OX + .02, zEnd, H + .006, SKIN.trim);
}
const trainOut = f => {
  // Gone by .92, not 1: the card is timed to f = 1, and a frame drawn a few
  // milliseconds short of it still had the tail's edge in shot under the card.
  const k = clamp01((f - .40) / .52);
  if (k <= 0) return [0, 0];
  // ⚠ Off the top of the canvas entirely, not a fixed distance. At a fixed 4.6
  // cells the tail of a tall board was still in shot when the card came up,
  // and a card over a carriage with its tail showing reads as a train that
  // stalled. Measured on the canvas, so it holds for any board and any window.
  SHIFT = [0, 0];
  const near = P(0, 0, cellZ(S.H - 1 + .5) + .9 + .5)[1];   // the near shadow edge, on screen
  const perZ = -BZ[1] * LAY.s;                               // canvas px per unit of z
  const gone = Math.min(-SZ * 4.6, (-LAY.s * .8 - near) / perZ);
  return [0, gone * k * k];
};

/** The film starts: a countdown leader on the sheet, then the still comes up
    with a flash and settles with a flicker, and the projector beam crosses the
    room. The audience does no more than shift in their seats. */
function finCinema(E, f, stage) {
  if (!SCREEN) return;
  const [T, B, L, R] = SCREEN, W = R - L, Hh = B - T;
  if (stage === "back") {
    ctx.save();
    ctx.beginPath(); ctx.rect(L, T, W, Hh); ctx.clip();
    if (f < .5) {
      // the leader: 3, 2, 1, each with a sweep of the hand
      const n = 3 - Math.floor(f * 6), sweep = (f * 6) % 1;
      const cx = L + W / 2, cy = T + Hh / 2, rad = Math.min(W, Hh) * .40;
      ctx.fillStyle = "#3b3b37"; ctx.fillRect(L, T, W, Hh);
      ctx.fillStyle = "rgba(255,255,255,.16)";
      ctx.beginPath(); ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, rad, -Math.PI / 2, -Math.PI / 2 + sweep * Math.PI * 2); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "rgba(255,255,255,.55)"; ctx.lineWidth = Math.max(1, rad * .045);
      ctx.beginPath(); ctx.arc(cx, cy, rad, 0, Math.PI * 2); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(L, cy); ctx.lineTo(R, cy); ctx.moveTo(cx, T); ctx.lineTo(cx, B); ctx.stroke();
      ctx.fillStyle = "#f2f2ee"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.font = "800 " + rad * 1.35 + 'px "Baloo 2", "Trebuchet MS", sans-serif';
      ctx.fillText(String(Math.max(1, n)), cx, cy + rad * .06);
    } else {
      // the picture, already on the sheet under this: a flash off it, then a flicker
      const a = (1 - span(f, .5, .70)) * .85 + (f < .92 ? Math.random() * .05 : 0);
      ctx.fillStyle = "rgba(255,250,235," + a + ")"; ctx.fillRect(L, T, W, Hh);
    }
    ctx.restore();
  } else if (stage === "over") {
    // the beam, from a projector behind the back row up to the sheet
    const a = span(f, .5, .78) * .13;
    if (a <= 0) return;
    const ox = cv.width / 2, oy = cv.height * 1.08;
    const gr = ctx.createLinearGradient(ox, oy, ox, T);
    gr.addColorStop(0, "rgba(255,244,220,0)"); gr.addColorStop(1, "rgba(255,244,220," + a + ")");
    ctx.save(); ctx.fillStyle = gr;
    ctx.beginPath(); ctx.moveTo(ox - 8, oy); ctx.lineTo(L, T); ctx.lineTo(R, T); ctx.lineTo(ox + 8, oy);
    ctx.closePath(); ctx.fill(); ctx.restore();
  }
}

/** Kick-off. One player runs onto the ball and strikes it, the other runs in to
    meet it, and both throw their arms up when it lands. Out on the pitch, past
    the far wall, so the wall hides their feet the way the turf's edge should. */
function finStadium(E, f, stage) {
  if (stage !== "back") return;
  const { x0, x1, z0, T } = E;
  const mid = (x0 + x1) / 2;
  const tz0 = z0 - T * .6 - SZ * .75;          // the near touchline, as drawStadium placed it
  // ⚠ Close behind the touchline, and a short run. The frame leaves the pitch
  // only a couple of cells deep and the phone only a couple of cells either
  // side of the room; further out, the players played half off the canvas.
  const pz = tz0 - SZ * .55;                   // the line the play runs along
  const run = SX * 1.7, close = SX * .8;
  const a = span(f, .02, .42), b = span(f, .44, .84), flight = span(f, .44, .84);
  const ax = mid - run - SX * .5 + run * a;    // stops half a cell short: that is the kick
  const bx = mid + run + close - close * b;
  const ballX = mid + run * flight, ballY = Math.sin(flight * Math.PI) * .9;
  const phaseOf = d => Math.floor(d / STRIDE) % WMETA.phases;
  shadow(ax, pz, .3); shadow(bx, pz, .3);
  if (f >= .86) { blit("cheer_red", ax, 0, pz, 1); blit("cheer_sky", bx, 0, pz, 1); }
  else {
    blitWalk("red", "r", a > 0 && a < 1 ? phaseOf(run * a) : 0, ax, 0, pz);
    blitWalk("sky", "l", b > 0 && b < 1 ? phaseOf(close * b) : 0, bx, 0, pz);
  }
  shadow(ballX, pz, .13);
  const [px, py] = P(ballX, ballY + .13, pz);
  ctx.save(); ctx.fillStyle = "#f4f4f2"; ctx.strokeStyle = "#2b2f33";
  ctx.lineWidth = Math.max(1, LAY.s * .02);
  ctx.beginPath(); ctx.arc(px, py, LAY.s * .13, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.restore();
}

/** The show starts. Three colours of light swing across the boards, the
    footlights pulse, and the act bounces centre stage with their arms going up
    on every other beat. */
function finConcert(E, f, stage) {
  if (stage !== "back") return;
  const { x0, x1, z0, T, gx0, gx1 } = E;
  const sz1 = z0 - T * .9, sz0 = sz1 - SZ * 2.4;    // the stage, as drawConcert placed it
  const sx0 = gx0 + SX * 2.0, sx1 = gx1 - SX * 2.0;
  const mid = (x0 + x1) / 2, sz = (sz0 + sz1) / 2;
  const swing = (x1 - x0) * .55 + SX;
  for (const [rgb, ph] of [["255,80,200", 0], ["80,200,255", 2.1], ["255,220,120", 4.2]]) {
    const x = mid + Math.sin(f * Math.PI * 1.8 + ph) * swing;
    const [px, py] = P(x, .02, sz);
    const r = LAY.s * SX * .95;
    ctx.save(); ctx.translate(px, py); ctx.scale(1, .42);
    const gr = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
    gr.addColorStop(0, "rgba(" + rgb + ",.45)"); gr.addColorStop(1, "rgba(" + rgb + ",0)");
    ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }
  const pulse = .22 + .22 * Math.sin(f * Math.PI * 8);
  slab(sx0 + SX * .2, sz1 - .06, sx1 - SX * .2, sz1 + .02, -.025, "rgba(255,255,255," + pulse + ")");
  const hop = Math.abs(Math.sin(f * Math.PI * 4)) * .16;
  const az = sz1 - SZ * .8;
  shadow(mid, az, .3);
  blit((Math.floor(f * 8) % 2 ? "cheer_" : "idle_") + "purple", mid, hop, az, 1);
}

/** Class over. The teacher, beside the board, points the class through what is
    written up as it appears - chalk, left to right, under the pointer. */
function finClassroom(E, f, stage) {
  if (stage !== "back") return;
  const { x0, x1, z0, T } = E;
  const bz1 = z0 - T * .95, bz0 = bz1 - SZ * 1.5;     // the board, as drawClassroom placed it
  const room = (x1 - x0) * LAY.s;
  const msg = "WELL DONE!";
  // fitted to the board, and set a little right of centre to clear the teacher
  const [bx, by] = P((x0 + x1) / 2 + (x1 - x0) * .07, .014, (bz0 + bz1) / 2);
  let size = Math.max(8, room * .12);
  ctx.save();
  const font = s => '800 ' + s + 'px "Baloo 2", "Trebuchet MS", sans-serif';
  ctx.font = font(size);
  let w = ctx.measureText(msg).width;
  if (w > room * .58) { size *= room * .58 / w; ctx.font = font(size); w = ctx.measureText(msg).width; }
  const reveal = span(f, .10, .74);
  const left = bx - w / 2;
  ctx.beginPath(); ctx.rect(left - size * .1, by - size, w * reveal + size * .1, size * 2); ctx.clip();
  ctx.textAlign = "left"; ctx.textBaseline = "middle";
  ctx.fillStyle = "rgba(255,255,255,.88)";
  ctx.fillText(msg, left, by);
  ctx.restore();

  // the teacher: one of the atlas figures, with a book and a pointer drawn on
  const tx = x0 + SX * .45, tz = z0 - T - SZ * .30;   // inside the board's frame
  const k = LAY.s / META.scale;
  const [px, py] = P(tx, 0, tz);
  shadow(tx, tz, .3);
  blit("idle_grey", tx, 0, tz, 1);
  ctx.save();
  // the book, in the near hand
  ctx.translate(px - 40 * k, py - 4 * k); ctx.rotate(-.28);
  ctx.fillStyle = "#c9432f"; ctx.fillRect(-13 * k, -9 * k, 26 * k, 20 * k);
  ctx.fillStyle = "#f4ecd8"; ctx.fillRect(8 * k, -7 * k, 4 * k, 16 * k);
  ctx.restore();
  // the pointer, from the far hand to wherever the chalk has got to
  const tipX = left + w * Math.max(.02, reveal), tipY = by + size * .35;
  ctx.save();
  ctx.strokeStyle = "#8b5a2b"; ctx.lineCap = "round"; ctx.lineWidth = Math.max(2, 4 * k);
  ctx.beginPath(); ctx.moveTo(px + 42 * k, py - 6 * k); ctx.lineTo(tipX, tipY); ctx.stroke();
  ctx.fillStyle = "#2b2f33"; ctx.beginPath(); ctx.arc(tipX, tipY, Math.max(2, 3.5 * k), 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

/* head  - fraction of the canvas left empty above the room, so that whatever a
           theme puts beyond the far wall has somewhere to go
   finale - the ending, see ENDINGS above; cheer - how high the seated bounce;
   shift  - the room's own movement during the ending, as a world offset of f
   page  - what the shell paints behind the canvas, for the strip it never covers
   plate - true if a ?bg= plate may stand in for this theme's outside          */
const THEMES = {
  station: {
    head: .09, plate: true, outside: drawStation,
    finale: finStation, shift: trainOut, cheer: .12,
    skin: { wall: ROOM.livery, trim: ROOM.trim, top: ROOM.liveryTop, lip: ROOM.liveryLip,
            fa: ROOM.floorA, fb: ROOM.floorB, grout: ROOM.grout, glass: ROOM.glass,
            door: ROOM.mat },
  },
  cinema: {
    head: .27, page: CINEMA.outside, outside: drawCinema, finale: finCinema, cheer: .05,
    skin: { wall: CINEMA.wall, trim: CINEMA.trim, top: CINEMA.wallLip, lip: CINEMA.grout,
            fa: CINEMA.carpetA, fb: CINEMA.carpetB, grout: CINEMA.grout, glass: null,
            door: CINEMA.wallLip },
  },
  stadium: {
    head: .22, page: STADIUM.night, outside: drawStadium, finale: finStadium, cheer: .20,
    skin: { wall: STADIUM.wall, trim: STADIUM.trim, top: STADIUM.wallLip, lip: STADIUM.grout,
            fa: STADIUM.deckA, fb: STADIUM.deckB, grout: STADIUM.grout, glass: null,
            door: STADIUM.nosing },
  },
  concert: {
    head: .24, page: CONCERT.dark, outside: drawConcert, finale: finConcert, cheer: .18,
    skin: { wall: CONCERT.wall, trim: CONCERT.trim, top: CONCERT.wallLip, lip: CONCERT.grout,
            fa: CONCERT.parqA, fb: CONCERT.parqB, grout: CONCERT.grout, glass: null,
            door: CONCERT.stageLip },
  },
  classroom: {
    head: .20, page: CLASSROOM.lino, outside: drawClassroom, finale: finClassroom, cheer: .08,
    skin: { wall: CLASSROOM.wall, trim: CLASSROOM.trim, top: CLASSROOM.wallLip,
            lip: CLASSROOM.grout, fa: CLASSROOM.linoA, fb: CLASSROOM.linoB,
            grout: CLASSROOM.grout, glass: null, door: CLASSROOM.tray },
  },
};

/* ===========================  THE PARTY ROOMS  ===========================
   The game marks 118 of its 600 boards `difficultLevel` 1 or 2, and the HUD
   already says so twice - a chip in the topbar and a card on the way in. This
   is the third telling, and the only one the player reads without being asked
   to: the SAME room, thrown a party. A tint over the whole place, bunting and a
   lit sign over the far wall, and colour on the ground in front of the door.

   A party is a PATCH on a theme, never a theme of its own. The walls, the grid,
   the doorway and the queue lane still have to line up to the pixel, so a patch
   may do exactly three things: repaint the skin, ask for more headroom, and
   paint over the ground the theme has already laid. It may not move anything.

   ⚠ Where the dressing goes is decided by the phone, not by the room. On a
   portrait frame `frame()` leaves .04 of the canvas to the left of the walls and
   nothing at all to the right past the queue - so the sides are the one place a
   party must NOT be put, and everything that has to be seen goes above the far
   wall or on the near ground below the door. Side dressing is drawn as well,
   and is a gift to the desktop frame, which has a quarter of the canvas either
   side; nothing on a phone depends on it.

   ⚠ Nothing here is a function of time. The game redraws on taps, not on a
   clock - see tick() in the shell - so a light written as a function of NOW
   would sit frozen between moves and lurch on the next one. Every beam, spark
   and scatter below is fixed, and seeded so it is the same fixed thing on every
   redraw of the same board.                                                   */

let HARD = 0;              // 0 ordinary, 1 hard, 2 super hard - set by the shell

/* One set of party colours for all five rooms, so a marked level reads the same
   whichever room it lands in. They are deliberately NOT the seat palette: these
   sit behind and beside the pieces, and a bunting flag in the sky blue of a seat
   is one more blue for the player to tell apart. */
const FEST = ["#ff4d84", "#ffc93c", "#4ecbff", "#a879ff", "#5be6a2"];

/** A scatter that comes out the same every frame. `Math.random` in a painter
    boils the confetti every time the board is redrawn, which is every tap. */
const seeded = n => () => (n = (n * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;

/** A tint over everything the room has drawn outside itself. It is the cheapest
    thing here and it does the most work: on a phone most of the dressing is off
    the sides of the frame, and this is what still says at a glance that this is
    not the room the last level was played in.

    Strongest at the head and foot of the canvas and weakest across the middle,
    where the board is. Flat, it dulled the one bright room - a lilac at even
    strength over the classroom's tan came out the colour of wet cardboard. */
function partyWash(rgb, edge, mid) {
  const g = ctx.createLinearGradient(0, 0, 0, cv.height);
  g.addColorStop(0, "rgba(" + rgb + "," + edge + ")");
  g.addColorStop(.38, "rgba(" + rgb + "," + mid + ")");
  g.addColorStop(.62, "rgba(" + rgb + "," + mid + ")");
  g.addColorStop(1, "rgba(" + rgb + "," + edge + ")");
  ctx.save(); ctx.fillStyle = g;
  ctx.fillRect(0, 0, cv.width, cv.height); ctx.restore();
}

/** A string of flags between two points on the ground, hung at height `y` with
    a sag. Canvas space, like nameBoard: at this pitch a flag stood up in world
    units comes out a couple of pixels tall. */
function bunting(x0, z0, x1, z1, y, n) {
  const a = P(x0, y, z0), b = P(x1, y, z1), s = LAY.s;
  const sag = s * .55;
  const at = t => [a[0] + (b[0] - a[0]) * t,
                   a[1] + (b[1] - a[1]) * t + Math.sin(Math.PI * t) * sag];
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,.45)";
  ctx.lineWidth = Math.max(1, s * .020);
  ctx.beginPath();
  for (let i = 0; i <= 32; i++) {
    const p = at(i / 32); i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]);
  }
  ctx.stroke();
  const w = s * .15, h = s * .26;
  for (let i = 0; i < n; i++) {
    const p = at((i + .5) / n);
    ctx.fillStyle = FEST[i % FEST.length];
    ctx.beginPath();
    ctx.moveTo(p[0] - w / 2, p[1]); ctx.lineTo(p[0] + w / 2, p[1]); ctx.lineTo(p[0], p[1] + h);
    ctx.closePath(); ctx.fill();
  }
  ctx.restore();
}

/* Five balloons and their strings, as offsets from the point they are tied to,
   in units of the cell size: [across, up, radius]. */
const BUNCH = [[-.30, -1.62, .19], [.04, -1.88, .22], [.36, -1.58, .18],
               [-.15, -1.28, .16], [.25, -1.25, .15]];

/** A cluster tied off at a point on the ground. Rises up the canvas, so it is
    only ever tied BEYOND the far wall: from anywhere nearer, the walls are
    drawn over it a moment later and the strings come out cut. */
function balloons(wx, wz, k) {
  const [px, py] = P(wx, 0, wz), s = LAY.s * (k || 1);
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,.30)";
  ctx.lineWidth = Math.max(1, s * .018);
  for (const [dx, dy] of BUNCH) {
    ctx.beginPath(); ctx.moveTo(px, py);
    ctx.quadraticCurveTo(px + dx * s * .35, py + dy * s * .55, px + dx * s, py + dy * s);
    ctx.stroke();
  }
  BUNCH.forEach(([dx, dy, r], i) => {
    ctx.fillStyle = FEST[i % FEST.length];
    ctx.beginPath();
    ctx.ellipse(px + dx * s, py + dy * s, r * s, r * s * 1.16, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,.34)";   // the highlight is what makes it round
    ctx.beginPath();
    ctx.ellipse(px + (dx - r * .34) * s, py + (dy - r * .46) * s,
                r * s * .26, r * s * .32, 0, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.restore();
}

/** Paper on the floor, over a box of ground. Kept OUTSIDE the room in every
    theme: on the tiles it would be one more thing on the surface the player is
    reading seats off.

    ⚠ `litter`, not `confetti`. The shell has a confetti() of its own for the
    results card and is concatenated AFTER the engine, so a function of that
    name here is hoisted over by the shell's and this painter draws nothing at
    all - silently, since both are perfectly good functions.  Every name in this
    file is shared with the shell; check one before adding it. */
function litter(x0, z0, x1, z1, y, n, seed) {
  const rnd = seeded(seed), s = LAY.s;
  ctx.save(); ctx.globalAlpha = .8;
  for (let i = 0; i < n; i++) {
    const [px, py] = P(x0 + rnd() * (x1 - x0), y, z0 + rnd() * (z1 - z0));
    ctx.save(); ctx.translate(px, py); ctx.rotate(rnd() * Math.PI);
    ctx.fillStyle = FEST[i % FEST.length];
    ctx.fillRect(-s * .11, -s * .042, s * .22, s * .085);
    ctx.restore();
  }
  ctx.restore();
}

/** A coloured wash on the ground, the way finConcert lights the stage. */
function lightPool(wx, wz, rgb, r, a) {
  const [px, py] = P(wx, .02, wz), R = LAY.s * r;
  ctx.save(); ctx.translate(px, py); ctx.scale(1, .42);
  const gr = ctx.createRadialGradient(0, 0, 0, 0, 0, R);
  gr.addColorStop(0, "rgba(" + rgb + "," + a + ")");
  gr.addColorStop(1, "rgba(" + rgb + ",0)");
  ctx.fillStyle = gr;
  ctx.beginPath(); ctx.arc(0, 0, R, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

/** A shaft of light standing up from a point, tilted off vertical, widening and
    fading as it goes. Run off the top of the canvas rather than to a fixed
    length: it is meant to leave the frame, and a beam that stops has a lamp at
    the wrong end.

    Drawn as strips with the alpha falling off across them, not as one wedge: a
    single filled triangle has two hard edges down the sides, and light has none
    - as one shape it read as a plank of wood leaning against the screen. */
function beam(wx, wz, tilt, rgb, a) {
  const [px, py] = P(wx, 0, wz), s = LAY.s;
  const len = cv.height * 1.15, N = 9;
  const tx = px + Math.sin(tilt) * len, ty = py - Math.cos(tilt) * len;
  const nx = Math.cos(tilt), ny = Math.sin(tilt);
  const w0 = s * .20, w1 = s * 1.9;
  ctx.save();
  for (let i = 0; i < N; i++) {
    const u0 = i / N - .5, u1 = (i + 1) / N - .5;
    const k = Math.max(0, 1 - Math.abs(u0 + u1));      // brightest down the middle
    const gr = ctx.createLinearGradient(px, py, tx, ty);
    gr.addColorStop(0, "rgba(" + rgb + "," + (a * k) + ")");
    gr.addColorStop(1, "rgba(" + rgb + ",0)");
    ctx.fillStyle = gr;
    ctx.beginPath();
    ctx.moveTo(px + nx * u0 * w0, py + ny * u0 * w0);
    ctx.lineTo(px + nx * u1 * w0, py + ny * u1 * w0);
    ctx.lineTo(tx + nx * u1 * w1, ty + ny * u1 * w1);
    ctx.lineTo(tx + nx * u0 * w1, ty + ny * u0 * w1);
    ctx.closePath(); ctx.fill();
  }
  ctx.restore();
}

/** A burst hung in the sky above a point. Still: see the warning at the top.

    ⚠ `lift` is in cell sizes, and a cell is bigger on a narrow board than on a
    wide one - so the same lift that cleared the topbar on a 7-wide board was
    drawn straight through the clock on a 4-wide one. Held below the head of the
    canvas whatever the arithmetic asks for. */
function firework(wx, wz, lift, col, n, seed) {
  const [px, py0] = P(wx, 0, wz), s = LAY.s;
  const R = s * .85, rnd = seeded(seed);
  const py = Math.max(py0 - s * lift, cv.height * .085 + R);
  ctx.save();
  const gl = ctx.createRadialGradient(px, py, 0, px, py, R * 1.25);
  gl.addColorStop(0, "rgba(255,255,255,.14)"); gl.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gl;
  ctx.beginPath(); ctx.arc(px, py, R * 1.25, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = col; ctx.lineCap = "round";
  ctx.lineWidth = Math.max(1, s * .022);
  for (let i = 0; i < n; i++) {
    const a = i / n * Math.PI * 2 + rnd() * .25, r = R * (.6 + rnd() * .4);
    const ex = px + Math.cos(a) * r, ey = py + Math.sin(a) * r * .82;
    ctx.globalAlpha = .45 + rnd() * .5;
    ctx.beginPath();
    ctx.moveTo(px + Math.cos(a) * r * .3, py + Math.sin(a) * r * .25);
    ctx.lineTo(ex, ey); ctx.stroke();
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.arc(ex, ey, Math.max(1, s * .025), 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

/** Gold posts with a rope slung between them, along a line on the ground. */
function velvetRope(x0, z0, x1, z1, n) {
  const s = LAY.s, tops = [];
  ctx.save();
  ctx.lineCap = "round";
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const [px, py] = P(x0 + (x1 - x0) * t, 0, z0 + (z1 - z0) * t);
    const ty = py - s * .40;
    tops.push([px, ty]);
    ctx.strokeStyle = "#d8b45a"; ctx.lineWidth = Math.max(2, s * .045);
    ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px, ty); ctx.stroke();
    ctx.fillStyle = "#f2d78d";
    ctx.beginPath(); ctx.arc(px, ty - s * .04, Math.max(1.5, s * .055), 0, Math.PI * 2); ctx.fill();
  }
  ctx.strokeStyle = "#8e1f2e"; ctx.lineWidth = Math.max(2, s * .05);
  for (let i = 0; i < n; i++) {
    const a = tops[i], b = tops[i + 1];
    ctx.beginPath(); ctx.moveTo(a[0], a[1]);
    ctx.quadraticCurveTo((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + s * .24, b[0], b[1]);
    ctx.stroke();
  }
  ctx.restore();
}

/** A rounded rectangle as a path, and the points to hang lamps on round it:
    evenly along the four straight runs, plus one on the outside of each corner.
    Returned rather than drawn, so the frame and its lamps are laid out once and
    used twice. */
function roundRect(l, t, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(l + r, t);
  ctx.arcTo(l + w, t, l + w, t + h, r);
  ctx.arcTo(l + w, t + h, l, t + h, r);
  ctx.arcTo(l, t + h, l, t, r);
  ctx.arcTo(l, t, l + w, t, r);
  ctx.closePath();
}
function ringPoints(l, t, w, h, r, gap) {
  const out = [];
  const runs = [[l + r, t, l + w - r, t], [l + w, t + r, l + w, t + h - r],
                [l + w - r, t + h, l + r, t + h], [l, t + h - r, l, t + r]];
  for (const [x0, y0, x1, y1] of runs) {
    const n = Math.max(1, Math.round(Math.hypot(x1 - x0, y1 - y0) / gap));
    for (let i = 0; i < n; i++) {
      const u = (i + .5) / n;
      out.push([x0 + (x1 - x0) * u, y0 + (y1 - y0) * u]);
    }
  }
  const k = r * .7071;
  out.push([l + r - k, t + r - k], [l + w - r + k, t + r - k],
           [l + w - r + k, t + h - r + k], [l + r - k, t + h - r + k]);
  return out;
}

/** The lit sign. `nameBoard` is the quiet version of this - a board on a post
    saying where you are; this one is the same idea dressed for the occasion,
    and it is what makes a marked level read as one from the first frame.

    A gilt frame with a lamp run all the way round it, a dark panel inside with
    a hairline inset, a crest on top and gold lettering. Every piece of it is
    struck off `size`, so the whole thing scales as one object between a phone
    and a desktop rather than coming apart at one of them.

    `lift` is how far above its ground point the board hangs, in cell sizes, and
    `post` draws the pole under it. Fitted to the canvas rather than set at a
    fixed size: SUPER BIG EVENT is half again as wide as BIG EVENT and would
    otherwise run off both sides of a phone. */
function marquee(text, wx, wz, lift, post) {
  const [px, py] = P(wx, 0, wz), s = LAY.s;
  const font = n => '800 ' + n + 'px "Baloo 2", "Trebuchet MS", sans-serif';
  let size = Math.max(11, s * .34);
  ctx.save();
  ctx.font = font(size);
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const pad = 1.9;
  let w = ctx.measureText(text).width + size * pad;
  const cap = cv.width * .56;
  if (w > cap) { size *= cap / w; ctx.font = font(size); w = ctx.measureText(text).width + size * pad; }

  const h = size * 2.0, fr = size * .17;        // panel height, frame thickness
  const crest = size * .62;
  /* ⚠ Held below the head of the canvas, and inside its sides. The topbar sits
     across the head of the frame whatever headroom the theme asks for; and the
     station and the stadium post their sign out on the platform, a hand's width
     from the right edge, so a board centred on that post runs off the canvas
     the moment the wording is longer than one short word. The board moves; the
     post stays where it stands and meets it wherever it now lands. */
  const cy = Math.max(py - s * lift, cv.height * .075 + h / 2 + fr + crest * 1.8);
  const m = cv.width * .012;
  const bx = Math.min(Math.max(px, w / 2 + fr + m), cv.width - w / 2 - fr - m);
  const L = bx - w / 2, T = cy - h / 2, r = size * .34;
  const FL = L - fr, FT = T - fr, FW = w + fr * 2, FH = h + fr * 2, FR = r + fr;

  /* The light it throws on whatever is behind it. ⚠ The box has to be at least
     as big as the gradient's own radius: filled to the frame's height instead,
     the wash was still at seven-tenths where the box stopped and left two hard
     edges ruled across the wall. */
  const GR = FW * .85;
  const gl = ctx.createRadialGradient(bx, cy, h * .25, bx, cy, GR);
  gl.addColorStop(0, "rgba(255,196,120,.26)"); gl.addColorStop(1, "rgba(255,196,120,0)");
  ctx.fillStyle = gl; ctx.fillRect(bx - GR, cy - GR, GR * 2, GR * 2);

  if (post) {
    shadow(wx, wz, .16);
    const stem = Math.min(Math.max(px, L + r), L + w - r);
    ctx.strokeStyle = "#3b3340"; ctx.lineCap = "round";
    ctx.lineWidth = Math.max(2, s * .06);
    ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(stem, cy + h * .4); ctx.stroke();
  }

  // the finial, drawn under the frame so the frame's edge finishes its foot
  const cg = ctx.createLinearGradient(0, FT - crest * 1.5, 0, FT);
  cg.addColorStop(0, "#fff4cf"); cg.addColorStop(.55, "#e0ae4c"); cg.addColorStop(1, "#a8761f");
  ctx.fillStyle = cg;
  ctx.beginPath();                       // a lozenge standing on the frame
  ctx.moveTo(bx, FT - crest * 1.30);
  ctx.lineTo(bx + crest * .52, FT - crest * .55);
  ctx.lineTo(bx, FT + crest * .10);
  ctx.lineTo(bx - crest * .52, FT - crest * .55);
  ctx.closePath(); ctx.fill();
  ctx.beginPath();                       // and the ball on top of it
  ctx.arc(bx, FT - crest * 1.52, crest * .26, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,.45)";
  ctx.beginPath();
  ctx.arc(bx - crest * .09, FT - crest * 1.60, crest * .09, 0, Math.PI * 2); ctx.fill();

  // it sits off whatever is behind it
  ctx.save();
  ctx.globalAlpha = .30; ctx.fillStyle = "#140a18";
  roundRect(FL + fr * .5, FT + fr * .9, FW, FH, FR); ctx.fill();
  ctx.restore();

  // the gilt frame: a metal gradient, not one flat gold
  const fg = ctx.createLinearGradient(0, FT, 0, FT + FH);
  fg.addColorStop(0, "#fff2c4"); fg.addColorStop(.34, "#dcae45");
  fg.addColorStop(.62, "#b8842a"); fg.addColorStop(1, "#f7dc9d");
  roundRect(FL, FT, FW, FH, FR); ctx.fillStyle = fg; ctx.fill();

  // the panel inside it
  const pg = ctx.createLinearGradient(0, T, 0, T + h);
  pg.addColorStop(0, "#3d2144"); pg.addColorStop(1, "#170b1c");
  roundRect(L, T, w, h, r); ctx.fillStyle = pg; ctx.fill();
  const ins = size * .20;
  roundRect(L + ins, T + ins, w - ins * 2, h - ins * 2, Math.max(1, r - ins));
  ctx.strokeStyle = "rgba(240,208,132,.55)";
  ctx.lineWidth = Math.max(1, size * .05); ctx.stroke();

  // the lamps, all the way round the frame
  const rr = Math.max(1.3, size * .105);
  const lamps = ringPoints(FL + fr * .5, FT + fr * .5, FW - fr, FH - fr, FR - fr * .5,
                           Math.max(size * .52, rr * 4));
  for (let i = 0; i < lamps.length; i++) {
    const [lx, ly] = lamps[i];
    const hg = ctx.createRadialGradient(lx, ly, 0, lx, ly, rr * 3.2);
    hg.addColorStop(0, "rgba(255,222,152,.55)"); hg.addColorStop(1, "rgba(255,222,152,0)");
    ctx.fillStyle = hg;
    ctx.beginPath(); ctx.arc(lx, ly, rr * 3.2, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = i % 2 ? "#fff6dc" : "#ffcd79";
    ctx.beginPath(); ctx.arc(lx, ly, rr, 0, Math.PI * 2); ctx.fill();
  }

  // the lettering: gold, cut out of the panel by a dark stroke behind it
  const ty = cy + size * .05;
  const tg = ctx.createLinearGradient(0, ty - size * .6, 0, ty + size * .6);
  tg.addColorStop(0, "#fff8e2"); tg.addColorStop(.52, "#ffdc95"); tg.addColorStop(1, "#dda13a");
  ctx.lineJoin = "round";
  ctx.strokeStyle = "rgba(26,10,30,.75)";
  ctx.lineWidth = Math.max(2, size * .10);
  ctx.strokeText(text, bx, ty);
  ctx.fillStyle = tg; ctx.fillText(text, bx, ty);
  ctx.restore();
}

/** What the sign says. The two grades read as an escalation of one thing rather
    than as two unrelated words, the way the topbar's own chip does - Hard, then
    Super. */
const partyWord = () => HARD > 1 ? "SUPER BIG EVENT" : "BIG EVENT";

/* ---- the five parties -------------------------------------------------
   Each one paints over the ground its own theme has just laid. `nz` below is
   the near ground, the strip between the front wall and the foot of the canvas:
   with the sides gone on a phone, it and the band beyond the far wall are the
   whole of the room a party has to work with.                                 */

/** Platform party. Bunting over the line at the far end, the near track lit and
    littered, and the station's own name board swapped for a lit one. */
function partyStation(E) {
  const { x0, x1, z0, z1, T, OX, gx0, gx1, gz0, gz1 } = E;
  const big = HARD > 1;
  partyWash("96,44,150", .38, .22);
  bunting(x0 - T, z0 - T * 2.5, x1 + T, z0 - T * 2.5, 1.5, 9);
  if (big) bunting(x0 - T * .3, z0 - T * 4.2, x1 + T * .3, z0 - T * 4.2, 2.0, 7);
  balloons(x0 - T * .5, z0 - T * 1.4, .82);
  balloons(x1 + T * .5, z0 - T * 1.4, .82);

  const nz = z1 + T * 1.15;
  lightPool(x0 + SX * 1.1, nz + SZ * .35, "255,77,132", 2.3, big ? .40 : .32);
  lightPool(x1 - SX * 1.1, nz + SZ * .55, "78,203,255", 2.3, big ? .36 : .28);
  litter(x0 - T, nz, x1 + T, nz + SZ * 2.0, -.024, big ? 70 : 48, 7);
  litter(gx0, gz0, x0 - T, gz1, -.024, 40, 11);          // the far track, for a wide frame

  const p0 = OX + SX * 1.25;                                // the platform, likewise
  lightPool(p0 + SX * .8, (gz0 + gz1) / 2, "255,201,60", 2.8, .30);
  litter(p0, z0 - T * 2, gx1, z1 + T * 2, -.024, 55, 13);
  marquee(partyWord(), OX + SX * .85, z0 - T * .2, 1.45, 1);
}

/** Premiere night. The carpet is laid on the near ground, across the way in,
    with a rope down both sides of it, and searchlights rake the sky over the
    sheet. */
function partyCinema(E) {
  const { x0, x1, z0, z1, T, OX, gx0, gx1, gz0, gz1 } = E;
  const big = HARD > 1;
  partyWash("150,26,52", .34, .14);
  const sz0 = z0 - T * .95 - SZ * 2.15;   // the screen's far edge, as drawCinema placed it
  beam(x0 - SX * .6, sz0 - SZ * .4, -.30, "255,236,200", .26);
  beam(x1 + SX * .6, sz0 - SZ * .4, .30, "255,236,200", .26);
  if (big) beam((x0 + x1) / 2, sz0 - SZ * .8, .01, "255,236,200", .20);
  marquee(partyWord(), (x0 + x1) / 2, sz0, 1.05, 0);

  const nz = z1 + T * 1.35;
  slab(x0 - T, nz, x1 + T, nz + SZ * 2.0, -.026, "#7e1c28");
  slab(x0 - T, nz, x1 + T, nz + SZ * .12, -.025, "#d8b45a");
  slab(x0 - T, nz + SZ * 1.88, x1 + T, nz + SZ * 2.0, -.025, "#d8b45a");
  litter(x0 - T, nz, x1 + T, nz + SZ * 2.0, -.024, big ? 50 : 34, 3);
  lightPool(x0 + SX * 1.2, nz + SZ * .55, "255,214,150", 2.0, .30);
  lightPool(x1 - SX * 1.2, nz + SZ * .55, "255,214,150", 2.0, .30);
  velvetRope(x0 - T, nz + SZ * .30, x1 + T, nz + SZ * .30, 5);

  const c0 = OX + SX * 2.20;                                // for a wide frame
  slab(c0, gz0, gx1, gz1, -.044, "#5e161f");
  slab(c0, gz0, c0 + SX * .12, gz1, -.043, "#d8b45a");
  litter(c0, gz0, gx1, gz1, -.040, 55, 23);
}

/** Cup final. Fireworks over the pitch, the near concourse lit and littered,
    and the sign up where a scoreboard would stand. */
function partyStadium(E) {
  const { x0, x1, z0, z1, T, OX, gx0, gx1, gz0, gz1 } = E;
  const big = HARD > 1;
  partyWash("40,30,90", .34, .16);
  const tz0 = z0 - T * .6 - SZ * .75;     // the near touchline, as drawStadium placed it
  /* None of them goes above lift 1.5. The topbar sits across the head of the
     canvas whatever headroom the theme asks for, and a burst any higher was
     drawn through the clock. */
  firework(x0 - SX * .4, tz0 - SZ * .5, .95, "#ff4d84", 13, 5);
  firework((x0 + x1) / 2 + SX * .6, tz0 - SZ * 1.1, 1.50, "#ffc93c", 15, 9);
  firework(x1 + SX * .4, tz0 - SZ * .5, .90, "#4ecbff", 12, 3);
  if (big) {
    firework(x0 + SX * 1.5, tz0 - SZ * 1.2, 1.45, "#a879ff", 12, 21);
    firework(x1 - SX * 1.5, tz0 - SZ * 1.3, 1.50, "#5be6a2", 12, 33);
  }
  bunting(x0 - T, z0 - T * 1.9, x1 + T, z0 - T * 1.9, 1.1, 9);

  const nz = z1 + T * 1.15;
  lightPool(x0 + SX * 1.1, nz + SZ * .35, "255,201,60", 2.3, .32);
  lightPool(x1 - SX * 1.1, nz + SZ * .55, "255,77,132", 2.3, .32);
  litter(x0 - T, nz, x1 + T, nz + SZ * 2.0, -.024, big ? 75 : 52, 13);

  const p0 = OX + SX * 2.20;                                // for a wide frame
  lightPool(p0 + SX * 1.0, (gz0 + gz1) / 2, "78,203,255", 2.8, .26);
  litter(p0, gz0, gx1, gz1, -.024, 55, 27);
  marquee(partyWord(), OX + SX * .85, z0 - T * .4, 1.45, 1);
}

/** Festival night. A wall of colour behind the stage, beams off the truss, and
    the pit lit and littered. */
function partyConcert(E) {
  const { x0, x1, z0, z1, T, OX, gx0, gx1, gz0, gz1 } = E;
  const big = HARD > 1;
  partyWash("120,40,190", .30, .14);
  const sz1 = z0 - T * .9, sz0 = sz1 - SZ * 2.4;   // the stage, as drawConcert placed it
  const sx0 = x0 - SX * .8, sx1 = x1 + SX * .8;
  const mid = (x0 + x1) / 2;
  /* The wall behind the act. Eleven narrow panels at half strength, not seven
     saturated ones: at full colour and full width it was the brightest thing on
     the screen by a distance, and the eye went to it rather than to the board.

     ⚠ Canvas space, unlike everything else the stage is built from. A cell is
     bigger on a tall narrow board than on a wide one, so a wall placed the way
     the stage is - so many cells beyond it - was behind the clock on a 4-wide
     board and halfway down the screen on a 7-wide one. Here it hangs a fixed
     distance behind the stage front and stops short of the topbar, and each
     panel fades out upwards so that stopping short does not read as a cut. */
  const wa = P(sx0, 0, sz0 - SZ * .15), wb = P(sx1, 0, sz0 - SZ * .15);
  const yB = wa[1], yT = Math.max(cv.height * .085, yB - LAY.s * 1.05);
  const wallL = Math.min(wa[0], wb[0]), wallR = Math.max(wa[0], wb[0]);
  ctx.save();
  for (let i = 0; i < 11; i++) {
    const x = wallL + (wallR - wallL) * i / 11, w = (wallR - wallL) * .78 / 11;
    const gr = ctx.createLinearGradient(0, yT, 0, yB);
    gr.addColorStop(0, "rgba(255,255,255,0)");
    gr.addColorStop(1, FEST[i % FEST.length]);
    ctx.globalAlpha = .55; ctx.fillStyle = gr;
    ctx.fillRect(x, yT, w, yB - yT);
  }
  ctx.restore();
  beam(mid - SX * 1.9, sz1 - SZ * .3, -.40, "255,77,132", .30);
  beam(mid, sz1 - SZ * .3, .02, "78,203,255", .26);
  beam(mid + SX * 1.9, sz1 - SZ * .3, .40, "255,201,60", .30);
  if (big) {
    beam(mid - SX * 3.6, sz1 - SZ * .3, -.66, "168,121,255", .26);
    beam(mid + SX * 3.6, sz1 - SZ * .3, .66, "91,230,162", .26);
  }
  litter(sx0, sz1, sx1, sz1 + SZ * 1.2, -.022, big ? 55 : 38, 5);
  marquee(partyWord(), mid, sz0 - SZ * .15, 1.35, 0);

  const nz = z1 + T * 1.15;
  lightPool(x0 + SX * 1.1, nz + SZ * .35, "168,121,255", 2.3, .34);
  lightPool(x1 - SX * 1.1, nz + SZ * .55, "78,203,255", 2.3, .34);
  litter(x0 - T, nz, x1 + T, nz + SZ * 2.0, -.024, big ? 70 : 48, 17);

  const p0 = OX + SX * 2.20;                                // for a wide frame
  lightPool(p0 + SX * 1.0, (gz0 + gz1) / 2, "255,77,132", 2.8, .28);
  litter(p0, gz0, gx1, gz1, -.028, 55, 29);
}

/** End of term. The one bright room, so the party is paper rather than light: a
    banner over the board, balloons at both ends of it, and the sign across the
    front of the class. */
function partyClassroom(E) {
  const { x0, x1, z0, z1, T, OX, gx0, gx1, gz0, gz1 } = E;
  const big = HARD > 1;
  partyWash("255,110,185", .30, .10);
  const bz1 = z0 - T * .95, bz0 = bz1 - SZ * 1.5;   // the board, as drawClassroom placed it
  bunting(x0 - SX * .8, bz0 - SZ * .1, x1 + SX * .8, bz0 - SZ * .1, .95, 10);
  if (big) bunting(x0 - SX * .3, bz0 - SZ * 1.3, x1 + SX * .3, bz0 - SZ * 1.3, 1.6, 8);
  balloons(x0 - SX * .55, bz1, .85);
  balloons(x1 + SX * .55, bz1, .85);
  marquee(partyWord(), (x0 + x1) / 2, bz0 - SZ * .1, 1.55, 0);

  const nz = z1 + T * 1.15;
  lightPool(x0 + SX * 1.1, nz + SZ * .35, "255,127,176", 2.3, .30);
  lightPool(x1 - SX * 1.1, nz + SZ * .55, "255,201,60", 2.3, .26);
  litter(x0 - T, nz, x1 + T, nz + SZ * 2.0, -.024, big ? 75 : 52, 17);
  litter(gx0, gz0, x0 - T, gz1, -.044, 40, 23);           // for a wide frame

  const p0 = OX + SX * 2.20;                                // for a wide frame
  lightPool(p0 + SX * 1.2, (gz0 + gz1) / 2, "168,121,255", 2.8, .24);
  litter(p0, gz0, gx1, gz1, -.026, 55, 31);
}

/* ---- the room itself, dressed -----------------------------------------
   The five painters above all work OUTSIDE the walls, and on a phone that is
   where most of the frame is. This is the other half: the board, which is the
   part the player is actually looking at. A wash of light on the floor, a run
   of bulbs round the wall top with a bracket at each corner, and a pool of
   light under every seat.

   One set for all five rooms, and one gold, because what it is saying is not
   "this is a station" but "this one is an occasion" - and that does not change
   with the room.

   ⚠ Nothing here may touch a seat's colour or lift a tile's contrast: the
   colours ARE the puzzle, and a decoration that makes two of them harder to
   tell apart has cost the player the level. So what is left inside the walls is
   light and nothing else - warm, low, and the same under every seat. Anything
   with an edge to it belongs on the wall top or beyond it, where the grid is
   not. */
const EVENT_GOLD = "#e3bd68";

/** The floor of a Big Event room: a wash that lifts the middle and lets the
    corners go. Drawn straight after the tiles, so the seats and everybody
    walking are still to come over the top.

    ⚠ Light only. A gilt border inlaid round the floor was tried here and taken
    out again: it is a line drawn ACROSS the grid the player is reading, it runs
    behind the seats rather than round them, and on a full board it is one more
    edge competing with the only edges that matter. */
function eventFloor(E) {
  const { x0, x1, z0, z1 } = E;
  const c = slabPath(x0, z0, x1, z1, .009);
  const L = Math.min(...c.map(p => p[0])), R = Math.max(...c.map(p => p[0]));
  const T = Math.min(...c.map(p => p[1])), B = Math.max(...c.map(p => p[1]));
  const W = R - L, H = B - T;
  ctx.save(); ctx.clip();
  const g = ctx.createRadialGradient(L + W / 2, T + H / 2, Math.min(W, H) * .12,
                                     L + W / 2, T + H / 2, Math.max(W, H) * .62);
  g.addColorStop(0, "rgba(255,226,172,.11)");
  g.addColorStop(.6, "rgba(255,226,172,.02)");
  g.addColorStop(1, "rgba(28,14,44,.18)");
  ctx.fillStyle = g; ctx.fillRect(L, T, W, H);
  ctx.restore();
}

/** The wall top of a Big Event room: lamps all the way round it and a bracket
    at each corner. Drawn last, over the doorway cut, so the run reads as one
    continuous thing rather than as a band the door has been punched through.

    ⚠ The doorway keeps its gap. A lamp standing in the way in is the one place
    on this wall where a decoration would sit on top of the thing the player is
    reading - the head of the queue, coming through. */
function eventWalls(E) {
  const { x0, x1, z0, z1, T, H, dz0, dz1 } = E;
  const a = x0 - T + .09, b = x1 + T - .09;
  const c = z0 - T + .09, d = z1 + T - .09;
  const step = SX * .62;

  const arm = SX * .90, th = .16;
  const bracket = (cx, cz, dx, dz) => {
    slab(Math.min(cx, cx + dx * arm), Math.min(cz, cz + dz * th),
         Math.max(cx, cx + dx * arm), Math.max(cz, cz + dz * th), H + .005, EVENT_GOLD);
    slab(Math.min(cx, cx + dx * th), Math.min(cz, cz + dz * arm),
         Math.max(cx, cx + dx * th), Math.max(cz, cz + dz * arm), H + .005, EVENT_GOLD);
  };
  ctx.save(); ctx.globalAlpha = .85;
  bracket(x0 - T, z0 - T, 1, 1);   bracket(x1 + T, z0 - T, -1, 1);
  bracket(x0 - T, z1 + T, 1, -1);  bracket(x1 + T, z1 + T, -1, -1);
  ctx.restore();

  const at = [];
  for (let x = a; x <= b + 1e-6; x += step) { at.push([x, c]); at.push([x, d]); }
  for (let z = c + step; z < d - step * .5; z += step) {
    at.push([a, z]);
    if (z < dz0 - .25 || z > dz1 + .25) at.push([b, z]);
  }
  const r = Math.max(1.2, LAY.s * .050);
  ctx.save();
  for (let i = 0; i < at.length; i++) {
    const [px, py] = P(at[i][0], H + .007, at[i][1]);
    const gl = ctx.createRadialGradient(px, py, 0, px, py, r * 3.4);
    gl.addColorStop(0, "rgba(255,212,136,.40)"); gl.addColorStop(1, "rgba(255,212,136,0)");
    ctx.fillStyle = gl;
    ctx.beginPath(); ctx.arc(px, py, r * 3.4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = i % 2 ? "#fff5d6" : "#ffcd79";
    ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

/** The pool of light a seat stands in on a Big Event level. Sized off the seat
    itself so a three-cell bench gets a three-cell pool, and measured on the
    canvas rather than guessed at: the two ground axes do not come out the same
    length on screen under this camera. */
function seatSheen(b, wx, wz, alpha) {
  const along = b.len * .52 + .18, across = .52;
  const hx = (b.dir & 1 ? across : along) * SX;
  const hz = (b.dir & 1 ? along : across) * SZ;
  const [px, py] = P(wx, 0, wz);
  const rx = Math.abs(P(wx + hx, 0, wz)[0] - px);
  const rz = Math.abs(P(wx, 0, wz + hz)[1] - py);
  if (rx < 1 || rz < 1) return;
  ctx.save();
  ctx.globalAlpha = (alpha == null ? 1 : alpha) * .9;
  ctx.translate(px, py); ctx.scale(1, rz / rx);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx);
  g.addColorStop(0, "rgba(255,231,182,.20)");
  g.addColorStop(.55, "rgba(255,231,182,.09)");
  g.addColorStop(1, "rgba(255,231,182,0)");
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(0, 0, rx, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

/* head / page / cheer, where the party wants them different, and a skin patch
   laid over the room's own. Only the keys that change are listed: everything
   else is the theme underneath, which is the point - it is the same room. */
const PARTY = {
  station: {
    head: .15, page: "#3b2452", paint: partyStation,
    skin: { wall: "#7b3ba8", top: "#9a5fd0", lip: "#4d2470", trim: "#ffc93c",
            fa: "#efe7f4", fb: "#ded3e8", grout: "#c3b3d0", door: "#ffd75a" },
  },
  cinema: {
    head: .30, page: "#1c0d12", paint: partyCinema, cheer: .10,
    skin: { wall: "#4a2030", top: "#5d2a3c", lip: "#2c1220", trim: "#d8b45a",
            fa: "#4d1c22", fb: "#441a1f", grout: "#2c1216", door: "#d8b45a" },
  },
  stadium: {
    head: .26, page: "#191d2b", paint: partyStadium,
    skin: { wall: "#7e8aa0", top: "#98a4bc", lip: "#5c6474", trim: "#ffc93c",
            fa: "#b6bccb", fb: "#a6adbd", grout: "#666d7c", door: "#ffc93c" },
  },
  concert: {
    head: .28, page: "#120b1c", paint: partyConcert,
    skin: { wall: "#3a2450", top: "#4e3268", lip: "#241533", trim: "#ff4d84",
            fa: "#4a3358", fb: "#3f2b4b", grout: "#2a1c38", door: "#ff4d84" },
  },
  classroom: {
    head: .25, page: "#ddc9e2", paint: partyClassroom, cheer: .16,
    skin: { wall: "#e7d6ea", top: "#f6ecf7", lip: "#c1a4c8", trim: "#ff7fb0",
            fa: "#f3ead9", fb: "#e7dccb", grout: "#c0b09c", door: "#ff9ec4" },
  },
};

/** The theme as it is actually being played: the room's own entry, with the
    party laid over it when the board is a marked one. Everything that reads a
    theme goes through this rather than through THEMES, so a party never has to
    be remembered at the call site. The merge is worked out once per room. */
function themeNow() {
  const base = THEMES[THEME] || THEMES.station;
  const p = HARD ? PARTY[THEME] : null;
  if (!p) return base;
  return p.on || (p.on = Object.assign({}, base, {
    head: p.head == null ? base.head : p.head,
    page: p.page || base.page,
    cheer: p.cheer == null ? base.cheer : p.cheer,
    // A painted plate is the ordinary platform and nothing else. A party
    // repaints the ground, so it has to draw its own room out there.
    plate: false,
    skin: Object.assign({}, base.skin, p.skin),
    party: p.paint,
    // the same two for every room - see the dressing block above
    dressFloor: eventFloor,
    dressWalls: eventWalls,
  }));
}

/* ---- the interior walls ------------------------------------------------
   A `hole` is a cell the floor skips, and 71 of the shipped boards carry a run
   of them: a partition down the middle of the room, nine cells of an eleven-row
   board, open at BOTH ends so the queue walks around either side.

   ⚠ Until this was drawn, a hole was nothing but a cell the floor loop skipped,
   so what the player saw was the cavity colour showing through - a dark patch
   the same family as the floor it sat in. It read as a pit, or as a stripe of
   pattern, rather than as something a passenger cannot cross, which is the one
   thing about it that changes how the board is played.

   It is built out of the room's own recipe - body, livery stripe, lit crown -
   rather than colours of its own, so every theme dresses it without a table
   here naming five more. */

/** The hole cells as a few big rectangles rather than many little ones.

    Greedy: take the first unclaimed cell, run right while the row holds, then
    down while the whole width holds. ⚠ Merging matters even though the shipped
    boards are all one column - a block drawn per CELL puts a stripe of trim
    across the wall every 1.6 units, which reads as a row of bollards. */
function holeRects(g) {
    const seen = new Uint8Array(g.W * g.H), out = [];
    for (let r = 0; r < g.H; r++) for (let c = 0; c < g.W; c++) {
        const i = r * g.W + c;
        if (!g.hole[i] || seen[i]) continue;
        let c1 = c;
        while (c1 + 1 < g.W && g.hole[r * g.W + c1 + 1] && !seen[r * g.W + c1 + 1]) c1++;
        let r1 = r;
        for (;;) {
            const nr = r1 + 1;
            if (nr >= g.H) break;
            let ok = true;
            for (let k = c; k <= c1 && ok; k++) ok = !!g.hole[nr * g.W + k] && !seen[nr * g.W + k];
            if (!ok) break;
            r1 = nr;
        }
        for (let rr = r; rr <= r1; rr++) for (let cc = c; cc <= c1; cc++) seen[rr * g.W + cc] = 1;
        out.push([c, r, c1, r1]);
    }
    return out;
}

/* ⚠ The partition's colours are computed from the FLOOR, not taken from
   SKIN.wall, and that is the whole difference between it reading and not.
   The skins were authored for a room seen against the outside, so their wall
   colour has no duty to stand out from their own floor: cinema is wall #3a2c26
   on carpet #332721, near enough the same tone that the block vanished into the
   grid. Station is the other failure - its livery is #f8bf1a, and a canary
   yellow bar through the middle of the board shouts louder than the seats.
   Shifting away from the floor by a fixed amount gives every theme the same
   contrast without a table here naming five more colours. */
/** ⚠ Accepts what it also RETURNS. The first cut parsed hex only, and every
    colour here is derived from another - so the moment one was fed back in,
    parseInt read "rgb(117,107,103)" as NaN and the tone came out pure black.
    That is where the black joints across the first wall came from, and it looks
    like a styling choice rather than a parse failure, which is what made it
    survive a look. */
function wallRgb(c) {
    const m = /^rgb\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)/.exec(c);
    if (m) return [+m[1], +m[2], +m[3]];
    const h = c.replace("#", "");
    const n = parseInt(h.length === 3 ? h.replace(/./g, d => d + d) : h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
const wallStr = c => "rgb(" + c.map(v => Math.round(Math.max(0, Math.min(255, v)))).join(",") + ")";
/** Perceived lightness, 0..1 - the weights are why a yellow floor counts as
    light and a grey one of the same number does not. */
function wallLum(c) {
    const [r, g, b] = wallRgb(c);
    return (r * .2126 + g * .7152 + b * .0722) / 255;
}
/** `k` < 0 darker, > 0 lighter.

    ⚠ Lightening MULTIPLIES rather than mixing toward white, and that is the
    difference between a warm brown wall and a grey slab. Mixing toward white
    pulls every channel to the same place, so a dark colour lightened that way
    loses its hue exactly when it is being lightened the most - which turned the
    cinema's brown partition into a placeholder-grey bar on the carpet. Above
    mid lightness a gain can only clip, so the mix is used there instead. */
function wallTone(c, k) {
    const p = wallRgb(c);
    if (k < 0) return wallStr(p.map(v => v * (1 + k)));
    return wallLum(c) < .55 ? wallStr(p.map(v => v * (1 + k * 2.6)))
                            : wallStr(p.map(v => v + (255 - v) * k));
}
/** The same colour taken to a given lightness, hue intact. Used to guarantee
    the partition separates from the floor it stands on however the theme was
    painted. */
function wallLift(c, target) {
    const l = wallLum(c);
    return l < .02 ? wallStr([255 * target, 255 * target, 255 * target])
                   : wallStr(wallRgb(c).map(v => v * (target / l)));
}

/** The partition's body colour for a given skin.

    Its own function so that anything measuring the design calls the same code
    the game draws with. Written inline first, and the script checking the
    contrast then carried a COPY of the expression - which is a number that
    agrees with the game right up until one of the two is edited.

    ⚠ The threshold is .20, not the .12 it started at. Measured across all five
    themes at all three grades, .12 let three skins through unlifted at gaps of
    .123, .132 and .145 - concert's plain room being the worst, a wall darker
    than its own floor by barely more than a shade. Everything lifted lands near
    .20, and .20 is what those three needed to match it. */
function wallBody(SKIN) {
    const floorL = wallLum(SKIN.fa), room = SKIN.wall;
    return Math.abs(wallLum(room) - floorL) < .20
        ? wallLift(room, floorL < .45 ? floorL + .22 : floorL - .24) : room;
}

/** One partition, standing on the floor.

    ⚠ Height is NOT what sells this, and trying to make it taller is the wrong
    lever. The camera sits at pitch 1.33 - within 14 degrees of straight down -
    so raising a face by .58 of a world unit lifts it about FOUR PIXELS on a
    phone. The first cut used the room's own wall recipe at that height and read
    as a rug lying on the floor. What does the work is tone: a top clearly apart
    from the floor, a near face much darker than the top, and a shadow thrown
    across the tiles beside it.

    ⚠ Only the near face is drawn. The camera has no yaw, so a face whose normal
    runs along x is seen exactly edge-on and has no width on screen at all -
    drawing the two ends would be four points on a line. The far face is behind
    its own top. */
function drawHoleWalls(g, SKIN, H) {
    const rects = holeRects(g);
    if (!rects.length) return;
    /* ⚠ Built from the room's OWN wall colour, not from a neutral. Lightening
       the floor toward white was the second failure: it separated cleanly and
       came out a desaturated grey bar that belonged to no theme - a placeholder
       laid on the carpet. Taking the wall's hue makes the partition obviously
       the same stuff the room is built of, which is the fastest way to say
       "you cannot walk through this" without a label.

       The floor is still consulted, but only to guarantee separation: cinema's
       wall and carpet are four points of lightness apart, and there the body is
       pushed away from the floor until it reads. */
    const body = wallBody(SKIN);
    const top = body;
    const crown = wallTone(body, .22);
    const face = wallTone(body, -.46);
    const rib = wallTone(body, -.20);
    // The shadow is the floor's own colour taken down, not black: on a room as
    // dark as the cinema a black shadow is invisible, and on the station's
    // cream floor it would be a smear of soot.
    const cast = wallTone(SKIN.fa, -.42);
    // Below the room's own walls on purpose. Level with them and the partition
    // reads as the room being two rooms; under them it reads as one room with
    // something standing in it, which is what it is.
    const HW = H * .74;
    for (const [c0, r0, c1, r1] of rects) {
        const x0 = cellW(c0) - SX / 2, x1 = cellW(c1) + SX / 2;
        const z0 = cellZ(r0) - SZ / 2, z1 = cellZ(r1) + SZ / 2;

        /* The shadow, and it earns its place: in a view this close to straight
           down it is the strongest signal that anything stands up at all.
           Three offset copies rather than one, because a single hard-edged
           rectangle beside the block reads as a second, flatter block. */
        ctx.save();
        for (let i = 3; i >= 1; i--) {
            ctx.globalAlpha = .17;
            const d = i * .17;
            slab(x0 + d, z0 + d * 1.15, x1 + d, z1 + d * 1.15, .008, cast);
        }
        ctx.restore();

        // The face the camera can actually see, floor to top.
        quad([P(x0, 0, z1), P(x1, 0, z1), P(x1, HW, z1), P(x0, HW, z1)], face);

        slab(x0, z0, x1, z1, HW, top);                      // the top

        /* Panel joints, one per cell across the run's length. Without them a
           nine-cell partition is one long featureless bar with nothing to read
           its size against; with them it is masonry, and the joints line up
           with the grid the seats sit on, so the wall is measured in the same
           units as everything else on the board. */
        const along = (r1 - r0) >= (c1 - c0);
        if (along) for (let r = r0 + 1; r <= r1; r++) {
            const z = cellZ(r) - SZ / 2;
            slab(x0 + .12, z - .05, x1 - .12, z + .05, HW + .002, rib);
        } else for (let c = c0 + 1; c <= c1; c++) {
            const x = cellW(c) - SX / 2;
            slab(x - .05, z0 + .12, x + .05, z1 - .12, HW + .002, rib);
        }

        // The lit edge, on the far side, where the room's own crown is lit too.
        // Last, so a joint cannot run through it.
        slab(x0, z0, x1, z0 + .12, HW + .004, crown);
    }
}

function drawRoom(g) {
  // A painted plate replaces the ground OUTSIDE the room. The walls, the floor
  // and the doorway stay drawn: they have to line up with the grid to the pixel,
  // and they are what makes the place read as a room at all.
  const painted = !!(BG && BG.complete && BG.naturalWidth);
  if (painted) drawBackdrop();
  const x0 = cellW(-.5), x1 = cellW(g.W - 1 + .5);
  const z0 = cellZ(-.5), z1 = cellZ(g.H - 1 + .5);
  const T = .90, H = .78;                        // wall thickness, wall height
  const dz0 = cellZ(g.door) - SZ * .42, dz1 = cellZ(g.door) + SZ * .42;
  const OX = x1 + T;                             // outside face of the door wall
  // A board with two lines has a doorway in the far wall as well, at the same
  // row, and OX2 is that wall's outside face. Everything below that draws the
  // near doorway is mirrored across the room for it.
  const twoDoors = !!(g.doors && g.doors.length > 1);
  const OX2 = x0 - T;
  // the far doorway has its own row, and it is not the near one's
  const dr2 = twoDoors ? g.doors[1][1] : 0;
  const ez0 = cellZ(dr2) - SZ * .42, ez1 = cellZ(dr2) + SZ * .42;

  // ---- outside the room ----
  const gx0 = x0 - T - SX * 9, gx1 = x1 + T + SX * 9;
  const gz0 = z0 - T - SZ * 9, gz1 = z1 + T + SZ * 9;
  const TH = themeNow();
  const f = FIN ? FIN.f : null;
  const E = { g, x0, x1, z0, z1, T, H, OX, dz0, dz1, gx0, gx1, gz0, gz1, SKIN: TH.skin };
  ROOME = E;
  // ⚠ The ground does not move with the carriage. SHIFT is the train pulling
  // out; everything beyond the walls is drawn where it stands.
  const moved = SHIFT; SHIFT = [0, 0];
  // A painted plate stands in for the station ground and nothing else: the other
  // themes draw a whole building out there, which no ground tile can replace.
  if (!(painted && TH.plate)) TH.outside(E);
  if (TH.party) TH.party(E);          // the hard-level dressing, see PARTY
  if (f != null && TH.finale) TH.finale(E, f, "back");
  // A deck for the far line, on the boards that have one. Without it they are
  // stood on the track: a sprite that fades with its place in the queue, against
  // dark ground, is a line nobody can read - and the near line has had a
  // platform under it since the beginning. Built from the room's own colours, so
  // it belongs to whichever theme is up rather than being a station in a cinema.
  if (twoDoors) {
    const K = TH.skin;
    slab(gx0, gz0, OX2, gz1, -.030, K.lip);                        // the drop to the track
    slab(gx0, gz0, OX2 - SX * .13, gz1, -.028, K.fa);              // the deck
    slab(OX2 - SX * .42, gz0, OX2 - SX * .30, gz1, -.026, K.trim); // the line you stand behind
  }
  SHIFT = moved;

  // ---- the carriage ----
  ctx.save(); ctx.globalAlpha = .22;             // it sits on the ground, so it casts
  slab(x0 - T + .18, z0 - T + .22, x1 + T + .18, z1 + T + .22, -.02, "#3c3a33");
  ctx.restore();

  const SKIN = TH.skin;

  // wall tops: one solid band all the way round, then the cavity punched out
  slab(x0 - T, z0 - T, x1 + T, z1 + T, H, SKIN.wall);
  slab(x0 - T, z0 - T, x1 + T, z0 - T + .16, H + .002, SKIN.trim);      // livery stripe, far
  slab(x0 - T, z1 + T - .16, x1 + T, z1 + T, H + .002, SKIN.trim);      // livery stripe, near
  slab(x0 - T, z0 - T, x0 - T + .16, z1 + T, H + .002, SKIN.trim);
  slab(x1 + T - .16, z0 - T, x1 + T, z1 + T, H + .002, SKIN.trim);
  // a lighter crown just inside the stripe reads as the top edge catching light
  slab(x0 - T + .16, z0 - T + .16, x1 + T - .16, z0 - T + .34, H + .003, SKIN.top);

  // windows let into the far wall top
  const panes = SKIN.glass ? Math.max(2, g.W - 1) : 0;
  for (let i = 0; i < panes; i++) {
    const a = x0 + (i + .16) * (x1 - x0) / panes, b = x0 + (i + .84) * (x1 - x0) / panes;
    slab(a, z0 - T * .74, b, z0 - T * .18, H + .004, SKIN.glass);
    slab(a, z0 - T * .30, b, z0 - T * .18, H + .005, ROOM.glassBar);
  }

  // the cavity: floor, dropped back to ground level
  slab(x0, z0, x1, z1, .0, SKIN.grout);
  for (let r = 0; r < g.H; r++) for (let c = 0; c < g.W; c++) {
    if (g.hole[idx(g, c, r)]) continue;
    quad(tileQuad(c, r, .006), (r + c) % 2 ? SKIN.fa : SKIN.fb);
  }
  if (TH.dressFloor) TH.dressFloor(E);
  // ⚠ After dressFloor, before the pieces. A hard wall painted over by the
  // hard-level floor wash would read as translucent, and a piece is never on a
  // hole cell, so nothing that draws later needs to sit on top of it.
  drawHoleWalls(g, SKIN, H);
  // the inner faces of the walls, seen almost edge-on: a dark lip is what sells them
  const L = .17;
  slab(x0 - L, z0 - L, x1 + L, z0, .0, SKIN.lip);
  slab(x0 - L, z1, x1 + L, z1 + L, .0, SKIN.lip);
  if (twoDoors) {                                // the far lip parts for its own way in
    slab(x0 - L, z0, x0, ez0, .0, SKIN.lip);
    slab(x0 - L, ez1, x0, z1, .0, SKIN.lip);
  } else {
    slab(x0 - L, z0, x0, z1, .0, SKIN.lip);
  }
  slab(x1, z0, x1 + L, dz0, .0, SKIN.lip);
  slab(x1, dz1, x1 + L, z1 + L, .0, SKIN.lip);

  // ---- the doorway ----
  // One cut, at wall height, and nothing else. The threshold and the step were
  // drawn at floor level, so under this camera they landed BELOW the cut and the
  // three of them stacked up into bars across the way in.
  slab(x1 - .02, dz0, OX + .02, dz1, H + .004, SKIN.door);
  if (twoDoors) slab(OX2 - .02, ez0, x0 + .02, ez1, H + .004, SKIN.door);

  if (TH.dressWalls) TH.dressWalls(E);
  if (f != null && TH.finale) TH.finale(E, f, "room");
}


function draw() {
  if (!S) return;
  const g = S;
  fitCanvas(g);
  LAY = layout();
  if (!ready) return;
  const TH = themeNow();
  if (FIN) FIN.f = Math.min(1, (performance.now() - FIN.t0) / FIN.ms);
  SHIFT = FIN && RICH && TH.shift ? TH.shift(FIN.f) : [0, 0];
  if (RICH) { ctx.fillStyle = ROOM.ground; ctx.fillRect(0, 0, cv.width, cv.height); }
  else {
    const grad = ctx.createLinearGradient(0, 0, 0, cv.height);
    grad.addColorStop(0, "#fdfdfc"); grad.addColorStop(1, "#ececeb");
    ctx.fillStyle = grad; ctx.fillRect(0, 0, cv.width, cv.height);
  }

  if (RICH) drawRoom(g); else {
  // bus shell
  const pad = 1.05;
  quad([P(cellW(-pad), 0, cellZ(-pad)), P(cellW(g.W - 1 + pad), 0, cellZ(-pad)),
        P(cellW(g.W - 1 + pad), 0, cellZ(g.H - 1 + pad)), P(cellW(-pad), 0, cellZ(g.H - 1 + pad))], "#f8bf1a");
  const inner = .78;
  quad([P(cellW(-inner), .002, cellZ(-inner)), P(cellW(g.W - 1 + inner), .002, cellZ(-inner)),
        P(cellW(g.W - 1 + inner), .002, cellZ(g.H - 1 + inner)), P(cellW(-inner), .002, cellZ(g.H - 1 + inner))], "#d2452c");

  // floor
  for (let r = 0; r < g.H; r++) for (let c = 0; c < g.W; c++) {
    if (g.hole[idx(g, c, r)]) continue;
    quad(tileQuad(c, r, .006), (r + c) % 2 ? "#95948c" : "#545354");
  }
  // doorway: an opening in the wall, the floor under it stays plain
  const dq = [P(cellW(g.W - 1) + SX * .5, .01, cellZ(g.door) - SZ * .42),
              P(cellW(g.W - 1) + SX * 1.02, .01, cellZ(g.door) - SZ * .42),
              P(cellW(g.W - 1) + SX * 1.02, .01, cellZ(g.door) + SZ * .42),
              P(cellW(g.W - 1) + SX * .5, .01, cellZ(g.door) + SZ * .42)];
  quad(dq, "#7fd2f2");
  }

  const region = reachRegion(g, 0);
  const nextCol = g.queue.length ? g.queue[0] : -1;
  const doorBlocked = !isFree(g, g.W - 1, g.door);
  g.nextSeat = (nextUp(g) || {}).spot || null;

  // Lighting up every legal destination floods the board, so the only thing that
  // marks a picked-up seat is a glow on its own tile.
  if (!g.sel) {
    for (let r = 0; r < g.H; r++) for (let c = 0; c < g.W; c++)
      if (GUIDES && region[idx(g, c, r)]) {
        ctx.save(); ctx.globalAlpha = .22;
        quad(tileQuad(c, r, .012), "#bfe9ff");
        ctx.restore();
      }
  }

  for (const a of g.anim) {
    if (!GUIDES || !a.route) continue;
    ctx.save(); ctx.globalAlpha = .30;
    for (const [c, r] of a.route) quad(tileQuad(c, r, .014), "#ffffff");
    ctx.restore();
  }

  const items = [];
  const push = (wx, wz, fn, bias) => items.push({ z: view(wx, 0, wz)[2] + (bias || 0), fn });

  const held = HELD && HELD.moved ? HELD.seat : null;
  const gdx = held ? HELD.dx : 0, gdz = held ? HELD.dz : 0;

  for (const b of g.seats) {
    if (b === held) continue;                 // drawn last, riding the cursor
    const [sx, sz] = seatCentre(b);
    push(sx, sz, () => { shadow(sx, sz, (isBlock(b) ? .32 : .45) * b.len); paintPiece(b, sx, sz, 1); });
    if (GUIDES && doorBlocked && b.id === g.occ[idx(g, g.W - 1, g.door)]) {
      const cs = cellsOf(b), mid = cs[Math.floor(cs.length / 2)];
      push(cellW(mid[0]), cellZ(mid[1]), () => {
        const [px, py] = P(cellW(mid[0]), .02, cellZ(mid[1]));
        ctx.save(); ctx.strokeStyle = "#ffcf3d"; ctx.lineWidth = Math.max(3, LAY.s * .075);
        ctx.setLineDash([LAY.s * .18, LAY.s * .12]);
        ctx.beginPath(); ctx.ellipse(px, py, SX * .5 * LAY.s, SX * .5 * LAY.s * .42, 0, 0, Math.PI * 2);
        ctx.stroke(); ctx.restore();
      }, -.05);
    }
    if (GUIDES && g.nextSeat && b === g.nextSeat.seat) {
      const cs = cellsOf(b), mid = cs[Math.floor(cs.length / 2)];
      push(cellW(mid[0]), cellZ(mid[1]), () => {
        const [px, py] = P(cellW(mid[0]), .02, cellZ(mid[1]));
        ctx.save(); ctx.strokeStyle = "rgba(255,255,255,.95)"; ctx.lineWidth = Math.max(2, LAY.s * .055);
        ctx.beginPath(); ctx.ellipse(px, py, SX * .46 * LAY.s, SX * .46 * LAY.s * .42, 0, 0, Math.PI * 2);
        ctx.stroke(); ctx.restore();
      }, -.05);
    }
    b.occ.forEach((ci, i) => {
      if (ci == null) return;
      const [c, r] = placeCell(b, i), [wx, wz] = placeAt(b, i), z = 1 / packing(b);
      push(wx, wz, () => blit(riderFrame(b, ci), wx, .05 + cheerLift(c, r), wz - .04, 1, z), .3);
    });
  }

  // the stop, one line per door
  const qnow = performance.now();
  for (let dk = 0; dk < (g.doors ? g.doors.length : 1); dk++) {
    const q = queueOf(g, dk);
    const [laneX, laneZ] = stopAt(g, dk);
    for (let i = 0; i < Math.min(q.length, 7); i++) {
      const st = g.qsteps && g.qsteps[dk] && g.qsteps[dk][i];
      const back = st ? placesBack(st, qnow) : 0;       // places still to walk
      // Waiting your turn is not walking: until t0 comes round you are carrying the
      // whole place and standing still, and drawing that as a walk frame turns the
      // back half of the line to face away for as long as anyone is boarding.
      const walking = back > 1e-3 && qnow >= st.t0;
      const pos = i + back, wz = laneZ + pos * QUEUE_PITCH * queueDir(g, dk);
      const nm = SPRITE[colName(q[i])] || "grey";
      // No fade. It was there to push the tail of the line back behind the head,
      // but the line is information - who is coming, in what colour, in what
      // order - and a player reading the back of it was reading it through a
      // veil. The far line made that plain: over dark ground the tail was simply
      // not there.
      const a = 1;
      push(laneX, wz, () => {
        shadow(laneX, wz, .3);
        if (!walking) return blit("idle_" + nm, laneX, 0, wz, a);
        // Stepping up: away from the camera, and the legs cycle on the distance
        // covered, the same way they do for someone out on the floor.
        ctx.globalAlpha = a;
        blitWalk(nm, "u", Math.floor((st.from - back) * QUEUE_PITCH / STRIDE) % WMETA.phases,
                 laneX, 0, wz);
        ctx.globalAlpha = 1;
      });
    }
  }
  for (const a of g.anim)
    push(a.x, a.z, () => {
      shadow(a.x, a.z, .3);
      blitWalk(SPRITE[colName(a.ci)] || "grey", a.facing || "d", a.phase || 0, a.x, a.y || 0, a.z);
    }, 1.5);

  items.sort((p, q) => p.z - q.z);
  for (const it of items) it.fn();

  if (held) {
    const A = .72;                          // lighter than a seat that is put down
    const [sx, sz] = seatCentre(held);
    shadow(sx + gdx, sz + gdz, (isBlock(held) ? .32 : .45) * held.len);
    paintPiece(held, sx + gdx, sz + gdz, A);
    held.occ.forEach((ci, i) => {
      if (ci == null) return;
      const [wx, wz] = placeAt(held, i);
      blit(riderFrame(held, ci), wx + gdx, .05, wz + gdz - .04, A, 1 / packing(held));
    });
  }

  if (g.sel) {
    for (const [c, r] of cellsOf(g.sel)) {
      ctx.save(); ctx.globalAlpha = .30;
      quad(tileQuad(c, r, .016), "#ffe9a8"); ctx.restore();
    }
  }

  if (FIN && RICH && TH.finale && ROOME) TH.finale(ROOME, FIN.f, "over");
  onOverlay(g);                  // the shell's own marks, on top of the room
}

/* ---------------- input ---------------- */
const seatAt = (g, c, r) => { const id = g.occ[idx(g, c, r)]; return id < 0 ? null : g.seats[id]; };

function toCanvas(clientX, clientY) {
  const rect = cv.getBoundingClientRect();
  return [(clientX - rect.left) / rect.width * cv.width,
          (clientY - rect.top) / rect.height * cv.height];
}
/** Where the cursor is on the floor, in world units - not snapped to a tile. */
function pickWorld(clientX, clientY) {
  const [px, py] = toCanvas(clientX, clientY);
  const o = P(0, 0, 0);
  const a = BX[0] * LAY.s, b = BZ[0] * LAY.s, c2 = -BX[1] * LAY.s, d = -BZ[1] * LAY.s;
  const det = a * d - b * c2;
  if (!det) return null;
  const dx = px - o[0], dy = py - o[1];
  return [(dx * d - b * dy) / det, (a * dy - dx * c2) / det];
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
/** Does a drawn sprite actually cover this canvas point? Mirrors blit() exactly,
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

function pickSeatAt(clientX, clientY) {
  const [X, Y] = toCanvas(clientX, clientY);
  let best = null, bestZ = -Infinity;
  const take = (b, z) => { if (z > bestZ) { bestZ = z; best = b; } };
  for (const b of S.seats) {
    const [sx, sz] = seatCentre(b);
    if (spriteHit(seatFrame(b), sx, 0, sz, X, Y)) take(b, view(sx, 0, sz)[2]);
    b.occ.forEach((ci, i) => {                  // a passenger counts as their seat
      if (ci == null) return;
      const [wx, wz] = placeAt(b, i);
      if (spriteHit(riderFrame(b, ci), wx, .05, wz - .04, X, Y))
        take(b, view(wx, 0, wz)[2] + .3);
    });
  }
  if (best) return best;
  const cell = pickCell(clientX, clientY);          // fall back to the floor tile
  return cell ? seatAt(S, cell[0], cell[1]) : null;
}

/* ---------------- picking a seat up and putting it down ----------------
   One state, one gesture: press a seat, it follows the pointer, release to drop
   it. There is deliberately no sticky selection - carrying one over from the
   last press is what made it feel like the old seat was still in hand.        */

let HELD = null;   // { seat, w0, dx, dz, moved }

/** Where the held seat is hovering, in fractional cells. */
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
const SNAP = 1.4;                 // how far from a legal cell a drop still counts
function releaseHeld() { HELD = null; S.sel = null; S.dragTargets = null; }

/* ---- gesture recorder ----------------------------------------------------
   A drag that misbehaves under a real mouse leaves no trace in a headless test,
   so every gesture is written down: what was under the pointer, what state the
   seat was in, and what the drop resolved to. Shown on screen, and posted to the
   dev server when one is listening.                                          */
const TRACE = [];
let TRACING = new URLSearchParams(location.search).has("trace");
function trace(o) {
  if (!TRACING) return;
  o.t = Math.round(performance.now());
  TRACE.push(o); if (TRACE.length > 40) TRACE.shift();
  const el = document.getElementById("trace");
  if (el) el.textContent = TRACE.slice(-7).reverse()
    .map(x => Object.entries(x).filter(([k]) => k !== "t")
      .map(([k, v]) => k + "=" + JSON.stringify(v)).join(" ")).join(String.fromCharCode(10));
  try {
    if (location.protocol.startsWith("http"))
      fetch("/log", { method: "POST", body: JSON.stringify(o), keepalive: true });
  } catch (e) {}
}

cv.addEventListener("pointerdown", ev => {
  if (!S || S.phase !== "play") return;
  const seat = pickSeatAt(ev.clientX, ev.clientY);
  trace({ ev: "down", level: S.level, seat: seat ? seat.id : null,
          at: seat ? [seat.c, seat.r] : null, len: seat ? seat.len : null,
          locked: seat ? !!seat.locked : null,
          occ: seat ? seat.occ.filter(v => v != null).length : null,
          places: seat ? placements(S, seat).length : null,
          walkers: S.anim.length, ptype: ev.pointerType, btn: ev.buttons });
  if (!seat) { trace({ ev: "refused", reason: "no seat under pointer" }); releaseHeld(); draw(); return; }
  /* The shell gets first refusal on the seat. It is how the jump booster works:
     armed, a tap on a seat is a passenger flying into it rather than the start
     of a drag. */
  if (onSeatPick(seat)) { releaseHeld(); draw(); return; }
  if (seat.locked) { trace({ ev: "refused", seat: seat.id, reason: "locked" }); bump(); say("Somebody is already walking to that seat."); releaseHeld(); draw(); return; }
  const targets = placements(S, seat);
  if (!targets.length) {                      // boxed in on every side
    trace({ ev: "refused", seat: seat.id, reason: "no placements" });
    bump(); say("No room beside that seat right now - shift a neighbour and try again.");
    releaseHeld(); draw(); return;
  }
  const w = pickWorld(ev.clientX, ev.clientY);
  HELD = { seat, w0: w, dx: 0, dz: 0, moved: false,
           x: ev.clientX, y: ev.clientY, targets };
  S.sel = seat;
  try { cv.setPointerCapture(ev.pointerId); } catch (e) {}
  draw();
});

cv.addEventListener("pointermove", ev => {
  if (!HELD) return;
  // A pointerup delivered outside the canvas used to be missed, leaving the seat
  // stuck to a cursor with no button down. No buttons means the gesture is over.
  if (ev.buttons === 0) { endDrag(ev); return; }
  if (!HELD.moved && Math.hypot(ev.clientX - HELD.x, ev.clientY - HELD.y) > 3) HELD.moved = true;
  const w = pickWorld(ev.clientX, ev.clientY);
  if (w && HELD.w0) { HELD.dx = w[0] - HELD.w0[0]; HELD.dz = w[1] - HELD.w0[1]; }
  draw();
});

function endDrag(ev) {
  if (!HELD) return;
  const h = HELD;
  let cell = h.moved ? dropCell() : null;
  if (cell && (h.seat.locked || !placements(S, h.seat)
        .some(([c, r]) => c === cell[0] && r === cell[1]))) {
    cell = null;                       // somebody set off for it mid-drag
    say("Somebody started walking to that seat - it has to stay put.");
    bump();
  }
  trace({ ev: "up", seat: h.seat.id, moved: h.moved,
          from: [h.seat.c, h.seat.r], hover: dropAt().map(v => +v.toFixed(2)),
          targets: h.targets.length, drop: cell, why: ev && ev.type });
  releaseHeld();
  if (cell) {
    place(S, h.seat, cell[0], cell[1]);
    S.moves++;
    onSeatMoved();                     // a booster charge is spent on the move, not the arming
    onHud(); draw();
    autoBoard();                       // whoever can now reach a seat gets on
  } else {
    draw();
  }
}
cv.addEventListener("pointerup", endDrag);
addEventListener("pointerup", endDrag);          // also when released off-canvas
cv.addEventListener("pointercancel", () => { releaseHeld(); draw(); });
addEventListener("pointercancel", () => { if (HELD) { releaseHeld(); draw(); } });
addEventListener("blur", () => { if (HELD) { releaseHeld(); draw(); } });

/** Walking distance from the door to a cell, through empty floor only. */
function floorDist(g, k) {
  const N = g.W * g.H, d = new Int32Array(N).fill(-1);
  const [DC, DR] = doorCell(g, k || 0);
  if (!isFree(g, DC, DR)) return d;
  const start = idx(g, DC, DR);
  d[start] = 0;
  const q = [[DC, DR]];
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

/** The one place a passenger can take without setting foot on the floor: a seat
    standing in the doorway itself. The seat is still a plug - nothing behind it
    is reachable while it sits there - but the passenger is stood right against
    it, and waiting to be told to move a seat they could simply have sat in reads
    as the game being broken rather than as a puzzle. */
function doorSeat(g, ci, door) {
  const [DC, DR] = doorCell(g, door || 0);
  const id = g.occ[idx(g, DC, DR)];
  if (id < 0) return null;                        // -1 is an empty cell
  const seat = g.seats[id];
  if (!seat || !accepts(seat, ci)) return null;
  for (let k = 0; k < seat.cap; k++) {
    if (seat.occ[k] != null || (seat.claim && seat.claim.has(k))) continue;
    // only the place that is actually in the doorway: the rest of a long seat is
    // inside the room, and there is no floor to walk round to it on
    const pc = placeCell(seat, k);
    if (pc[0] === DC && pc[1] === DR)
      return { seat, k, entry: null, door: door || 0 };
  }
  return null;
}

/** The nearest place a passenger can actually take: a seat, which of its places,
    and the floor tile they step in from. */
function pickSeat(g, ci, door) {
  door = door || 0;
  const plug = doorSeat(g, ci, door);
  if (plug) return plug;                          // null whenever the doorway is clear
  const d = floorDist(g, door);
  let best = null, bestD = Infinity;
  for (const seat of g.seats) {
    if (!accepts(seat, ci)) continue;
    for (let k = 0; k < seat.cap; k++) {
      if (seat.occ[k] != null || (seat.claim && seat.claim.has(k))) continue;
      for (const [nc, nr] of cellEntries(g, seat, k)) {
        const dist = d[idx(g, nc, nr)];
        if (dist >= 0 && dist < bestD) { bestD = dist; best = { seat, k, entry: [nc, nr], door }; }
      }
    }
  }
  return best;
}

/** Which line moves next, and through which door. Where both can move they take
    turns, so one does not empty while the other stands still. */
function nextUp(g) {
  const order = g.lastDoor === 0 ? [1, 0] : [0, 1];
  for (const k of order) {
    const q = queueOf(g, k);
    if (!q.length) continue;
    const spot = pickSeat(g, q[0], k);
    if (spot) return { door: k, ci: q[0], spot };
  }
  return null;
}

/** The tiles a passenger walks: door -> corridor -> the place itself. Rebuilt
    from the same BFS that decides reachability, so the route on screen is the
    route the rules used. */
function walkPath(g, seat, k, entry, door) {
  if (!entry) return null;        // straight off the step onto a seat in the doorway
  const d = floorDist(g, door || 0);
  const path = [entry.slice()];
  let [c, r] = entry;
  while (d[idx(g, c, r)] > 0) {
    for (const [dc, dr] of DIRS) {
      const nc = c + dc, nr = r + dr;
      if (!inBoard(g, nc, nr)) continue;
      if (d[idx(g, nc, nr)] === d[idx(g, c, r)] - 1) { c = nc; r = nr; path.push([c, r]); break; }
    }
  }
  path.reverse();
  path.push(placeCell(seat, k));
  return path;
}

/** Passengers board on their own. Nobody waits for the person in front to sit
    down: the moment the next in line can reach a free place they set off, so
    several are usually crossing the floor at once. The launches are staggered by
    one stride and nothing more. The player never taps a seat - they only slide
    seats. */
/* Nobody walks in while something is being explained over the board. It is a
   hold and not a stop: whatever asked for it calls autoBoard() again on the way
   out, and the queue picks up where it was. */
let HOLD = false;

function autoBoard(instant) {
  instant = instant || INSTANT;
  if (!S || S.phase !== "play") return;
  if (HOLD) return;
  if (S.boarding && !instant) return;
  const token = S.token;
  const stale = () => !S || S.token !== token;

  /* The tiles somebody is crossing. A union of every walker's route, not one
     walker's: there is more than one of them out there now. */
  const trackWalk = () => {
    const cells = new Set();
    for (const w of S.anim) for (const [c, r] of w.route || []) cells.add(c + "," + r);
    S.walkCells = cells.size ? cells : null;
  };

  /* Boarding ends when there is nothing left to launch AND the last walker has
     sat down. With one passenger at a time those were the same moment; they are
     not any more, and finishing on the first of them ends the level early. */
  const done = () => {
    if (stale() || S.launching || S.anim.length) return;
    S.boarding = false;
    onHud(); draw();
    if (!S.queue.length && !(S.queue2 || []).length && S.seated >= S.total) finish(true);
  };

  const launch = () => {
    if (stale()) return;
    S.launching = false;
    if (S.phase !== "play") { S.boarding = false; return; }
    if (!S.queue.length && !(S.queue2 || []).length) return done();
    const up = nextUp(S);
    if (!up) return done();
    const ci = up.ci, spot = up.spot, door = spot.door || 0;
    S.lastDoor = door;
    const seat = spot.seat, slot = spot.k;
    queueOf(S, door).shift();
    if (!instant) shuffleUp(S, door);     // whichever line just lost its head closes up
    seat.pending++;
    (seat.claim || (seat.claim = new Set())).add(slot);   // nobody else takes this place
    const cell = placeCell(seat, slot);
    seat.locked = true;             // no dragging a seat out from under a walker
    const sitDown = () => {
      seat.pending--;
      // a long seat can have a second passenger still on their way to it, and
      // unlocking on the first arrival let the player drag it out from under them
      seat.locked = seat.pending > 0;
      if (seat.claim) seat.claim.delete(slot);
      seat.occ[slot] = ci; S.seated++;
      onSeated();
    };
    if (instant) { sitDown(); launch(); return; }
    const path = walkPath(S, seat, slot, spot.entry, door) || [cell];
    const pts = [stopAt(S, door)];                                   // waiting at the stop
    for (const [c, r] of path) pts.push([cellW(c), cellZ(r)]);
    pts[pts.length - 1] = [cellW(cell[0]), cellZ(cell[1]) - .04];    // settle onto the seat

    // The last step is not a walk - it is a little hop up onto the seat, so split
    // it off and animate it separately.
    const hopTo = pts.pop();
    const hopFrom = pts[pts.length - 1];

    let total = 0;
    const seg = [];
    for (let i = 1; i < pts.length; i++) {
      const L = Math.hypot(pts[i][0] - pts[i-1][0], pts[i][1] - pts[i-1][1]);
      seg.push(L); total += L;
    }
    const a = { ci, x: pts[0][0], z: pts[0][1], y: 0, route: path, facing: "d", phase: 0 };
    S.anim.push(a);
    trackWalk();
    S.boarding = true;
    // The next passenger leaves now, not when this one sits. One stagger of
    // BASE_GAP_MS is about one cell at walking pace, which is the gap you would
    // leave yourself; with no stagger the queue empties as a single clump.
    S.launching = true;
    setTimeout(launch, BASE_GAP_MS / SPEED);

    const faceOf = (dx, dz) => (Math.abs(dx) > Math.abs(dz) ? (dx > 0 ? "r" : "l") : (dz > 0 ? "d" : "u"));

    const hop = () => {
      const dx = hopTo[0] - hopFrom[0], dz = hopTo[1] - hopFrom[1];
      a.facing = faceOf(dx, dz);
      const h0 = performance.now(), hd = HOP_MS / SPEED;
      const tickHop = now => {
        if (stale()) return;
        const t = Math.min(1, (now - h0) / hd);
        const e = t * t * (3 - 2 * t);                  // ease in and out of the jump
        a.x = hopFrom[0] + dx * e;
        a.z = hopFrom[1] + dz * e;
        a.y = Math.sin(t * Math.PI) * .42;              // up and over
        a.phase = t < .5 ? 1 : 3;                       // legs tucked, then out to land
        draw();
        if (t < 1) requestAnimationFrame(tickHop);
        else {
          S.anim.splice(S.anim.indexOf(a), 1);
          trackWalk();
          sitDown();
          onHud(); draw();
          // A slide made while this one was still walking found boarding already
          // true and did nothing. Try again on the way down, or a path opened
          // mid-walk would sit unused until the player moved a second time.
          if (S.queue.length && !S.launching) {
            S.launching = true;
            setTimeout(launch, BASE_GAP_MS / SPEED);
          } else done();
        }
      };
      requestAnimationFrame(tickHop);
    };

    if (total < 1e-6) { hop(); return; }

    const dur = Math.max(MIN_WALK_MS, total * BASE_MS_PER_UNIT * walkPace(S)) / SPEED;
    const t0 = performance.now();
    const tick2 = now => {
      if (stale()) return;
      const t = Math.min(1, (now - t0) / dur);
      let want = t * total, i = 0;
      while (i < seg.length - 1 && want > seg[i]) { want -= seg[i]; i++; }
      const f = seg[i] ? Math.min(1, want / seg[i]) : 1;
      a.x = pts[i][0] + (pts[i+1][0] - pts[i][0]) * f;
      a.z = pts[i][1] + (pts[i+1][1] - pts[i][1]) * f;
      const dx = pts[i+1][0] - pts[i][0], dz = pts[i+1][1] - pts[i][1];
      if (Math.abs(dx) > 1e-6 || Math.abs(dz) > 1e-6) a.facing = faceOf(dx, dz);
      a.phase = Math.floor((t * total) / STRIDE) % WMETA.phases;   // legs cycle with distance
      a.y = Math.abs(Math.sin(t * Math.PI * Math.max(2, seg.length))) * .10;
      draw();
      if (t < 1) requestAnimationFrame(tick2); else hop();
    };
    requestAnimationFrame(tick2);
  };
  launch();
}

/* ---- the jump booster ---------------------------------------------------
   A jump is not a seat that moves - it is a passenger that flies. The player
   picks a seat the front of the queue can sit in, and they go straight to it
   over the top of whatever is in the way. That is the whole point of it: the
   seat that would win the board is usually the one nothing can walk to, and a
   booster that only slides a seat is a booster that does what dragging already
   does.

   Everything except the route is ordinary boarding - the same claim on the
   place, the same lock while they are in the air, the same landing - so a jump
   in the middle of a queue that is already walking does not need its own
   bookkeeping. */
const FLY_MS = 620;                // how long the flight takes at normal speed
const FLY_UP = 1.6;                // how high it arcs, in cells: clear of everything

/** The place the front of the queue could take on this seat, or -1. */
function freeSlot(seat) {
  for (let k = 0; k < seat.cap; k++)
    if (seat.occ[k] == null && !(seat.claim && seat.claim.has(k))) return k;
  return -1;
}

/** The add-line booster: one more column of floor down the left-hand side.

    The board is not being invented wider - it is being let out to the width the
    panel already has. Every SeatPanel in the bundle carries an extra grid strip
    on its lowest-x column with scaleX 0, switched off, and nothing in 2676
    levels ever puts a seat, a hole or an obstacle there. convert_163.py drops
    that column on the way in; this hands it back.

    One per board, because one is all the panel has. The door stays where it is:
    it is drawn at column W-1, everything shifted right by one, so the cell under
    it moved with it.

    ⚠ Refused while anybody is walking. A walker's path is world coordinates
    worked out when they set off, and widening the board moves every cell under
    their feet. It costs nothing in practice - the booster is for a board that
    has stopped, which is a board with nobody on the floor. */
function addLine(g) {
  if (!g || g.phase !== "play") return false;
  if (g.anim.length || g.launching || g.lines) return false;
  const W = g.W + 1;
  const hole = new Uint8Array(W * g.H);
  for (let r = 0; r < g.H; r++)
    for (let c = 0; c < g.W; c++) hole[r * W + c + 1] = g.hole[r * g.W + c];
  for (const b of g.seats) b.c++;
  /* ⚠ The doorway steps right with everything else. g.doors is fixed when the
     board loads, as [[W-1, row]] for the near door and [0, row] for the far one,
     and every seat moves one column right here. A near door left on the old W-1
     is an interior cell with a seat now standing on it: reachRegion finds the
     door blocked, nobody can walk in, and the booster the player just paid for
     is what made the board unwinnable. The far door is already on column 0 and
     stays there - the new lane becomes the outer edge on that side. */
  if (g.doors) for (const d of g.doors) if (d[0] === g.W - 1) d[0] = W - 1;
  g.W = W; g.hole = hole; g.lines = 1;
  g.occ = new Int16Array(W * g.H).fill(-1);
  for (const b of g.seats) for (const [c, r] of cellsOf(b)) g.occ[idx(g, c, r)] = b.id;
  g.sel = null; g.drag = null; g.walkCells = null;
  fitCanvas(g); LAY = layout();
  return true;
}

/** Fly the front of the queue into `seat`. False when they cannot sit there,
    which leaves the booster armed for another try rather than eating it. */
function jumpBoard(g, seat) {
  if (!g || g.phase !== "play" || !g.queue.length || !seat) return false;
  const ci = g.queue[0];
  if (!accepts(seat, ci)) return false;
  const slot = freeSlot(seat);
  if (slot < 0) return false;

  g.queue.shift();
  shuffleUp(g);                          // the rest of the line steps up
  seat.pending++;
  (seat.claim || (seat.claim = new Set())).add(slot);
  seat.locked = true;                    // not while somebody is on their way in
  const cell = placeCell(seat, slot);
  const from = [cellW(g.W - 1) + SX * 2.0, cellZ(g.door)];   // the spot at the door
  const to = [cellW(cell[0]), cellZ(cell[1]) - .04];
  const a = { ci, x: from[0], z: from[1], y: 0, route: null, facing: "l", phase: 1 };
  g.anim.push(a);

  const token = g.token, t0 = performance.now(), dur = FLY_MS / SPEED;
  const tick = now => {
    if (!S || S.token !== token) return;
    const t = Math.min(1, (now - t0) / dur);
    const e = t * t * (3 - 2 * t);
    a.x = from[0] + (to[0] - from[0]) * e;
    a.z = from[1] + (to[1] - from[1]) * e;
    a.y = Math.sin(t * Math.PI) * FLY_UP;
    a.phase = t < .5 ? 1 : 3;            // legs tucked on the way up, out to land
    draw();
    if (t < 1) return requestAnimationFrame(tick);
    S.anim.splice(S.anim.indexOf(a), 1);
    seat.pending--;
    seat.locked = seat.pending > 0;
    if (seat.claim) seat.claim.delete(slot);
    seat.occ[slot] = ci; S.seated++;
    onSeated();
    onHud(); draw();
    /* Whoever else can now reach a seat gets on, and the board is finished here
       if that was the last of them. autoBoard() steps aside when a queue is
       already walking; that chain does the same check when it lands. */
    autoBoard();
  };
  requestAnimationFrame(tick);
  return true;
}

/* The three things only the surrounding page can answer. A shell assigns
   these; the engine never reaches into the DOM around the canvas itself. */
let onHud = () => {};
let onSay = () => {};
let onFinish = () => {};
let onNewLevel = () => {};
let onSeatMoved = () => {};
let onSeatPick = () => false;    // true = the shell has taken this tap
let onSeated = () => {};         // a passenger has just taken a place
let onOverlay = () => {};        // coach marks: drawn last, over everything
function say(msg) { onSay(msg); }
function bump() { cv.animate([{ filter: "none" }, { filter: "brightness(1.15)" }, { filter: "none" }], { duration: 200 }); }

function finish(won) {
  /* ⚠ A level ends once. `done()` has no phase test of its own - it fires when
     the last walker sits down, which can be after the clock has already run out
     and taken the level with it. That paid the purse and unlocked the next level
     on top of a loss that had just cost a life and broken the streak. The guard
     belongs here rather than in `done()` because every ending comes through this
     door: the clock, the last seat, and ?win=1. */
  if (!S || S.phase !== "play") return;
  S.phase = won ? "win" : "lose";
  onFinish(won);
}
function fmt(sec) { sec = Math.max(0, Math.ceil(sec));
  return Math.floor(sec / 60) + ":" + String(sec % 60).padStart(2, "0"); }
