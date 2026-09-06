"""Pin down the door.

The player says the door is normally blocked by a seat at level start, and that
the opening move is to drag that seat clear. So the true door position should
show a HIGH blocked-rate across the campaign - and, crucially, it should never
sit on a hole or outside the board.
"""
import json, collections

lv = json.load(open("lv/levels_campaign.json", encoding="utf-8"))

def board(o):
    W, H = o["w"], o["h"]
    holes = set(o["holes"])
    occ = set()
    for x, y, ln, col, vert in o["seats"]:
        for k in range(ln):
            occ.add((x, y + k) if vert else (x + k, y))
    return W, H, holes, occ

CANDS = {}
for edge in ("right", "left"):
    for tag, f in (("row 0", lambda H: 0),
                   ("row 1", lambda H: 1),
                   ("row H/4", lambda H: H // 4),
                   ("row H/2", lambda H: H // 2),
                   ("row H-2", lambda H: H - 2),
                   ("row H-1", lambda H: H - 1)):
        CANDS[edge + " " + tag] = (edge, f)
for edge in ("top", "bottom"):
    for tag, f in (("col 0", lambda W: 0),
                   ("col W/2", lambda W: W // 2),
                   ("col W-1", lambda W: W - 1)):
        CANDS[edge + " " + tag] = (edge, f)

rows = []
for name, (edge, f) in CANDS.items():
    blocked = hole = 0
    for o in lv:
        W, H, holes, occ = board(o)
        if edge == "right":   c, r = W - 1, f(H)
        elif edge == "left":  c, r = 0, f(H)
        elif edge == "top":   c, r = f(W), 0
        else:                 c, r = f(W), H - 1
        if (r * W + c) in holes: hole += 1
        elif (c, r) in occ: blocked += 1
    rows.append((name, blocked / len(lv), hole / len(lv)))

rows.sort(key=lambda x: -x[1])
print("%-18s %8s %8s" % ("door candidate", "blocked", "on hole"))
for name, b, h in rows:
    print("%-18s %7.0f%% %7.0f%%" % (name, b * 100, h * 100))

# how much floor is reachable once you clear the doorway - a real door should
# open onto the bus, not into a sealed pocket
print()
def region_size(W, H, holes, occ, c, r):
    if (r * W + c) in holes: return -1
    seen = {(c, r)}
    st = [(c, r)]
    while st:
        x, y = st.pop()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x+dx, y+dy
            if not (0 <= nx < W and 0 <= ny < H): continue
            if (ny*W+nx) in holes or (nx,ny) in occ or (nx,ny) in seen: continue
            seen.add((nx,ny)); st.append((nx,ny))
    return len(seen)

for name in ("right row 1", "right row H/4", "right row 0", "right row H/2"):
    edge, f = CANDS[name]
    sizes = []
    for o in lv:
        W, H, holes, occ = board(o)
        c, r = W - 1, f(H)
        free_total = W * H - len(holes) - len(occ)
        sz = region_size(W, H, holes, occ - {(c, r)}, c, r)
        sizes.append(sz / max(free_total + (1 if (c, r) in occ else 0), 1))
    sizes.sort()
    print("%-18s floor opened after clearing the doorway: median %.0f%%  p10 %.0f%%"
          % (name, 100 * sizes[len(sizes)//2], 100 * sizes[len(sizes)//10]))
