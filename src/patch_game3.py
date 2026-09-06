p = "game_tpl.html"
s = open(p, encoding="utf-8").read()

OLD = """function params(L) {
  const a = anchorAt(L);
  const U = PACING.unlocks;
  let colours = a.colours;
  if (L < 4) colours = 1; else if (L < 5) colours = 2; else if (L < 13) colours = Math.min(colours, 3);
  colours = Math.max(1, Math.min(COLOURS.length, colours));
  let grid = a.grid.slice();
  if (L < 8) grid = [3, 6]; else if (L < 11) grid = [4, 6]; else if (L < 14) grid = [4, 8];
  let slots = a.slots;
  if (L < 14) slots = Math.max(2, Math.round(2 + (L - 1) * 1.5));
  slots = Math.min(slots, grid[0] * grid[1] - 2);
  return {
    w: grid[0], h: grid[1], colours, slots,
    greyPct: L < U.grey ? 0 : a.greyPct,
    widePct: L < U.wide ? 0 : a.widePct,
    time: Math.max(40, L < 6 ? 240 : a.time),
  };
}"""

NEW = """// Grid follows the measured unlock order rather than the noisy per-block median,
// with the bigger boards appearing at roughly the share they hold in the campaign
// (5x8 59%, 6x10 15%, 4x8 9%, 7x11 4%).
function gridFor(L, rand) {
  if (L < 8) return [3, 6];
  if (L < 11) return [4, 6];
  if (L < 12) return [4, 7];
  if (L < 14) return [4, 8];
  const r = rand();
  if (L >= 21 && r < .04) return [7, 11];
  if (L >= 15 && r < .19) return [6, 10];
  if (r < .28) return [4, 8];
  return [5, 8];
}

function params(L, rand) {
  const a = anchorAt(L);
  const U = PACING.unlocks;
  let colours = a.colours;
  if (L < 4) colours = 1; else if (L < 5) colours = 2; else if (L < 13) colours = Math.min(colours, 3);
  colours = Math.max(1, Math.min(COLOURS.length, colours));
  const grid = gridFor(L, rand);
  let slots = a.slots;
  if (L < 14) slots = Math.max(2, Math.round(2 + (L - 1) * 1.5));
  slots = 2 * Math.max(1, Math.min(Math.round(slots / 2), Math.floor(grid[0] * grid[1] * .42)));
  return {
    w: grid[0], h: grid[1], colours, slots,
    greyPct: L < U.grey ? 0 : a.greyPct,
    widePct: L < U.wide ? 0 : a.widePct,
    time: Math.max(40, L < 6 ? 240 : a.time),
  };
}"""

if OLD not in s:
    raise SystemExit("params block not found")
s = s.replace(OLD, NEW)

s = s.replace("  const p = params(L), rand = rng(L * 2654435761 + 17);",
              "  const rand = rng(L * 2654435761 + 17), p = params(L, rand);")

open(p, "w", encoding="utf-8").write(s)
print("patched")
