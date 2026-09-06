p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

# ---- no field of lit tiles when a seat is picked up ----
OLD = """  // walkable floor tint + legal drop targets
  if (g.sel && g.dragTargets) {
    for (const [c, r] of g.dragTargets) {
      ctx.save(); ctx.globalAlpha = .5;
      quad(tileQuad(c, r, .012), "#ffffff"); ctx.restore();
    }
  } else {
    for (let r = 0; r < g.H; r++) for (let c = 0; c < g.W; c++)
      if (GUIDES && region[idx(g, c, r)]) { ctx.save(); ctx.globalAlpha = .22; quad(tileQuad(c, r, .012), "#bfe9ff"); ctx.restore(); }
  }"""
NEW = """  // Lighting up every legal destination floods the board, so the only thing that
  // marks a picked-up seat is a glow on its own tile.
  if (!g.sel) {
    for (let r = 0; r < g.H; r++) for (let c = 0; c < g.W; c++)
      if (GUIDES && region[idx(g, c, r)]) {
        ctx.save(); ctx.globalAlpha = .22;
        quad(tileQuad(c, r, .012), "#bfe9ff");
        ctx.restore();
      }
  }"""
assert OLD in s
s = s.replace(OLD, NEW)

# ---- a soft glow under the held seat, and a quiet nudge under the cursor ----
OLD2 = """  if (g.sel) {
    for (const [c, r] of cellsOf(g.sel)) {
      ctx.save(); ctx.globalAlpha = .55;
      quad(tileQuad(c, r, .016), "#ffd76a"); ctx.restore();
    }
  }
  if (g.drag && g.drag.hover) {
    const [c, r] = g.drag.hover;
    ctx.save(); ctx.globalAlpha = .85;
    quad(tileQuad(c, r, .02), "#ffe27a"); ctx.restore();
  }"""
NEW2 = """  if (g.sel) {
    for (const [c, r] of cellsOf(g.sel)) {
      ctx.save(); ctx.globalAlpha = .34;
      quad(tileQuad(c, r, .016), "#ffe9a8"); ctx.restore();
    }
  }
  if (g.drag && g.drag.hover) {          // just the tile under the cursor
    const [c, r] = g.drag.hover;
    ctx.save(); ctx.globalAlpha = .40;
    quad(tileQuad(c, r, .02), "#ffe9a8"); ctx.restore();
  }"""
assert OLD2 in s
s = s.replace(OLD2, NEW2)

# selected seat should not fade out - it is the thing you are looking at
s = s.replace("blit(\"bench_\" + nm, wx, 0, wz, drag ? .55 : 1, .78);",
              "blit(\"bench_\" + nm, wx, 0, wz, drag ? .82 : 1, .78);")

s = s.replace("""    <p class="note">The blue floor tint, the white ring under a seat, the walking route and the yellow dashed
      ring on a door-blocking seat are all coaching overlays added here &mdash; the shipped game draws none of
      them. <b>Guides off</b> hides the lot. The yellow tile under a seat you have picked up, and the white
      tiles showing where it may go, stay either way.</p>""",
"""    <p class="note">The blue floor tint, the white ring under a seat, the walking route and the yellow dashed
      ring on a door-blocking seat are all coaching overlays added here &mdash; the shipped game draws none of
      them. <b>Guides off</b> hides the lot. Picking a seat up just puts a soft glow on its own tile.</p>""")

open(p, "w", encoding="utf-8").write(s)
print("highlights toned down")
