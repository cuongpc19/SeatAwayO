import re
p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

# ============ 1. atlas plumbing ============
s = s.replace('const META = /*__META__*/;\nconst ATLAS_SRC = "data:image/png;base64,/*__ATLAS__*/";',
              'const META = /*__META__*/;\nconst ATLAS_SRC = "data:image/png;base64,/*__ATLAS__*/";')
s = s.replace('function blit(frame, wx, wy, wz, alpha, mul) {\n'
              '  const f = META.frames[frame]; if (!f) return;\n'
              '  const [px, py] = P(wx, wy, wz);\n'
              '  const k = LAY.s / META.scale * (mul || 1);\n'
              '  ctx.globalAlpha = alpha == null ? 1 : alpha;\n'
              '  ctx.drawImage(atlas, f[0], f[1], META.tile, META.tile,\n'
              '                px - META.pivot[0] * k, py - META.pivot[1] * k, META.tile * k, META.tile * k);\n'
              '  ctx.globalAlpha = 1;\n'
              '}',
              '/** Frames carry their own size and origin: [x, y, w, h, pivotX, pivotY]. */\n'
              'function blit(frame, wx, wy, wz, alpha) {\n'
              '  const f = META.frames[frame]; if (!f) return;\n'
              '  const [px, py] = P(wx, wy, wz);\n'
              '  const k = LAY.s / META.scale;\n'
              '  ctx.globalAlpha = alpha == null ? 1 : alpha;\n'
              '  ctx.drawImage(atlas, f[0], f[1], f[2], f[3],\n'
              '                px - f[4] * k, py - f[5] * k, f[2] * k, f[3] * k);\n'
              '  ctx.globalAlpha = 1;\n'
              '}')

# ============ 2. seat geometry, facing and boarding rules ============
OLD = s[s.index("function cellsOf(b) {"):s.index("/** Where this seat can slide to, one cell at a time through the empty floor. */")]
NEW = '''/** The grid cells a seat covers. SeatDirect 0 and 2 lie along x, 1 and 3 along z. */
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
function fits(g, b, c, r) {
  const save = [b.c, b.r];
  b.c = c; b.r = r;
  const cs = cellsOf(b);
  b.c = save[0]; b.r = save[1];
  for (const [cc, rr] of cs) {
    if (!inBoard(g, cc, rr)) return false;
    if (cc === g.W - 1 && rr === g.door) return false;      // doorway stays clear
    const id = g.occ[idx(g, cc, rr)];
    if (id >= 0 && id !== b.id) return false;
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
const accepts = (b, ci) =>
  freeSlots(b) > (b.pending || 0) && (b.colour === 0 || b.colour === ci);
function canSeat(g, b, ci, region) { return accepts(b, ci) && touches(g, b, region || reachRegion(g)); }

'''
s = s[:s.index("function cellsOf(b) {")] + NEW + s[s.index("/** Where this seat can slide to, one cell at a time through the empty floor. */"):]

# the old standalone place/fits/reachRegion/touches/accepts/canSeat are now duplicated - drop them
for dead in [
  "function place(g, b, c, r) {\n  for (const [cc, rr] of cellsOf(b)) g.occ[idx(g, cc, rr)] = -1;\n  b.c = c; b.r = r;\n  for (const [cc, rr] of cellsOf(b)) g.occ[idx(g, cc, rr)] = b.id;\n}\n",
]:
    pass

# ============ 3. choose a specific place, and walk to it ============
OLD2 = s[s.index("/** The tiles a passenger actually walks"):s.index("/** Passengers board on their own")]
NEW2 = '''/** The nearest place a passenger can actually take: a seat, which of its places,
    and the floor tile they step in from. */
function pickSeat(g, ci) {
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

'''
s = s[:s.index("/** The tiles a passenger actually walks")] + NEW2 + s[s.index("/** Passengers board on their own"):]

open(p, "w", encoding="utf-8").write(s)
print("geometry + boarding rules rewritten")
