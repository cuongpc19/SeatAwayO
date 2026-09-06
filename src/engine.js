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
const OPEN_MS = 2000;      // the pause between a board appearing and the queue starting
/* Walking pace. These three move together: taking one without the others gives
   a passenger who strides across the floor and then dawdles onto the seat, or a
   short walk that ignores the change entirely because it lands on the floor.

   260, 300 and 520 are the numbers measured off the recording. The game runs
   quicker than the recording by 1.15 x 1.20 x 1.20 = 1.656, and each is that
   measurement divided by 1.656 - always recomputed from the original rather than
   from the last value, or the rounding creeps further off with every pass.

   The walk cycle needs nothing here: `a.phase` counts STRIDE off the distance
   covered, so the legs step faster on their own and stay in step with the floor
   rather than skating over it. */
const BASE_MS_PER_UNIT = 157;                       // ms per grid unit walked
const MIN_WALK_MS = 314;                            // a walk is never snappier than this
const HOP_MS = 181;                                 // the little jump onto the seat

const BASE_GAP_MS = 260;                            // pause between passengers - waiting, not walking
const STRIDE = 0.52;                                // world units per animation frame
const QUEUE_PITCH = 1.15;                           // world units between two people in line
const QUEUE_STEP_MS = QUEUE_PITCH * BASE_MS_PER_UNIT;   // one place up the line, at walking pace
const QUEUE_GAP_MS = 110;                           // before the person behind follows
const idx = (g, c, r) => r * g.W + c;
const inBoard = (g, c, r) => c >= 0 && c < g.W && r >= 0 && r < g.H && !g.hole[idx(g, c, r)];
const isFree = (g, c, r) => inBoard(g, c, r) && g.occ[idx(g, c, r)] < 0;

/** The grid cells a seat covers. SeatDirect 0 and 2 lie along x, 1 and 3 along z. */
function cellsOf(b) {
  const a = [];
  for (let k = 0; k < b.len; k++) a.push(b.dir & 1 ? [b.c, b.r + k] : [b.c + k, b.r]);
  return a;
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
  const [c, r] = cellsOf(b)[k];
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
  for (let k = 0; k < b.len; k++)
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
function reachRegion(g) {
  const seen = new Uint8Array(g.W * g.H);
  if (!isFree(g, g.W - 1, g.door)) return seen;
  seen[idx(g, g.W - 1, g.door)] = 1;
  const st = [[g.W - 1, g.door]];
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
    id: i, c: s[0], r: s[1], len: s[2], colour: s[3],
    dir: s[4] | 0,                                  // SeatDirect 0..3, straight from the APK
    occ: new Array(s[2]).fill(null),                // one place per cell
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
  g.total = g.queue.length;
  g.colours = new Set(raw.queue).size;
  g.time = raw.time; g.left = raw.time;
  g.seated = 0; g.phase = "play"; g.moves = 0; g.walkCells = null;
  g.sel = null; g.drag = null; g.anim = []; g.qstep = null;
  S = g;
  S.boarding = false; S.launching = false;
  fitCanvas(g);
  LAY = layout();
  onNewLevel();                 // each shell clears its own end-of-level card
  onHud(); draw();
  /* A beat before anybody moves. Boarding used to start on the same frame the
     board appeared, so on a level where the queue can walk straight in - level 1
     is one - the first passenger was already sitting down before the player had
     looked at the screen, and the hop that teaches the whole game went unseen.
     INSTANT keeps its synchronous path: headless play-throughs read S.seated on
     the next line and cannot wait out a timer. */
  if (INSTANT) autoBoard();
  else {
    const token = S.token;
    setTimeout(() => { if (S && S.token === token) autoBoard(); }, OPEN_MS / SPEED);
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
function shuffleUp(g) {
  const now = performance.now(), was = g.qstep;
  //  was[i + 1] is this same person a moment ago: the line has already shifted,
  //  so what is now place i held place i + 1 when that state was written.
  g.qstep = g.queue.map((_, i) => {
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
    if (S !== g || !g.qstep) { g.qraf = false; return; }
    const now2 = performance.now();
    if (g.qstep.some(st => placesBack(st, now2) > 1e-3)) { draw(); requestAnimationFrame(tick); }
    else { g.qstep = null; g.qraf = false; draw(); }
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
  const high = RICH ? 1.55 : 2.2;
  const x0 = -(g.W - 1) / 2 * SX, z0 = -(g.H - 1) / 2 * SZ;
  const pts = [];
  for (const [cc, rr] of [[-pad, -pad], [g.W - 1 + right, -pad],
                          [-pad, g.H - 1 + pad], [g.W - 1 + right, g.H - 1 + pad]])
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
  const head = (THEMES[THEME] || THEMES.station).head;
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
    const c = [view(-gx, 0, -gz), view(rx, 0, -gz), view(-gx, 0, gz), view(rx, 0, gz)];
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
  const v = view(x, y, z);
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
const riderFrame = (b, ci) => "r" + b.dir + "_" + (SPRITE[colName(ci)] || "grey");

/** Frames carry their own size and origin: [x, y, w, h, pivotX, pivotY]. */
function blit(frame, wx, wy, wz, alpha) {
  const f = META.frames[frame]; if (!f) return;
  const [px, py] = P(wx, wy, wz);
  const k = LAY.s / META.scale;
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
  return [T, B, L, R];
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
  const { x0, x1, OX, gx0, gx1, gz0, gz1 } = E;

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

/* head  - fraction of the canvas left empty above the room, so that whatever a
           theme puts beyond the far wall has somewhere to go
   page  - what the shell paints behind the canvas, for the strip it never covers
   plate - true if a ?bg= plate may stand in for this theme's outside          */
const THEMES = {
  station: {
    head: .09, plate: true, outside: drawStation,
    skin: { wall: ROOM.livery, trim: ROOM.trim, top: ROOM.liveryTop, lip: ROOM.liveryLip,
            fa: ROOM.floorA, fb: ROOM.floorB, grout: ROOM.grout, glass: ROOM.glass,
            door: ROOM.mat },
  },
  cinema: {
    head: .27, page: CINEMA.outside, outside: drawCinema,
    skin: { wall: CINEMA.wall, trim: CINEMA.trim, top: CINEMA.wallLip, lip: CINEMA.grout,
            fa: CINEMA.carpetA, fb: CINEMA.carpetB, grout: CINEMA.grout, glass: null,
            door: CINEMA.wallLip },
  },
  stadium: {
    head: .22, page: STADIUM.night, outside: drawStadium,
    skin: { wall: STADIUM.wall, trim: STADIUM.trim, top: STADIUM.wallLip, lip: STADIUM.grout,
            fa: STADIUM.deckA, fb: STADIUM.deckB, grout: STADIUM.grout, glass: null,
            door: STADIUM.nosing },
  },
  concert: {
    head: .24, page: CONCERT.dark, outside: drawConcert,
    skin: { wall: CONCERT.wall, trim: CONCERT.trim, top: CONCERT.wallLip, lip: CONCERT.grout,
            fa: CONCERT.parqA, fb: CONCERT.parqB, grout: CONCERT.grout, glass: null,
            door: CONCERT.stageLip },
  },
  classroom: {
    head: .20, page: CLASSROOM.lino, outside: drawClassroom,
    skin: { wall: CLASSROOM.wall, trim: CLASSROOM.trim, top: CLASSROOM.wallLip,
            lip: CLASSROOM.grout, fa: CLASSROOM.linoA, fb: CLASSROOM.linoB,
            grout: CLASSROOM.grout, glass: null, door: CLASSROOM.tray },
  },
};

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

  // ---- outside the room ----
  const gx0 = x0 - T - SX * 9, gx1 = x1 + T + SX * 9;
  const gz0 = z0 - T - SZ * 9, gz1 = z1 + T + SZ * 9;
  const TH = THEMES[THEME] || THEMES.station;
  // A painted plate stands in for the station ground and nothing else: the other
  // themes draw a whole building out there, which no ground tile can replace.
  if (!(painted && TH.plate))
    TH.outside({ g, x0, x1, z0, z1, T, H, OX, dz0, dz1, gx0, gx1, gz0, gz1 });

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
  // the inner faces of the walls, seen almost edge-on: a dark lip is what sells them
  const L = .17;
  slab(x0 - L, z0 - L, x1 + L, z0, .0, SKIN.lip);
  slab(x0 - L, z1, x1 + L, z1 + L, .0, SKIN.lip);
  slab(x0 - L, z0, x0, z1, .0, SKIN.lip);
  slab(x1, z0, x1 + L, dz0, .0, SKIN.lip);
  slab(x1, dz1, x1 + L, z1 + L, .0, SKIN.lip);

  // ---- the doorway ----
  // One cut, at wall height, and nothing else. The threshold and the step were
  // drawn at floor level, so under this camera they landed BELOW the cut and the
  // three of them stacked up into bars across the way in.
  slab(x1 - .02, dz0, OX + .02, dz1, H + .004, SKIN.door);
}

function draw() {
  if (!S) return;
  const g = S;
  fitCanvas(g);
  LAY = layout();
  if (!ready) return;
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

  const region = reachRegion(g);
  const nextCol = g.queue.length ? g.queue[0] : -1;
  const doorBlocked = !isFree(g, g.W - 1, g.door);
  g.nextSeat = g.queue.length ? pickSeat(g, g.queue[0]) : null;

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
    push(sx, sz, () => { shadow(sx, sz, .45 * b.len); blit(seatFrame(b), sx, 0, sz, 1); });
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
      const [c, r] = cellsOf(b)[i];
      push(cellW(c), cellZ(r), () => blit(riderFrame(b, ci), cellW(c), .05, cellZ(r) - .04), .3);
    });
  }

  // the stop
  const laneX = cellW(g.W - 1) + SX * 2.0, qnow = performance.now();
  for (let i = 0; i < Math.min(g.queue.length, 7); i++) {
    const st = g.qstep && g.qstep[i];
    const back = st ? placesBack(st, qnow) : 0;       // places still to walk
    // Waiting your turn is not walking: until t0 comes round you are carrying the
    // whole place and standing still, and drawing that as a walk frame turns the
    // back half of the line to face away for as long as anyone is boarding.
    const walking = back > 1e-3 && qnow >= st.t0;
    const pos = i + back, wz = cellZ(g.door) + pos * QUEUE_PITCH;
    const nm = SPRITE[colName(g.queue[i])] || "grey";
    // Faded by where they stand rather than by which place they hold, so someone
    // coming forward brightens as they arrive instead of on the frame they shift.
    const a = Math.max(.4, 1 - pos * .11);
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
    shadow(sx + gdx, sz + gdz, .45 * held.len);
    blit(seatFrame(held), sx + gdx, 0, sz + gdz, A);
    held.occ.forEach((ci, i) => {
      if (ci == null) return;
      const [c, r] = cellsOf(held)[i];
      blit(riderFrame(held, ci), cellW(c) + gdx, .05, cellZ(r) + gdz - .04, A);
    });
  }

  if (g.sel) {
    for (const [c, r] of cellsOf(g.sel)) {
      ctx.save(); ctx.globalAlpha = .30;
      quad(tileQuad(c, r, .016), "#ffe9a8"); ctx.restore();
    }
  }

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
      const [c, r] = cellsOf(b)[i];
      if (spriteHit(riderFrame(b, ci), cellW(c), .05, cellZ(r) - .04, X, Y))
        take(b, view(cellW(c), 0, cellZ(r))[2] + .3);
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
function floorDist(g) {
  const N = g.W * g.H, d = new Int32Array(N).fill(-1);
  if (!isFree(g, g.W - 1, g.door)) return d;
  const start = idx(g, g.W - 1, g.door);
  d[start] = 0;
  const q = [[g.W - 1, g.door]];
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
function doorSeat(g, ci) {
  const id = g.occ[idx(g, g.W - 1, g.door)];
  if (id < 0) return null;                        // -1 is an empty cell
  const seat = g.seats[id];
  if (!seat || !accepts(seat, ci)) return null;
  const cells = cellsOf(seat);
  for (let k = 0; k < seat.len; k++) {
    if (seat.occ[k] != null || (seat.claim && seat.claim.has(k))) continue;
    // only the place that is actually in the doorway: the rest of a long seat is
    // inside the room, and there is no floor to walk round to it on
    if (cells[k][0] === g.W - 1 && cells[k][1] === g.door)
      return { seat, k, entry: null };            // no entry tile: they step straight up
  }
  return null;
}

/** The nearest place a passenger can actually take: a seat, which of its places,
    and the floor tile they step in from. */
function pickSeat(g, ci) {
  const plug = doorSeat(g, ci);
  if (plug) return plug;                          // null whenever the doorway is clear
  const d = floorDist(g);
  let best = null, bestD = Infinity;
  for (const seat of g.seats) {
    if (!accepts(seat, ci)) continue;
    for (let k = 0; k < seat.len; k++) {
      if (seat.occ[k] != null || (seat.claim && seat.claim.has(k))) continue;
      for (const [nc, nr] of cellEntries(g, seat, k)) {
        const dist = d[idx(g, nc, nr)];
        if (dist >= 0 && dist < bestD) { bestD = dist; best = { seat, k, entry: [nc, nr] }; }
      }
    }
  }
  return best;
}

/** The tiles a passenger walks: door -> corridor -> the place itself. Rebuilt
    from the same BFS that decides reachability, so the route on screen is the
    route the rules used. */
function walkPath(g, seat, k, entry) {
  if (!entry) return null;        // straight off the step onto a seat in the doorway
  const d = floorDist(g);
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
  path.push(cellsOf(seat)[k]);
  return path;
}

/** Passengers board on their own. Nobody waits for the person in front to sit
    down: the moment the next in line can reach a free place they set off, so
    several are usually crossing the floor at once. The launches are staggered by
    one stride and nothing more. The player never taps a seat - they only slide
    seats. */
function autoBoard(instant) {
  instant = instant || INSTANT;
  if (!S || S.phase !== "play") return;
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
    if (!S.queue.length && S.seated >= S.total) finish(true);
  };

  const launch = () => {
    if (stale()) return;
    S.launching = false;
    if (S.phase !== "play") { S.boarding = false; return; }
    if (!S.queue.length) return done();
    const ci = S.queue[0];
    const spot = pickSeat(S, ci);
    if (!spot) return done();
    const seat = spot.seat, slot = spot.k;
    S.queue.shift();
    if (!instant) shuffleUp(S);          // the rest of the line steps up
    seat.pending++;
    (seat.claim || (seat.claim = new Set())).add(slot);   // nobody else takes this place
    const cell = cellsOf(seat)[slot];
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
    const path = walkPath(S, seat, slot, spot.entry) || [cell];
    const pts = [[cellW(S.W - 1) + SX * 2.0, cellZ(S.door)]];        // waiting at the stop
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

    const dur = Math.max(MIN_WALK_MS, total * BASE_MS_PER_UNIT) / SPEED;
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

/* The three things only the surrounding page can answer. A shell assigns
   these; the engine never reaches into the DOM around the canvas itself. */
let onHud = () => {};
let onSay = () => {};
let onFinish = () => {};
let onNewLevel = () => {};
let onSeatMoved = () => {};
let onSeated = () => {};         // a passenger has just taken a place
let onOverlay = () => {};        // coach marks: drawn last, over everything
function say(msg) { onSay(msg); }
function bump() { cv.animate([{ filter: "none" }, { filter: "brightness(1.15)" }, { filter: "none" }], { duration: 200 }); }

function finish(won) {
  S.phase = won ? "win" : "lose";
  onFinish(won);
}
function fmt(sec) { sec = Math.max(0, Math.ceil(sec));
  return Math.floor(sec / 60) + ":" + String(sec % 60).padStart(2, "0"); }
