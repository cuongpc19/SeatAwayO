p = "game3_tpl.html"
s = open(p, encoding="utf-8").read()

# ---- one definition of "a way into this seat", used everywhere ----
OLD = """function touches(g, b, region) {
  for (const [c, r] of cellsOf(b))
    for (const [dc, dr] of DIRS) {
      const nc = c + dc, nr = r + dr;
      if (inBoard(g, nc, nr) && region[idx(g, nc, nr)]) return true;
    }
  return false;
}"""
NEW = """// You climb into a seat over the cushion or from either side. The backrest is on
// the +z edge, so the tile directly behind a seat is not a way in.
const ENTRY_DIRS = [[0, -1], [-1, 0], [1, 0]];

/** Floor tiles a passenger could step onto to take this seat. */
function entryCells(g, b) {
  const own = new Set(cellsOf(b).map(([c, r]) => c + "," + r));
  const seen = new Set(), out = [];
  for (const [c, r] of cellsOf(b))
    for (const [dc, dr] of ENTRY_DIRS) {
      const nc = c + dc, nr = r + dr, k = nc + "," + nr;
      if (!inBoard(g, nc, nr) || own.has(k) || seen.has(k)) continue;
      seen.add(k); out.push([nc, nr]);
    }
  return out;
}

function touches(g, b, region) {
  for (const [c, r] of entryCells(g, b)) if (region[idx(g, c, r)]) return true;
  return false;
}"""
assert OLD in s
s = s.replace(OLD, NEW)

# ---- the chosen seat must be reachable through one of those tiles ----
OLD2 = """  for (const seat of g.seats) {
    if (!accepts(seat, ci)) continue;
    for (const [c, r] of cellsOf(seat)) {
      for (const [dc, dr] of DIRS) {
        const nc = c + dc, nr = r + dr;
        if (!inBoard(g, nc, nr)) continue;
        const dist = d[idx(g, nc, nr)];
        if (dist >= 0 && dist < bestD) { bestD = dist; best = seat; }
      }
    }
  }"""
NEW2 = """  for (const seat of g.seats) {
    if (!accepts(seat, ci)) continue;
    for (const [nc, nr] of entryCells(g, seat)) {
      const dist = d[idx(g, nc, nr)];
      if (dist >= 0 && dist < bestD) { bestD = dist; best = seat; }
    }
  }"""
assert OLD2 in s
s = s.replace(OLD2, NEW2)

# ---- and they must actually walk in through it ----
OLD3 = """  let entry = null, best = Infinity, last = null;
  for (const [c, r] of cellsOf(seat)) {
    for (const [dc, dr] of DIRS) {
      const nc = c + dc, nr = r + dr;
      if (!inBoard(g, nc, nr)) continue;
      const dist = d[idx(g, nc, nr)];
      if (dist >= 0 && dist < best) { best = dist; entry = [nc, nr]; last = [c, r]; }
    }
  }"""
NEW3 = """  let entry = null, best = Infinity, last = null;
  const own = cellsOf(seat);
  for (const [nc, nr] of entryCells(g, seat)) {
    const dist = d[idx(g, nc, nr)];
    if (dist < 0 || dist >= best) continue;
    // hop onto whichever of the seat's own tiles that entry is next to
    let target = own[0], bestStep = Infinity;
    for (const [c, r] of own) {
      const m = Math.abs(c - nc) + Math.abs(r - nr);
      if (m < bestStep) { bestStep = m; target = [c, r]; }
    }
    best = dist; entry = [nc, nr]; last = target;
  }"""
assert OLD3 in s
s = s.replace(OLD3, NEW3)

s = s.replace("""      <li>They come in through the <b>door</b> on the right and walk across empty floor only &mdash; seats block the way.
        A coloured seat takes only its own colour; a <b>grey seat</b> takes anyone.</li>""",
"""      <li>They come in through the <b>door</b> on the right and walk across empty floor only &mdash; seats block the way.
        A coloured seat takes only its own colour; a <b>grey seat</b> takes anyone.</li>
      <li>A seat can only be entered over its cushion or from either side. Nobody climbs in over the backrest, so
        the tile behind a seat is no use for boarding it.</li>""")

open(p, "w", encoding="utf-8").write(s)
print("boarding from behind a seat disallowed")
