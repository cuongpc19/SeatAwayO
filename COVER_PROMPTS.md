# Cover prompts

Prompts for generating the three CrazyGames store tiles by hand, in an image
model, instead of rendering them with `art/store_covers.py`.

Unlike `BACKGROUND_PROMPTS.md`, the pieces **are** in these images: a store tile
is a picture of the game's own toys, not a plate the code draws on top of. So
the prompt has to describe the seats and the passengers, not just the world.

| file | size | where CrazyGames shows it |
|---|---|---|
| `cover-1920x1080.png` | 1920×1080 | the wide banner on the game page |
| `cover-800x1200.png`  | 800×1200  | the portrait tile, phone grids |
| `cover-800x800.png`   | 800×800   | the square tile, thumbnails |

---

## ⚠ Generate without the title

No image model sets "Seat Match" in Baloo2 with the livery drop-stack and gets
it right — it will hand back **Seat Motch**, or good lettering in the wrong
face, and the name is the one thing on a tile that cannot be approximately
correct. Every prompt below therefore asks for **empty space where the title
goes** and no text anywhere in the frame.

Put the real lettering on afterwards with the code that already draws it:

```python
# in art/, on the generated file
from PIL import Image
import home_cover as hc

img = Image.open("gen-1920x1080.png").convert("RGBA")
hc.W, hc.H, hc.TITLE_Y, hc.SAFE, hc.WITH_TAGLINE = 1920, 1080, 0.30, 0.62, False
hc.lettering(img).convert("RGB").save("../store/crazygames/cover-1920x1080.png")
```

`TITLE_Y` is the middle of the name as a fraction of the height, `SAFE` how wide
it may run. The numbers per size are in `art/store_covers.py`'s `SPECS`.

---

## Shared block

Paste this into every prompt, then add the framing paragraph for the size.

```
Stylised 3D cartoon render of toy furniture, glossy smooth rounded plastic,
like injection-moulded toys with fat rounded-off edges — no fabric, no wood
grain, no texture of any kind, just clean shiny vinyl-plastic surfaces.

Camera 76 degrees above the horizon looking down at the seats, axis-aligned,
straight on, no rotation and no perspective drift — you see the tops of the
cushions and the front faces of the seat backs at the same time.

Subjects, left to right in one straight row, all standing on the same ground:
1. a small single armchair in bright red #e83e48, with a passenger sitting in
   it — the passenger is a simple glossy sphere head in the same red, with two
   tiny rounded arm stubs, no face, no eyes, no mouth, no hair, no clothes;
2. a wide two-seat bench in bright yellow #fac42e, twice as wide as the
   armchair, with two passengers side by side on it: a yellow sphere #fac42e
   and a blue sphere #239be1, same simple armless-ball design;
3. an empty single armchair in flat neutral grey #969ca8, no passenger, the
   same shape as the red one.
The three pieces are the same depth and the same height, evenly spaced, none
overlapping, all facing the camera.

Ground and light: a smooth vertical gradient from deep navy #161a36 at the top
to a lighter slate blue #4a548e at the foot, with a soft warm yellow #f8bf1a
haze glowing on the ground directly behind the row, and a dark vignette in the
corners. One soft key light from above and slightly left, soft ambient
occlusion, a soft contact shadow under each piece so the row sits on the ground
rather than floating. No hard shadows, no reflections on the ground.

Clean mobile-puzzle store art. High contrast between the pieces and the
background so the row still reads at 200px wide.
```

**Negative prompt**

```
text, letters, words, logo, watermark, signature, UI, buttons, numbers,
faces, eyes, mouths, smiles, hair, hats, clothes, arms, legs, hands, people,
humans, characters, realistic furniture, fabric, upholstery, cloth texture,
wood, sofa cushions with seams, room, walls, floor tiles, windows, clutter,
props, plants, busy background, photo, photorealistic, depth of field, blur,
tilt-shift, low contrast, dark muddy colours, extra seats, extra spheres
```

---

## 1920×1080 — the wide banner

```
[shared block]

16:9 landscape, 1920x1080. The row of three pieces runs across the lower half,
about 85% of the width, centred, with its base around 80% down the frame. Leave
the top third completely empty — plain gradient and haze, nothing in it — as
clear space for a title that will be added later. Nothing may touch the edges.
```

## 800×1200 — the portrait tile

```
[shared block]

2:3 portrait, 800x1200. The row of three pieces sits across the middle of the
frame, about 90% of the width, centred, its base a little below the halfway
line. Leave a wide empty band above the row — plain gradient and haze — as
clear space for a title that will be added later, and leave the bottom third
empty and quiet as well. Nothing may touch the edges.
```

## 800×800 — the square tile

```
[shared block]

1:1 square, 800x800. The row of three pieces fills the lower half, about 88% of
the width, centred, its base around 75% down the frame. Leave the top third
empty — plain gradient and haze — as clear space for a title that will be added
later. Nothing may touch the edges.
```

---

## If you do want the model to set the type

Only worth it as a mood board, never as the shipped file. Append:

```
Above the row, the words "Seat Match" on two lines, in a very heavy rounded
geometric sans with fat round terminals, bright golden yellow #f8bf1a, with a
darker yellow #d99c14 and a deep red-brown #a83220 stacked directly beneath
each letter as a hard 3D drop, and a soft dark cast under the whole word.
```

and drop `text, letters, words, logo` from the negative prompt. Check every
letter before using it.

---

## Judging what comes back

The tile has one job — to be the one clicked in a wall of forty. Shrink the
result to 200px wide and ask:

- is the row still three distinct pieces, or one coloured smudge;
- are the passengers still visible **in** the seats, or hidden behind the seat
  backs (camera too low) or floating over them (camera too high);
- is the middle piece still obviously twice as wide as the outer two — that is
  the whole puzzle in one line;
- is the grey seat obviously the odd one out;
- is there still a clean empty band for the name.

Anything that fails the first or the last is not fixable in post. Re-roll it.
