p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

a = s.index("    const path = walkPath(S, seat) || [cell];")
b = s.index("    S.boarding = true;")

NEW = '''    const path = walkPath(S, seat) || [cell];
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

    const faceOf = (dx, dz) => (Math.abs(dx) > Math.abs(dz) ? (dx > 0 ? "r" : "l") : (dz > 0 ? "d" : "u"));

    const hop = () => {
      const dx = hopTo[0] - hopFrom[0], dz = hopTo[1] - hopFrom[1];
      a.facing = faceOf(dx, dz);
      const h0 = performance.now(), hd = HOP_MS / SPEED;
      const tickHop = now => {
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
          seat.pending--; seat.occ.push(ci); S.seated++;
          hud(); draw();
          setTimeout(step, BASE_GAP_MS / SPEED);
        }
      };
      requestAnimationFrame(tickHop);
    };

    if (total < 1e-6) { hop(); S.boarding = true; return; }

    const dur = Math.max(520, total * BASE_MS_PER_UNIT) / SPEED;
    const t0 = performance.now();
    const tick2 = now => {
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
'''
s = s[:a] + NEW + s[b:]

s = s.replace("const STRIDE = 0.52;                                // world units per animation frame",
              "const STRIDE = 0.52;                                // world units per animation frame\n"
              "const HOP_MS = 300;                                 // the little jump onto the seat")

open(p, "w", encoding="utf-8").write(s)
print("hop added")
