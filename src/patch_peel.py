p = "game2_core.js"
s = open(p, encoding="utf-8").read()

a = s.index("  while (sim.benches.some(b => !b.gone) && guard++ < budget) {")
b = s.index("  if (sim.benches.some(b => !b.gone) && !force) return null;")

NEW = '''  const seatOn = (bench) => {
    const colour = bench.colour === "grey" ? pool[Math.floor(rand() * pool.length)] : bench.colour;
    queue.push(colour); plan.push(bench.id);
    bench.occ.push(colour);
    if (bench.occ.length >= bench.len) clearBench(sim, bench);
  };
  /** Slide `bench` to the first placement that puts it against the corridor. */
  const digOut = (bench) => {
    for (const [c, r] of placements(sim, bench, 220)) {
      const save = [bench.c, bench.r];
      moveBench(sim, bench, c, r);
      if (benchTouches(sim, bench, reachRegion(sim))) return true;
      moveBench(sim, bench, save[0], save[1]);
    }
    return false;
  };

  while (sim.benches.some(b => !b.gone) && guard++ < budget) {
    const region = reachRegion(sim);
    const open = sim.benches.filter(b => !b.gone && b.occ.length < b.len);
    const cand = open.filter(b => benchTouches(sim, b, region));
    const buried = open.filter(b => !cand.includes(b));

    // Deliberately call on a walled-off bench now and then. Without this the queue
    // only ever asks for benches already against the corridor, and nothing on the
    // board ever has to be rearranged.
    let handled = false;
    if (buried.length && (!cand.length || rand() < p.movePct)) {
      for (const bench of shuffle(buried.slice(), rand)) {
        if (!digOut(bench)) continue;
        moves++; seatOn(bench); handled = true; break;
      }
    }
    if (handled) continue;

    if (cand.length) { seatOn(cand[Math.floor(rand() * cand.length)]); continue; }

    // fully stuck: shove anything aside until some bench opens up
    let freed = false;
    for (const other of shuffle(sim.benches.filter(x => !x.gone), rand)) {
      for (const [c, r] of placements(sim, other, 160)) {
        const save = [other.c, other.r];
        moveBench(sim, other, c, r);
        const reg = reachRegion(sim);
        if (open.some(x => !x.gone && benchTouches(sim, x, reg))) { freed = true; moves++; break; }
        moveBench(sim, other, save[0], save[1]);
      }
      if (freed) break;
    }
    if (!freed) return force ? finish() : null;
  }
'''

s = s[:a] + NEW + s[b:]
open(p, "w", encoding="utf-8").write(s)
print("peel loop rewritten")
