import time
from board import *

# a plausible mid-game 5x8 state: some benches filled, some still empty,
# grey benches are the locked ones, a queue waits on the lane
G = "green"; R = "red"; Y = "yellow"; P = "purple"; B = "blue"; O = "orange"; X = "grey"

def cell(bench, guest=None): return dict(bench=bench, guest=guest)

grid = [
    [cell(G, G), cell(G, G), cell(X),    None,      cell(P, P), cell(P),    cell(Y, Y), cell(Y)],
    [cell(R, R), cell(R),    cell(X),    cell(B, B), cell(B),   cell(B, B), cell(X),    cell(O, O)],
    [None,       cell(Y, Y), cell(Y),    cell(X),    cell(G),   cell(G, G), cell(P, P), cell(P)],
    [cell(B, B), cell(B),    cell(O, O), cell(O),    cell(X),   cell(R, R), cell(R),    cell(X)],
    [cell(P),    cell(P, P), cell(X),    cell(Y, Y), cell(Y),   cell(X),    cell(B, B), cell(B)],
]
queue = [R, R, Y, B, P, G, O, B]
walker = (G, (2.6, 0, 4.6))

t = time.time()
st = build_board(grid, queue, walker)
img = st.compose()
img.convert("RGB").save("board.png")
print("board %.1fs -> board.png %s" % (time.time() - t, img.size))
