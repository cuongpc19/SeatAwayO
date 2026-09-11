# Seat Match — design brief

Everything a designer needs to redesign the look without breaking the game: the rules, the
numbers, the screens, and the short list of things that are not decisions.

Every figure here was **measured from the shipped campaign data** (`src/lv/boards_163.json`,
2085 boards), not estimated. Where a rule has a reason, the reason is given — a rule without one
gets changed by the next person.

---

## 1. The game, in one minute

A room fills with coloured seats. A queue of coloured passengers waits outside one door. The
player **slides seats around the floor** so each passenger can walk from the door to a free seat
of their own colour. Everyone seated before the clock runs out is a win.

1. **A passenger boards on their own.** The player never touches a passenger. The one at the
   front of the queue walks in the moment a seat of their colour is reachable.
2. **The player only moves seats.** Press and hold a seat, drag it across free floor, let go. A
   seat *slides* — it cannot jump over anything.
3. **Reachability is the puzzle.** A seat with no walkable route from the door is useless, however
   empty it is. Most of the game is clearing a path.
4. **The clock is the only way to lose.** There is no move limit and no wrong move.

| | |
|---|---|
| Levels | **2085**, one fixed ladder |
| Board sizes | **9 distinct**, 3×6 up to 7×11 — **1556 of them are 5×8** |
| Queue | 2 to 56 people, median **31** |
| Clock | 30s to 455s, median **110s** |
| Difficulty | 1673 plain, **206 hard**, **206 very hard** |

---

## 2. The board

A rectangular grid of square cells. The door sits in one long wall; **110 boards carry a second
door** facing it across the floor, each with its own queue.

> ⚠ **The two queues are not halves of one.** Their colours differ on 77 of the 78 boards that
> ship both, so somebody at the wrong door cannot stand in for somebody at the right one. They
> also take turns, or one line empties while the other stands still.

### Seats

A seat covers **one or two cells** and holds one passenger per cell. Of 50,932 pieces across the
campaign: **33,951 single, 16,890 double**, 90 triple, 1 quad. Triples only appear from level 1844.

> ⚠ **A seat faces a direction, and you cannot enter over its back.** A passenger may step in from
> the front or either side, never from behind the backrest. Whatever the art becomes, **which way
> a seat faces must be readable at a glance** — a backrest, a hood, an opening. This is the rule
> players misread most, and the one a redesign is most likely to erase.

93.5% of pieces in the campaign share one facing, so the rule bites rarely — which makes it worse,
not better: a player meets it for the first time deep into the game and has to understand it
instantly.

### Floor

| | From | Effect |
|---|---|---|
| **Holes** | L21 | Cells with no floor. Nothing walks or slides across. Not drawn at all. |
| **Obstacles** | L15 | A cell with something bolted to it. Same effect, but the floor is there and something stands on it. |

> ⚠ **The doorway is not reserved.** A seat parked in the door is the normal opening state of many
> boards; clearing it *is* the puzzle. A design that keeps the doorway clear removes most of the
> early game.

---

## 3. Seat colours — not a palette choice

Every level stores a **colour index** per seat and per passenger. The index is the meaning; the hex
is what the shipped game paints it. Source of truth: `NAMES` and `CSS` in `src/engine.js`.

| Index | Name | Hex | Notes |
|---|---|---|---|
| **0** | Grey | `#969ca8` | **Bolted to the floor — never moves.** Accepts index 2 only. |
| 1 | Red | `#e83e48` | |
| **2** | Sky | `#239be1` | **The first colour the game ever shows.** Level 1 is all of it. |
| 3 | Yellow | `#fac42e` | |
| 4 | Green | `#4ac65c` | |
| 5 | Orange | `#fa822a` | Shares a board with index 2 on most early levels. |
| 6 | Purple | `#a25cea` | |
| 7 | Blue | `#2e92f2` | Rare. |
| 8 | Pink | `#f470b0` | |

> ⚠ **Indices 2, 5 and 6 must stay clearly distinct from index 7.** Sky and blue sit on the same
> boards. The shipped order looks scrambled on purpose: when sky moved to index 2, orange and
> purple moved with it rather than being re-chosen, because index 2 shares a board with index 5 on
> 490 of the first 600 levels. Leaving a blue at 5 would put two blues on those boards that a
> player has to tell apart at a glance and cannot.

A passenger wears their seat's colour. In 3D the passenger takes a **deeper tone of the same hue**
than the cushion — painted the same shade they vanish into the seat the moment they sit down, and
all that is left is a floating head.

---

## 4. Special seats

| Piece | From | Behaviour | Must read as |
|---|---|---|---|
| **Double seat** | L3 | Two cells, two passengers, same colour. | Visibly two places, not one slab. |
| **Grey seat** | L7 | Never moves. Takes only index 2. | Bolted down — plate, bolts, weight. |
| **Locked seat** | L98 | Padlocked and immovable **until somebody sits in it**; then it slides like any other. | A padlock on the back, which comes off on seating. |

The padlock is the one piece that needs a sentence in play: it is not permanent, and what opens it
is the thing the player is already trying to do.

---

## 5. Progression and scoring

- **One fixed ladder.** Levels are played in order. There is no level picker — the progress screen
  shows where you are and what is coming, and **does not start a level**.
- **Difficulty rhythm.** From level 15 on, every level ending in **5** is Hard and every level
  ending in **9** is Very hard. Levels ending in 0 are never marked. This is the APK's own
  `difficultLevel` field, not a judgement of ours.
- **Stars come off the clock**, and nothing else: over **55%** of the time left is three stars,
  over **25%** is two, anything else is one. A replay only ever raises a level's stars.

---

## 6. Economy

| Thing | Unlocks | Cost | Does |
|---|---|---|---|
| Win purse | — | — | **+100 gold** per level cleared |
| Win streak | L5 | — | Bonus on top: **+10 / +15 / +20 / +25** at 3, 5, 7 and 10 wins in a row. A loss resets it to zero. |
| **Time booster** | L8 | 150 | +30 seconds straight onto the clock |
| **Jump booster** | L14 | 300 | Arms one move: the next seat dragged goes anywhere it fits, ignoring walls and other seats |
| **Add line** | L16 | 500 | Opens one extra lane down the left. Everything shifts right. One per board. |
| **Revive** | — | 500 | Offered on time-out: +60 seconds to keep playing the same board |

Locked boosters are shown greyed with `LV 8` on them rather than hidden — the player should see
what is coming.

> ⚠ **Add line moves the doorway with everything else.** Every seat steps one column right; a door
> left on the old edge becomes an interior cell with a seat standing on it, nobody can walk in, and
> the booster the player just paid for is what made the board unwinnable.

---

## 7. Screens

### Home — *the only way onto a board*
- Title / cover art
- **PLAY** — one tap, continues at the current level
- `Level n of 2085` · total stars · gold
- `Next hard level: n`
- Settings, progress screen

### Progress — *where am I, how much is left*
- The current level and the next ~29, then an ellipsis, then the final level in the corner
- Cleared levels are **not** shown — they cannot be replayed and their stars are already summed
- Hard and Very hard marked on the cells
- **Nothing here starts a level**

### Play — HUD *(top row, never over the board)*
- Left: settings/back, **Level** pill, difficulty chip
- Centre: **Time** pill, larger than the rest, turns red under 30s
- Right: **gold** purse
- Bottom: the three boosters in a row, each with its cost or its unlock level
- A one-line hint area (“Not enough gold”, “Nowhere for that seat to slide”)

### Level complete — *the reward, and the reason to go again*
- Celebration: rays, confetti
- **LEVEL COMPLETE!**
- Stars, one to three
- One-line summary of the run
- **Unlock meter** — a bar filling toward the next new piece or booster, labelled with what it is
  and which level it lands on
- **+gold**, large
- Streak line, when a bonus was earned
- `NEXT LEVEL` · `HOME`

> ⚠ The meter is asked for **the level just cleared**, not the one being handed over. The other
> form tops out one level short, and the reward reads as receding.

### Time out — *a sale, not a failure notice*
- Its own dialog, **not the win card recoloured**
- Big clock illustration, **+60**
- “Add 60 seconds to keep playing!” — **Continue** for 500 gold
- An **X** that declines, and only then reveals the OUT OF TIME card with `TRY AGAIN` / `HOME`

### Walkthrough — *one bubble, one new thing*
- A bubble pointing at what is new, everything else dimmed
- Runs for: grey seat, locked seat, jump, add line, time booster. **Not** for the double seat — it
  explains itself the first time one is dragged.
- Each booster lesson gives a **free use**, and the only way on is pressing the button itself. A
  card that can be dismissed *is* dismissed, and the player ends up owning a booster they have
  never used.
- The clock is held for the whole lesson.

> ⚠ **Never a dead end.** Every waiting step grows a way past it after a few seconds. A board can
> always turn out to have no move left in it, and a tutorial nobody can leave is a fault rather
> than a lesson.

### Settings — *paused*
- Sound and Vibration toggles
- `RESTART LEVEL` · `HOME` · `RESUME`
- A **PRIVACY** link that opens a panel inside the page

### Privacy — *a platform requirement*
- Opens in-page. **No outbound links anywhere in the UI** — the host forbids them.
- Must match exactly what the game collects.

---

## 8. Frames and platform

- **Both orientations**, laid out differently — not one stretched into the other.
- **Phone first.** The design box is 540×1160 and must hold at roughly 400px wide. Desktop must
  not be a portrait column with dead space either side.
- **Web, hosted by a portal.** One self-contained file, under 20 MB, **no absolute paths**, no
  outbound links, and **time-to-first-play is graded** — nothing heavy on the boot path.

---

## 9. Not decisions

Everything above is open to redesign except these. Each one breaks *boards*, not just looks.

1. **The colour indices.** Index 0 is the fixed grey and accepts only index 2. The hexes may
   shift, but the nine must stay nine and stay mutually distinguishable at small size.
2. **A seat cannot be entered over its back.** Facing must be visible in the art.
3. **A full seat stays on the floor.** It stops taking passengers and goes on being an obstacle.
   It does not vanish. *(The `gone` flag that suggests otherwise lives only in
   `src/bench_rush.html`, an abandoned prototype that `src/solvecheck.py` still points at.)*
4. **Every board has exactly as many places as people** — capacity equals queue on all 2085, with
   no spare seat anywhere. Nothing may consume a place.
5. **The player never moves a passenger** — only seats.
6. **The save key never changes after launch**, or every player loses their progress.

Points 2, 3 and 4 are each written here because they were got wrong once already.

---

## Where things live

| | |
|---|---|
| Board data, all 2085 | `src/lv/boards_163.json` |
| Colour table | `src/engine.js` — `NAMES`, `CSS` |
| Rules (2D, shipped) | `src/engine.js` |
| Shell, economy, cards | `src/game_shell.js` |
| Markup and CSS | `src/game_head.html` |
| Tuning in one block | `src/build.py` |
| 3D rebuild | `game3d/` — `rules3d.js`, `game_tpl.html` |
| Design prototypes | `proto/` |
