# Shipping to CrazyGames

What to actually do, in order.

Two paths: **§1 every update** (the one you will use), **§2 first submission only**.

---

## 1. Every update

```bash
git commit -am "…"               # BEFORE building — see the trap below
cd src && python build.py crazy
```

⚠ **Commit first.** Every telemetry row carries `build`, the git short hash, and it is the column
you reach for when two versions of a level disagree. Build on a dirty tree and `build.py` stamps
the rows `<hash>+` and says so on the build line — the fingerprint in `sig` still saves you, but
the build column stops naming a commit anyone can check out.

`build.py crazy` self-checks and refuses to finish quietly. It must print:

```
Bundle "crazy": ../dist/index.html - 3.99 MB
  OK   under 20 MB - keeps the mobile front page
  OK   relative paths only
  OK   CrazyGames SDK wired
  OK   Google Analytics wired
  OK   telemetry endpoint wired
  OK   privacy policy carried
  OK   no unfilled placeholders
  OK   no dev tools
```

The last four are new and each one has a reason:

- **Google Analytics / telemetry endpoint** — a build with the tracking switched off "just for a
  test" looks perfect and reports nothing, and the first sign of it is an empty dashboard a week
  later, which reads as a bug in the *reading*.
- **privacy policy carried** — the submission form demands one and the reviewer follows the
  in-game route to it. Missing it is a failed review, not a retry.
- **no unfilled placeholders** — a policy that ships the literal text `PASTE_A_CONTACT_EMAIL`
  names nobody.

Then upload:

> Developer Portal → your game → **Builds / Files** → drag the **contents of `dist/`** into the
> upload zone → save → submit for review.

⚠ **Do not zip it.** The upload box rejects archives with *"Archive files are not supported,
please drag and drop the files directly in the upload zone"*. Drag the folder contents; the
browser keeps the tree. The sibling project lost two attempts to this.

⚠ **Drag `dist/`, never the repo.** `dist/` holds exactly one file, written by `build.py`.
`level_player.html` (the level editor) and `public/stats.html` (the dashboard) are not in it and
must never be — a dev tool in front of a reviewer is a failed review.

### If the privacy policy changed

Edit **[src/privacy.html](src/privacy.html)** — never the two outputs. It is one fragment with two
destinations: `build.py` inlines it into the game *and* writes `public/privacy.html` from it, so
the hosted copy the form points at and the in-game copy a reviewer opens cannot drift.

```bash
npx firebase-tools deploy --only hosting     # → https://seatmatch-292b3.web.app/privacy.html
```

⚠ **It must match what the game actually collects.** Add a telemetry field and that page is wrong
the same day. See [ANALYTICS.md](ANALYTICS.md) §7.

### If the database rules changed

```bash
npx firebase-tools deploy --only database
```

---

## 2. First submission only

- [x] Firebase project, Realtime Database (Singapore) and GA4 — [ANALYTICS.md](ANALYTICS.md) §1
- [x] Database rules deployed and probed three ways — ANALYTICS.md §1
- [x] Three covers: [store/crazygames/](store/crazygames/) — 1920×1080 · 800×1200 · 800×800
- [x] Two preview videos, 15-20s, in `Manythings/` — landscape and portrait, both 17.95s
- [x] A contact address in the privacy policy
- [x] Hosting deployed — `https://seatmatch-292b3.web.app/privacy.html` answers 200
- [x] Authentication on, and a uid in the database read rule — ANALYTICS.md §2
- [ ] Payment details set up — must be done *before* submitting, not after approval
- [ ] Run the portal's **Quality Assurance Tool**, clear every warning

Form answers that have consequences:

| field | answer | why |
|---|---|---|
| Game engine | **HTML5** | not "Externally hosted (iframe)" — that is for games you host yourself |
| Orientation | **Both** | `frame()` in engine.js lays the room out differently for each, and both preview videos exist |
| Supports mobile | **tick** | the design box is 540×1160 and the phone frame is the one it was tuned against |
| SDK muting | **tick** | implemented in [src/platform_crazy.js](src/platform_crazy.js); leaving it unticked makes the mute handling inert |
| Saves progress | **Yes, using the Data Module** | *and switch the Progress Save feature on* — the module does nothing while the toggle is off |
| Online game | **no** | no multiplayer |
| Privacy policy | `https://seatmatch-292b3.web.app/privacy.html` | ⚠ form only |

⚠ **The privacy link goes in the form AND in the game, but never as an outbound link in the UI.**
Outbound links are banned. The in-game route is Settings → **PRIVACY**, which opens a panel inside
the same page — `src/test_stats.py` asserts that panel contains zero `<a href>`.

---

## 3. Verifying before upload

The build script covers the hard limits. These are the ones it cannot see:

```bash
cd src
python test_crazy.py     # boots with the SDK unreachable? save survives? host mute outranks?
python test_stats.py     # a finished level posts a row; the privacy panel opens and has no links
```

`test_crazy.py` blocks `sdk.crazygames.com` the way an adblocker does — the request never answers
and never errors — because that is the case that parks a player on a dead boot screen forever, and
it is the case a working network never shows you.

⚠ **`test_stats.py` opens the level with `?intro=none`.** A fresh save owes every feature
walkthrough at once, and a walkthrough *pauses the board*, so the clock never runs and the level
never ends. Without that flag the script times out on a build that is working perfectly.

---

## 4. The preview videos

Both in `Manythings/` (gitignored), rebuilt by one ffmpeg command each.

| | source | length |
|---|---|---|
| `SeatAway_trailer_landscape_1920x1080.mp4` | desktop capture, straight cut from 0:04 | 17.95s |
| `SeatAway_trailer_portrait_1080x1920.mp4` | same, cropped `748:1080:604:0` onto a blurred backing | 17.95s |

Rules learned the hard way:

- **15-20 seconds.** Outside that window it is rejected. ⚠ Cutting to "exactly 18" produced an
  **18.018s** file — the capture is VFR at ~29.97fps and the last frame runs past the mark. Ask for
  17.95.
- ⚠ **No black bars — explicitly banned.** The game does not match either store frame, so the
  portrait cut fills the sides with a blurred, scaled copy of the gameplay itself.
- ⚠ **No mouse cursor** — on their prohibited list. Xbox Game Bar captures it by default;
  Settings → Gaming → Captures.
- Recording: `Win + Alt + R` starts and stops, output in `%USERPROFILE%\Videos\Captures`.
  ⚠ It records the **focused window** — Alt-Tab mid-take and the recording ends there.

---

## 5. Things that must never change after launch

- ⚠ **`SAVE_KEY = "seatmatch.save.v2"`.** Automatic Progress Save backs up `localStorage` verbatim,
  so renaming it after launch restores the old name into a game that reads the new one and every
  player loses everything. Renamed from `seatawayo.save.v1` on 8 Sep 2026 — the last free moment,
  spent deliberately so the key carries the game's title rather than the repo's folder name.
- ⚠ **It is `.v2` because `seatmatch.save.v1` is taken.** `localStorage` is keyed by **origin**, not
  by path, so everything under `cuongpc19.github.io` shares one storage area — and the sibling port
  in `../seataway` writes `seatmatch.save.v1`. Its deploy answers 404 today, which makes the
  collision look theoretical; it is one redeploy away from two campaigns writing one save. The
  GitHub folder and the `/SeatAwayO/` deploy path stay as they are, so the suffix is the only thing
  keeping them apart. Do not "tidy" it to `.v1`.
- ⚠ **`OLD_KEYS` stays empty.** Adopting another key would copy a campaign's progress into a
  campaign where the level numbers mean something else — and that includes the old
  `seatawayo.save.v1`: the rename was a fresh start, not a migration.

---

## 6. What Basic Launch actually grades

Not just a quality review: a **two-week limited-traffic run**, with their QA watching engagement
while it runs. Those numbers decide Full Launch.

| metric | good | ours |
|---|---|---|
| avg session length | 10+ min | watch it in `stats.html` |
| day-1 retention | 10-15% | localStorage + Progress Save |
| reached gameplay | 80%+ | one tap from Home |
| build size | < 20 MB | **3.99 MB** ✓ |

⚠ **"Time to gameplay" is measured to the `gameplayStart` call**, not to first paint. That is why
`startAnalytics()` loads gtag.js on reaching a *level* rather than at boot, and why nothing may be
added to the boot path without checking this number. See ANALYTICS.md §7.
