/* ---------------- Google Analytics 4 ----------------
   Ported from Marble Sort's `src/game/analytics.ts`. Two events, and the loader
   that fetches gtag.js the first time a board is reached.

   ⚠ Loaded on reaching a LEVEL, never at boot. "Time to gameplay" is a number
   CrazyGames grades on and it is measured to the `gameplayStart` call, so a
   145 KB cross-origin request on the boot path costs a metric that decides
   whether the game gets traffic. Nothing here may move earlier.

   ⚠ This file is concatenated between the platform door and game_shell.js, so
   every name in it shares one scope with the shell and the engine. A duplicate
   `function` declaration in the shell silently wins the hoist and this file
   goes quiet with no error. Checked against both at the time of writing; check
   again before adding a name.

   What GA is for, and what it is not: see ANALYTICS.md §0. Short version -
   GA answers "how many people, from where, coming back how often". It must
   never be asked for a winrate, because it records the level NUMBER and this
   campaign's boards get retuned underneath that number. The Realtime Database
   in telemetry.js carries the board fingerprint and is the only honest source
   for anything per-level. */

/** The web app's GA4 stream, read out of the Firebase project rather than
    retyped: `firebase apps:sdkconfig WEB <appId>` -> measurementId. */
const GA_ID = "G-TZ865K21Z4";

let gaLoaded = false;    // the script tag has been appended
let gaOk = 0;            // 1 once gtag.js actually ran - telemetry ships this

/** ⚠ A plain `function`, and it must stay one. gtag.js only processes dataLayer
    entries that are `arguments` objects; pushing a real array is read as a
    GTM-style push and dropped WITHOUT AN ERROR. An arrow function has no
    `arguments` at all, so rewriting this as one sends nothing and looks fine.
    This is the mistake that made Marble Sort's first analytics build a no-op. */
function gtag() {
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push(arguments);
}

/** Bring GA up. Safe to call on every level; only the first does anything. */
function startAnalytics() {
  if (gaLoaded) return;
  gaLoaded = true;
  try {
    const el = document.createElement("script");
    el.async = true;
    el.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    // An adblocker or the host page's CSP can refuse this. That is a normal
    // outcome, not a fault: `gaOk` stays 0, every row in the database says so,
    // and the database is what the numbers come from anyway.
    el.onload = () => { gaOk = 1; };
    document.head.appendChild(el);
    gtag("js", new Date());
    // ⚠ send_page_view stays on. It is what `first_visit` and `session_start`
    // hang off, and those are the only record of a player who opens the game
    // and leaves without finishing a level - see ANALYTICS.md §8.
    gtag("config", GA_ID, { game: "seataway" });
  } catch (e) { /* no GA this session; the database still gets its row */ }
}

/** One event. Never throws - a dead analytics call must not take a level down. */
function track(name, params) {
  try { gtag("event", name, params || {}); } catch (e) { /* as above */ }
}

/** ⚠ `level` and `result` show up in GA reports only after they are declared as
    custom dimensions, and the declaration is NOT retroactive. See ANALYTICS.md
    §3 - without that step the events are counted but cannot be split, which
    reads exactly like the parameters never being sent. */
function gaLevelStart(lvl, diff) {
  startAnalytics();
  track("level_start", { level: lvl, diff: diff });
}

function gaLevelEnd(lvl, won, seconds, stars) {
  track("level_end", {
    level: lvl,
    result: won ? "win" : "lose",
    seconds: seconds,
    stars: stars,
  });
}
