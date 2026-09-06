p = "game2_core.js"
s = open(p, encoding="utf-8").read()

# ---- new helpers, inserted before the solver section ----
HELPERS = '''
/** 0-1 BFS from the corridor: how many benches still stand between the queue
    and this bench. 0 means it can be walked to right now. */
function benchDepth(g, target) {
  const N = g.W * g.H, INF = 1e9;
  const dist = new Int32Array(N).fill(INF);
  const dq = [];
  for (let r = 0; r < g.H; r++) {
    if (isFree(g, g.W - 1, r)) { dist[r * g.W + g.W - 1] = 0; dq.push(r * g.W + g.W - 1); }
  }
  // plain Dijkstra on a 0/1 graph, small boards so a sorted scan is fine
  const seen = new Uint8Array(N);
  while (dq.length) {
    let bi = 0;
    for (let i = 1; i < dq.length; i++) if (dist[dq[i]] < dist[dq[bi]]) bi = i;
    const cur = dq.splice(bi, 1)[0];
    if (seen[cur]) continue;
    seen[cur] = 1;
    const c = cur % g.W, r = (cur / g.W) | 0;
    for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nc = c + dc, nr = r + dr;
      if (nc < 0 || nc >= g.W || nr < 0 || nr >= g.H) continue;
      const ni = nr * g.W + nc;
      const id = g.occ[ni];
      const w = id < 0 ? 0 : 1;
      if (dist[cur] + w < dist[ni]) { dist[ni] = dist[cur] + w; dq.push(ni); }
    }
  }
  let best = INF;
  for (let k = 0; k < target.len; k++) {
    const c = target.c + k, r = target.r;
    for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nc = c + dc, nr = r + dr;
      if (nc < 0 || nc >= g.W || nr < 0 || nr >= g.H) continue;
      best = Math.min(best, dist[nr * g.W + nc]);
    }
  }
  return best;
}

/** Slide benches until `target` can be walked to. Returns moves used, or -1.
    Only benches touching the corridor can move at all, so that is all we try. */
function digTo(g, target, maxMoves) {
  const used = [];
  for (let step = 0; step < maxMoves; step++) {
    if (benchTouches(g, target, reachRegion(g))) return used;
    const cur = benchDepth(g, target);
    const region = reachRegion(g);
    let best = null, bestD = cur;
    for (const b of g.benches) {
      if (b.gone || b.id === target.id) continue;
      if (!benchTouches(g, b, region)) continue;          // walled in, cannot move
      const save = [b.c, b.r];
      for (const [c, r] of placements(g, b, 40)) {
        moveBench(g, b, c, r);
        const d = benchDepth(g, target);
        moveBench(g, b, save[0], save[1]);
        if (d < bestD) { bestD = d; best = [b, c, r]; }
      }
    }
    if (!best) return -1;
    moveBench(g, best[0], best[1], best[2]);
    used.push([best[0].id, best[1], best[2]]);
  }
  return benchTouches(g, target, reachRegion(g)) ? used : -1;
}
'''

anchor = "/* ---------------- solver / hint ---------------- */"
s = s.replace(anchor, HELPERS + "\n" + anchor)

# ---- use it in the peel loop ----
OLD = """  /** Slide `bench` to the first placement that puts it against the corridor. */
  const digOut = (bench) => {
    for (const [c, r] of placements(sim, bench, 220)) {
      const save = [bench.c, bench.r];
      moveBench(sim, bench, c, r);
      if (benchTouches(sim, bench, reachRegion(sim))) return true;
      moveBench(sim, bench, save[0], save[1]);
    }
    return false;
  };"""
NEW = """  /** Dig a corridor to `bench`, shallowest targets first. */
  const digOut = (bench) => {
    const r = digTo(sim, bench, 6);
    return r === -1 ? false : r.length;
  };"""
assert OLD in s
s = s.replace(OLD, NEW)

OLD2 = """      for (const bench of shuffle(buried.slice(), rand)) {
        if (!digOut(bench)) continue;
        moves++; seatOn(bench); handled = true; break;
      }"""
NEW2 = """      // shallowest first - a bench two rows deep is a fair ask, ten is not
      const byDepth = buried.map(b => [b, benchDepth(sim, b)])
                            .filter(([, d]) => d > 0 && d <= 3)
                            .sort((x, y) => x[1] - y[1]);
      for (const [bench] of byDepth) {
        const used = digOut(bench);
        if (used === false) continue;
        moves += used; seatOn(bench); handled = true; break;
      }"""
assert OLD2 in s
s = s.replace(OLD2, NEW2)

open(p, "w", encoding="utf-8").write(s)
print("patched: multi-step digging")
