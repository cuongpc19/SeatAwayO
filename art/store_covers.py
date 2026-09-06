"""The three covers CrazyGames asks for, off the home screen's own render.

    python store_covers.py   ->  ../store/crazygames/cover-<size>.png

They want 1920x1080, 800x1200 and 800x800, and the same picture has to work in
all three. It is re-rendered rather than cropped: a 16:9 crop of the 2:3 home
render loses either the row of seats or the title, and a 1:1 crop loses both
outer seats. Same scene, same lettering, three cameras.

⚠ The numbers per size are not decoration. `scale` and `gap` set how much of the
frame the row eats; `row_y` and `title_y` set where the two things sit. A wide
frame needs the row tighter and the type smaller relative to the width, or the
seats run off the sides and the title fills half the poster. Each row below was
looked at before it was written down.
"""
import os
import home_cover

OUT = "../store/crazygames"

#      w     h    scale  row_y  title_y  safe   gap
SPECS = [
    # Landscape. The row spreads, so the seats are pulled in and the type is
    # held to half the width - a title set to 70% of 1920 reads as a banner.
    ("cover-1920x1080", 1920, 1080, 152, 0.66, 0.30, 0.52, 2.30),
    # Portrait 2:3, the home screen's own shape at store size.
    ("cover-800x1200", 800, 1200, 96, 0.63, 0.30, 0.72, 2.45),
    # Square. Least room of the three: the row comes in tighter still.
    ("cover-800x800", 800, 800, 98, 0.66, 0.30, 0.70, 2.30),
]

os.makedirs(OUT, exist_ok=True)
for name, w, h, scale, row_y, title_y, safe, gap in SPECS:
    img = home_cover.render(w, h, scale, row_y, title_y, safe, gap)
    path = os.path.join(OUT, name + ".png")
    img.save(path, optimize=True)
    print("%-22s %s  %.0f KB" % (name + ".png", img.size, os.path.getsize(path) / 1024))
