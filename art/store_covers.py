"""The covers CrazyGames shows in its grid - the home screen's picture, reframed.

    python store_covers.py   ->  ../store/crazygames/cover-<size>.png

These used to be a drawing of their own: a violet ground, SEAT / MATCH stacked in
four colours behind a thick white sticker edge, and two riders beside an empty
grey seat. It read as a different game to the one that opens when you click it.
The home screen's art is the better tile - the warm glow under the row, the
livery lettering, a full seat, a shared bench and the grey one nobody can move -
so this is that same render in three frames rather than a second picture that
drifts away from the first one every time a seat changes.

⚠ Re-rendered per size, never cropped. `home_cover.render` takes the frame, the
camera scale, and where the row and the title sit, because a 16:9 crop of the 2:3
render loses the outer two seats and a 1:1 crop loses the tagline. Same scene,
same lettering, three cameras.

Slow - it is a raymarcher at cover resolution - and not part of build.py.
"""
import os
import time

from home_cover import render

OUT = "../store/crazygames"

# The three numbers that differ per frame, and why they differ:
#
#   scale     px per world unit. The row is 6.5 units across (two single seats,
#             a double, and the gaps), so `scale` is the width it fills:
#             1920 -> 6.5 x 256 = 1664px, 87% of the frame.
#   row_y     the camera's horizon. The pieces hang below it.
#   title_y   the middle of the name. A touch lower than the home screen's,
#             because nothing hangs under it here.
#   safe      how wide the name is allowed to run. Nothing is cropped here - a
#             store tile is shown whole - so this is composition, not the home
#             screen's 9:19.5 crop line. Wide frames want a narrower name.
#
#     file name         w     h   scale  row_y  title_y  safe
SPECS = [
    # Landscape. Room for the row to run wide under a name held to two thirds.
    ("cover-1920x1080", 1920, 1080,  256,  0.70,  0.30,  0.62),
    # Portrait 2:3, the same shape as the home screen. The row can only ever be
    # as wide as the frame, so the name and the row are centred as one block
    # with matching air above and below rather than pushed to the ends.
    ("cover-800x1200",   800, 1200,  115,  0.62,  0.36,  0.92),
    # Square. Between the two: a wide name, and the row nearly edge to edge.
    ("cover-800x800",    800,  800,  117,  0.66,  0.32,  0.86),
]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, w, h, scale, row_y, title_y, safe in SPECS:
        t0 = time.time()
        img = render(w, h, scale, row_y, title_y, safe, tagline=False)
        path = os.path.join(OUT, name + ".png")
        img.save(path, optimize=True)
        print("%-22s %s  %.0f KB  %.1fs"
              % (name + ".png", img.size, os.path.getsize(path) / 1024, time.time() - t0))
