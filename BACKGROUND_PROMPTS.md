# Background prompts

Prompts for generating the environment around the seating grid. The grid, the
seats and the people are drawn by code and are **not** in these images — the
generator only makes the world they sit in.

Four themes, none of them the APK's bus: **stadium, cinema, concert, classroom**.

---

## Why three pieces and not one picture

Boards are not one shape. Across the 600 campaign levels:

| | sizes in use |
|---|---|
| columns | 3 (×9), 4 (×111), **5 (×362)**, 6 (×93), 7 (×25) |
| rows | 6 (×25), 7 (×40), **8 (×409)**, 10 (×89), 11 (×37) |
| w ÷ h | 0.45 – 0.67 |

A single plate would have to stretch from 5×10 to 7×6 and the perspective would
tear. So generate **three tiles** the code composes at any size:

```
 ┌─────────┬───────────────────┬──────────┐
 │  LEFT   │       FLOOR       │  RIGHT   │
 │  strip  │   (seating area)  │  strip   │
 │ scenery │  tiles both ways  │  queue   │
 │ tiles ↕ │                   │ tiles ↕  │
 └─────────┴───────────────────┴──────────┘
     ~15%          ~55%             ~30%
```

- **FLOOR** — 1024×1024, seamless in both directions. The surface the seats stand on.
- **LEFT** — 512×2048, seamless top-to-bottom. Scenery, never walked on.
- **RIGHT** — 512×2048, seamless top-to-bottom. The aisle the queue waits in, so keep it walkable and quiet.

The door is always on the **right** edge of the grid and people enter from there,
which is why the right strip is the busy one.

---

## Shared technical block

Paste this into every prompt.

```
Top-down game background, camera 76 degrees above the horizon, axis-aligned,
no rotation, no vanishing point drift — almost a floor plan but with a slight
forward tilt. Stylised 3D cartoon render, glossy rounded plastic shapes, soft
ambient occlusion, one soft key light from the upper left, no hard shadows.
Clean mobile-puzzle look. Flat even lighting across the whole tile so it can
repeat without a visible seam.

MUTED, LOW-SATURATION palette only — greys, warm neutrals, muted teal, deep
navy, dusty wood. The gameplay pieces on top are bright saturated red #e83e48,
orange #fa822a, yellow #fac42e, green #4ac65c, cyan #2aced6, blue #2e92f2,
purple #a25cea, pink #f470b0, so the background must never use those at full
strength or the pieces stop reading.

No text, no letters, no numbers, no logos, no watermark, no UI, no characters,
no chairs or benches in the central area, no strong diagonal lines, no lens
blur, no vignette, no border frame.
```

---

## Theme A — Stadium

The grid is a block of terracing; the queue files down the vomitory.

**FLOOR** (1024×1024, seamless)
```
Seamless top-down tile of a football stadium terrace deck: pale concrete steps
running in even horizontal bands, worn tread edges, faint drainage channel,
scuffed paint, small bolt plates where seat frames anchor. Muted concrete grey
with a warm dusty tint. Nothing else on it.
```

**LEFT** (512×2048, vertical tile)
```
Vertical strip seen from above: the edge of a floodlit football pitch — deep
muted green turf with a mown stripe pattern, a chalk touchline, a low advertising
hoarding in blank dark navy, a narrow running track in desaturated brick red.
```

**RIGHT** (512×2048, vertical tile)
```
Vertical strip seen from above: a stadium concourse aisle — non-slip concrete
with a yellow-grey nosing strip along each step, a steel handrail running the
length, a shallow puddle of light from an overhead lamp. Open and walkable,
nothing standing in the middle.
```

---

## Theme B — Cinema

The grid is the seating block; the queue comes up the side aisle from the screen.

**FLOOR**
```
Seamless top-down tile of a cinema auditorium floor: dark patterned carpet with
a small repeating geometric weave, deep muted burgundy and charcoal, tiny
recessed floor lights, faint tread wear. Low contrast so it stays quiet.
```

**LEFT**
```
Vertical strip seen from above: the base of a cinema screen wall — heavy pleated
acoustic curtain in deep muted red, a black masking border, a strip of cool spill
light on the floor in front of it.
```

**RIGHT**
```
Vertical strip seen from above: a cinema side aisle — dark carpet with a line of
small blue step lights along the wall, a brushed metal handrail, a soft pool of
warm light from a wall sconce. Clear down the middle.
```

---

## Theme C — Concert

The grid is a seated tier; the queue comes in past the sound desk.

**FLOOR**
```
Seamless top-down tile of a concert hall parquet floor: narrow oak boards in a
herringbone pattern, warm mid-brown, satin varnish with a soft sheen, faint
scuffs. Muted, no strong grain contrast.
```

**LEFT**
```
Vertical strip seen from above: the front edge of a concert stage — dark matte
stage deck, a row of small warm footlights, taped cable runs, a strip of dark
pit floor. Deep neutral tones.
```

**RIGHT**
```
Vertical strip seen from above: a venue walkway — matte black rubber flooring
with a fine ribbed texture, gaffer-taped cable route in dull silver, a low
barrier post at intervals, soft magenta-tinged spill from the rig above kept
very desaturated.
```

---

## Theme D — Classroom

The grid is the desks; the queue comes in through the door at the side.

**FLOOR**
```
Seamless top-down tile of a school classroom floor: pale beige linoleum in large
squares, warm and slightly worn, faint scuff arcs from chair legs, soft speckle
in the surface. Bright but low saturation.
```

**LEFT**
```
Vertical strip seen from above: the front of a classroom — the top edge of a
green chalkboard tray with chalk dust, a low bookshelf in pale birch, a rolled
map cylinder, a potted plant. Warm neutral wood tones.
```

**RIGHT**
```
Vertical strip seen from above: a classroom side aisle — the same beige lino,
a row of low cubby lockers in soft muted teal along the wall, a couple of hooks
with bags, sunlight falling in a soft rectangle from a window. Walkable, clear
in the middle.
```

---

## Checking a generated tile before using it

1. **Seam** — duplicate the tile and butt the copies together. A visible join means regenerate; do not fix by blurring the edge.
2. **Saturation** — drop a red `#e83e48` and a cyan `#2aced6` square on it. If either stops popping, the background is too loud.
3. **Tilt** — verticals must stay vertical. Any converging lines and it will not sit under the seats.
4. **Emptiness** — the FLOOR tile must survive having a seat drawn on every cell. Anything eye-catching on it becomes clutter.

---

## What changes in the code

`drawRoom()` in `src/engine.js` paints the station procedurally today. Swapping
in images means replacing three calls:

| now | becomes |
|---|---|
| `ballast()` pattern fill | FLOOR tile as a repeating pattern |
| sleeper + rail slabs | LEFT strip, tiled down the z axis |
| platform + safety line + studs | RIGHT strip, tiled down the z axis |

The carriage walls, the doorway and the floor checker stay procedural — they have
to line up with the grid exactly, and a generated image cannot be trusted to.
