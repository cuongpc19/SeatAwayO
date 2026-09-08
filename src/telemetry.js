/* ---------------- the game's own telemetry ----------------
   Ported from Marble Sort's `src/game/telemetry.ts`. One row per finished
   level, written straight into the Firebase Realtime Database.

   Why this exists next to GA at all (ANALYTICS.md §0): GA records the level
   NUMBER, and a number is not a board. The clock, the grading and the campaign
   file itself all get retuned here, so games played on a board that no longer
   exists sit under the same number as games played on the one that replaced it,
   and GA will average them into one convincing, wrong figure. Every row below
   carries `sig`, the board's fingerprint, so a retune is visible instead of
   silently folded in. This is the exact mistake that wrecked a calibration pass
   on the sibling project - do not measure a winrate in GA.

   ⚠ Concatenated between the platform door and game_shell.js, sharing one scope
   with the shell and the engine. A duplicate `function` name in the shell wins
   the hoist and this file goes quiet with no error. Checked against both;
   check again before adding a name.

   ⚠ Nothing here may throw, block, or hold up a card. A player whose network
   refuses the write must not be able to tell. */

/** ⚠ The one place the endpoint is spelled out. scripts/pull_runs.py points the
    Firebase CLI at the instance by NAME instead of repeating this, and
    public/stats.html is configured by the SDK, so a region change is a one-line
    change here plus the instance name there - not a hunt.

    The region is in the hostname, so it is not cosmetic: a database created in
    us-central1 is `...-default-rtdb.firebaseio.com` with no region segment and
    this URL would 404 forever, silently, because nothing here reports a failed
    write. Probed rather than assumed: this project's instance answers on
    asia-southeast1 and the other two hostnames redirect to it. ANALYTICS.md §1. */
const RUNS_URL = "https://seatmatch-292b3-default-rtdb.asia-southeast1.firebasedatabase.app/runs.json";

/** Stamped by build.py from the git short hash, so a row says which build
    played it. ⚠ It is the working tree's HEAD - building on a dirty tree
    stamps every row with the PREVIOUS commit. Commit before building. */
const BUILD = "/*__BUILD__*/";

/** Hosts whose games are ours, not a player's. Filtered on READ, not blocked on
    write (see ANALYTICS.md §2): a blocked row is gone forever, a filtered one is
    still there when the question changes. */
function isDevHost(h) {
  return h === "localhost" || h === "127.0.0.1" || h === "" ||
         /^192\.168\./.test(h) || /^10\./.test(h) || /^172\.(1[6-9]|2\d|3[01])\./.test(h);
}

/** FNV-1a, 32 bit, over the fields that decide what a board actually is.

    Not over the whole record: `name`, `sourceId` and `track` are bookkeeping,
    and folding them in would make a fingerprint that changes when nothing a
    player could feel has changed. `time` and `diff` ARE in, because both are
    set by build.py's tuning and a board whose clock moved is a different board
    to win or lose on. */
function runSig(b) {
  if (!b) return "0";
  const s = JSON.stringify([b.w, b.h, b.time, b.diff | 0, b.door, b.door2,
                            b.panel, b.holes, b.seats, b.queue, b.queue2,
                            b.secondDoor, b.obstacles, b.holeObstacles,
                            b.colouredGrid, b.mods]);
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
  }
  return h.toString(36);
}

/* What the run in progress has done so far. Reset by teleStart. */
let teleAt = 0;          // performance.now() when the board opened
let teleLvl = 0;
let teleSig = "0";
let teleDiff = 0;
let teleUsed = [];       // booster ids spent on this run, in order

/** Called as a board opens. ⚠ Also on a retry, which is what makes a retry its
    own row rather than a continuation - the level was played twice and the
    database should say so. */
function teleStart(lvl, board) {
  teleAt = performance.now();
  teleLvl = lvl;
  teleSig = runSig(board);
  teleDiff = board ? (board.diff | 0) : 0;
  teleUsed = [];
}

/** A booster or a revive was spent on the run in progress. Kept out of GA on
    purpose (ANALYTICS.md §5) - it is sliceable here without a custom dimension
    per field and without GA's day-long lag. */
function teleBooster(id) {
  if (teleUsed.length < 40) teleUsed.push(id);   // a cap, so a stuck button cannot post a novel
}

/** The player bought their way past a loss and is still on the same board.

    ⚠ Needed because onFinish() has already fired and posted the losing row by
    the time revive() runs. Without re-arming the clock the continued game would
    post nothing at all and a bought win would vanish from the data. Two rows is
    the honest account of what happened: a loss, then a second game carrying
    `revive` in `used` - which is exactly what PURE-style filtering keys on. */
function teleResume(id) {
  teleBooster(id);
  teleAt = performance.now();
}

/** One finished level. Fire and forget. Returns the run's length in ms so the
    GA event and the database row cannot disagree about it. */
function teleEnd(won, stars) {
  if (!teleAt) return 0;               // ended without ever having started - nothing honest to say
  const ms = Math.round(performance.now() - teleAt);
  teleAt = 0;                          // ⚠ so a second card on the same run cannot post twice
  let host = "";
  try { host = location.hostname; } catch (e) { /* no location in some frames */ }
  const row = {
    lvl: teleLvl,
    sig: teleSig,
    diff: teleDiff,
    result: won ? "win" : "lose",
    ms: ms,
    moves: (typeof S === "object" && S && S.moves) | 0,
    stars: stars | 0,
    build: BUILD,
    dev: isDevHost(host) ? 1 : 0,
    host: host,
    from: (typeof PLATFORM === "object" && PLATFORM && PLATFORM.name) || "web",
    // ⚠ 1 = gtag.js ran, 0 = it was blocked. When `npm`-side tallies show this
    // at all zeros the GA property is empty because the script never arrived,
    // not because the tracking code is wrong. First thing to check - §6.
    ga: gaOk,
    t: Date.now(),
  };
  // ⚠ Absent, not empty. The database drops empty arrays, so an `used` that is
  // missing means no booster was spent - sending [] would store nothing anyway
  // and only makes the rules' shape check harder to write.
  if (teleUsed.length) row.used = teleUsed.slice();
  try {
    // keepalive so the write survives the player pressing NEXT LEVEL straight
    // away. No `await`, no `.then` that touches the game: a refusal here is a
    // lost row, never a lost card.
    fetch(RUNS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(row),
      keepalive: true,
      mode: "cors",
    }).catch(() => { /* offline, blocked, or the rules said no */ });
  } catch (e) { /* fetch missing entirely - nothing to do and nothing to report */ }
  return ms;
}
