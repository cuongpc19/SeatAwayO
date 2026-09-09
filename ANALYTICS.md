# Telemetry and analytics — what is set up, and how to read it

Two data sources, for two different questions. Reading the wrong one gives a confident wrong
answer, so start at §0.

Built to the same shape as the sibling project (Marble Sort), which is worth knowing because its
`ANALYTICS.md` carries the scars this one was designed around.

---

## 0. Which source answers which question

| question | source | why |
|---|---|---|
| How many people are playing? From which countries? | **Firebase Analytics** | GA resolves country from IP; we hold no such data |
| Session length, weekly/monthly returners | **Firebase Analytics** | GA builds these; computing them by hand is worse |
| **Winrate of level N** | **Realtime Database** (`pull_runs.py`) | see the warning below |
| Which level players quit on | Realtime Database | GA cannot tell one revision of a level from another |
| Who used boosters / revived | Realtime Database | not sent to GA (§5) |

> ⚠ **Never measure winrate with GA.** GA records only the level *number*, and in this project a
> number is not a board: `build.py` sets the clock (`PLAIN_SECONDS` / `HARD_SECONDS`), the grading
> (`grade()`), and which campaign file ships at all. Change any of those and games from a board
> that no longer exists sit under the same number as games from the one that replaced it, and GA
> will average them into one convincing figure. Every row in the Realtime Database carries `sig`,
> the **board fingerprint**, and both `pull_runs.py` and `stats.html` flag any level showing more
> than one. This is the exact mistake that wrecked a calibration pass on the sibling project.

---

## 1. The project, and what is live

Firebase project **`seatmatch-292b3`** (project number 104118195139), web app *seatmatch*
`1:104118195139:web:17b23adff60ede8caa2376`. Pinned in [.firebaserc](.firebaserc), so every
`firebase` command here needs no `--project`.

| | value | state |
|---|---|---|
| GA4 measurement id | `G-TZ865K21Z4` | **live** — [src/analytics.js](src/analytics.js) |
| Realtime Database | `seatmatch-292b3-default-rtdb`, **Singapore** | **live** — [src/telemetry.js](src/telemetry.js) |

Endpoint: `https://seatmatch-292b3-default-rtdb.asia-southeast1.firebasedatabase.app/runs.json`.

⚠ **The region is in the hostname and it is not cosmetic.** A database created in `us-central1`
answers on `...-default-rtdb.firebaseio.com` with no region segment. Probed rather than assumed on
8 Sep 2026: the other two hostnames return `"Database lives in a different region"` and name
`asia-southeast1` as the right one. If the instance is ever recreated elsewhere, change the URL in
`src/telemetry.js`, the `databaseURL` in `public/stats.html`, and `INSTANCE` in
`scripts/pull_runs.py`.

Verified end to end on 8 Sep 2026 (`python src/test_stats.py`): a level played headless produced
one row carrying `lvl`, `sig`, `diff`, `result`, `ms`, `moves`, `stars`, `build`, `dev`, `host`,
`from`, `ga`, `t`. (`used` is absent when no booster was spent — the database drops empty arrays,
and **absent means none**.)

Rules are deployed and were checked against the live database rather than assumed:

| probe | result |
|---|---|
| `GET /runs.json` with no auth | `Permission denied` ✓ |
| `POST /runs.json` with `{"junk":1}` | `Permission denied` ✓ (the `.validate` shape check) |
| `POST` a real-shaped row | written ✓ |

Redeploy after editing [database.rules.json](database.rules.json):

```bash
npx firebase-tools deploy --only database
```

⚠ **Never skip that on a fresh database.** It starts either world-readable (test mode, which then
locks itself completely after 30 days) or fully locked — and a fully locked database refuses every
write in silence, because nothing in `telemetry.js` reports a failed one. The shape here is the
only workable one: **write-only**. Anyone may add a row, nobody may read one, because the database
URL is visible in the game bundle and there is no way around that for browser-sent telemetry.

---

## 2. Reading the game data

```bash
python scripts/pull_runs.py              # tally only, writes nothing
python scripts/pull_runs.py --write      # merge into playlog.jsonl
python scripts/pull_runs.py --all        # count test games too
python scripts/pull_runs.py --level 15   # one level
python scripts/pull_runs.py --build abc1234
```

No credentials to set up: it shells out to the Firebase CLI, which is already logged in and reads
as project **owner**, bypassing the rules. That is why the rules need no read account for this
path.

Test games are recorded like any other but carry `dev: 1` and the hostname they were played on,
and `--all` is what counts them back in. **Filtering on read rather than blocking on write is
deliberate**: a blocked row is gone forever, a filtered one is still there when the question
changes.

### The dashboard — `public/stats.html`

Nine headline cards, then five tables: **by level**, **by day**, **by build**, **by source** and
**by booster**. Filtered by a time window (an hour up to everything, or a custom range), by build,
by source, and with test games hidden until asked for.

The by-level table is the one it exists for: winrate on a five-step ramp, games, wins, attempts per
clear, **median** time and moves, average stars, booster use split by booster, % of level 1, and a
**boards** column — the count of distinct fingerprints, which is the retune alarm. Anything with
fewer than 8 games behind it prints grey rather than as a measured figure.

⚠ **Winrate here is wins over attempts that finished**, because an end row is the only kind this
game writes (§8). A player who opened a board and walked away is in none of it, so the levels people
give up on are exactly the ones it flatters. Quit rate, drop-off and winrate per *player* need a
start row and a random per-device code; the sibling project logs both and this one logs neither, so
those columns are absent rather than approximated. Adding them is a change to
[src/telemetry.js](src/telemetry.js) and to the rules' shape check, not to the page.

⚠ **`dev` means different things in the two projects.** Here it is `0`/`1` for "played on
localhost or a LAN address"; in Marble Sort's dashboard it is the per-device code. A column ported
between the two pages without checking that will be wrong.

Live as of 8 Sep 2026. Two things had to be true, and both now are:

1. **Firebase Authentication switched on**, with Google as a provider. Without it
   `signInWithPopup` fails before it ever reaches a Google account, and the page just says
   sign-in failed. Console → Authentication → Get started → Google. Console only; no CLI for it.
   Probed: `GET identitytoolkit.googleapis.com/v1/projects?key=<apiKey>` now answers with the
   authorized-domain list (`seatmatch-292b3.web.app` among them) instead of
   `CONFIGURATION_NOT_FOUND`, which is what a project with no auth config returns.
2. **One uid in the read rule** — `uXOeymlk16bxqP2Qi4rdlfi0BGi1`, in
   [database.rules.json](database.rules.json). Anyone else signing in gets `Permission denied`,
   which is the rule working rather than a fault.

⚠ **A new uid means a new deploy.** uids are per-project, so the sibling project's does not work
here, and a second person wanting the dashboard needs their uid added and
`npx firebase-tools deploy --only database` run again.

⚠ **None of this is needed for the numbers.** `scripts/pull_runs.py` prints the same per-level
table in the terminal, reads as project owner, and needs no Authentication, no uid and no sign-in.
The dashboard is a convenience; the script is the source.

⚠ **Never widen that to `auth != null`.** It reads as "signed-in users only" and means *any Google
account on earth*; anyone can make one in a minute, and `/runs` is the whole dataset.

⚠ **`stats.html` lives in `public/`, never in `dist/`.** `build.py` writes exactly one file into
`dist/` and never copies `public/`, so this cannot ride into the CrazyGames upload the way it could
on the sibling project — but the reason to keep it out is the same as the level editor: a dev tool
in front of a reviewer is a failed review.

---

## 3. Per-level reporting in GA — declare it or see nothing

The game sends two events (see [src/analytics.js](src/analytics.js)):

| event | parameters | fired |
|---|---|---|
| `level_start` | `level`, `diff` | on reaching a board, and again on every retry |
| `level_end` | `level`, `result` (`win`/`lose`), `seconds`, `stars` | on the win/lose card |

Plus GA's own `first_visit`, `session_start`, `page_view`, `user_engagement`.

`Analytics → Events` shows how often each fired. Splitting by level needs one more step, **without
which GA never shows the parameter at all**:

> GA4 → `Admin` → `Custom definitions` → `Create custom dimension`
> - Dimension name `level` · Scope **Event** · Event parameter `level`
> - Same again for `result`, `diff` and `stars`.
>
> ⚠ **Not retroactive.** It applies from the moment it is declared, so declare it early, and
> expect 24-48 hours before it appears in reports.

---

## 4. Three screens, three different lags

| screen | lag | use when |
|---|---|---|
| **Realtime** | ~1 minute | just deployed, want to know it works |
| **DebugView** | instant | testing yourself, event by event |
| **Dashboard** / reports | **24-48 hours** | trends |

**A Dashboard of zeros does not mean it is broken.** It aggregates once a day, so the first day
after switching Analytics on reads zero everywhere while data is flowing. Check Realtime instead.

---

## 5. What GA deliberately does not get

Kept out to keep the payload small: boosters used, revives, coins, moves, the board fingerprint,
the build stamp, the host. All of it is already in the Realtime Database, sliceable without GA's
lag and without declaring a dimension per field. Add `track(...)` calls only if you specifically
want to cut one of them by country or by session.

---

## 6. When something looks broken

**Step 1 — did the script even arrive?** Every row carries `ga`: `1` = gtag.js loaded, `0` =
blocked (adblock or the host page's CSP). `pull_runs.py` prints the ratio. All zeros means the
script is blocked, not that the code is wrong — and no amount of GA work will fix it, so use the
database instead.

**Step 2 — DebugView.** Open the game with `?debug_mode=1`, then `Analytics → DebugView`. Events
appear within seconds with their parameters.

**Step 3 — `python src/test_stats.py`.** Plays level 1000 headless (which `build.py`'s `TEST_CLOCK`
forces to a 5-second clock), intercepts the POST rather than letting it fly, and prints the row the
game would have sent. It also opens the privacy panel and asserts it carries no outbound links.

**Step 4 — the mistakes already paid for:**

1. **Pushing an array into `dataLayer` instead of `arguments`.** gtag.js only processes entries
   that are `arguments` objects; a real array is read as a GTM-style push and **ignored in
   silence**. The `gtag` helper must stay a plain `function` — an arrow has no `arguments`. This
   made the sibling project's first analytics build send nothing at all.
2. **A name collision with the shell.** `analytics.js` and `telemetry.js` are concatenated into the
   same scope as `engine.js` and `game_shell.js`. A duplicate `function` declaration in the shell
   **wins the hoist** and the file goes quiet with no error — this project has already lost a
   `confetti()` that way. Grep both before adding a name.
3. **Turning Analytics on in the console and assuming that is it.** That creates an empty GA4
   property. With no events sent, every panel stays at zero.

---

## 7. Three things not to break

- **`gtag.js` is not in the bundle**, and it loads when the player reaches a *level*, not at boot.
  Time-to-gameplay is a metric CrazyGames grades on, and a 145 KB cross-origin request at startup
  is exactly what the boot path avoids. Do not move `startAnalytics()` earlier — it is called from
  `gaLevelStart`, inside `startLevel`, on purpose.
- **[src/privacy.html](src/privacy.html) must match what is actually collected.** It is one
  fragment with two destinations: `build.py` inlines it into the game *and* writes
  `public/privacy.html` from it, so the hosted copy and the in-game copy cannot drift. Add a field
  to `telemetry.js` and that fragment is wrong the same day — and CrazyGames requires it to be
  right. In-game route: Settings → PRIVACY.
- **`build` is only honest on a clean tree.** `build.py` stamps the git short hash, and appends `+`
  when the tree is dirty, printing a warning. Commit before a build whose numbers you intend to
  read: a `+` row was played on code that is not the commit it names.

---

## 8. What no source has

A row is written only when a level **ends**. Someone who opens the game and quits mid-level never
appears in the database. GA does see them (`first_visit` fires on arrival), so for "how many people
bounce immediately" GA is the only answer — that, and CrazyGames' own dashboard.

A **revive** produces two rows, not one: the loss is already posted by the time the player pays, so
the bought continuation is a second row carrying `revive` in `used`. Counting rows counts *games*,
not *levels attempted* — filter on `used` when you want the unbought population.
