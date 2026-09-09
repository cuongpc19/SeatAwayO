/* ---------------- the game shell ----------------
   Everything the editor page does not need: saved progress, a home screen, a
   level picker, and a result card. The rules all live in the engine above; this
   file only decides what the player sees around them.                        */

RICH = true;                       // the engine draws a room, not a bare grid

/* ---- the address bar --------------------------------------------------
   One read of the query string, at load, for the whole shell - the way Marble
   Sort does it. `location.search` cannot change without a reload, so the three
   separate reads this replaced were three copies free to drift apart, and did:
   the theme was read out of a URL the reset flag had not been stripped from yet.

     ?level=N     open board N straight away, past the home screen and past the
                  unlock gate - the picker only lists what has been earned,
                  which is no help when the board you want is number 300.
     ?reset=1     wipe the save before it is read. ?reset=1&level=1 is a clean
                  run from the very top.
     ?win=1       hand every board a win the moment it opens, so the
                  celebration and the result card can be read on any level
                  without solving one.
     ?intro=NAME  mark every other piece as met, so NAME's walkthrough is the
                  one this level owes: grey | twin | jump | time | area
     ?theme=NAME  pin one room and stop the five-level rotation.
                  classroom | station | stadium | concert | cinema
     ?hard=0|1|2  pin the party dressing on any board, rather than taking it
                  from the board's own grading - the five party rooms are
                  otherwise only reachable on the levels that carry them.
     ?bg=NAME     swap the procedural room for a painted bg/NAME.png.

   None of them is a way round the campaign: the level still has to be won to
   unlock the next, and a reset is just the blank save.

   A bare flag counts. Marble Sort tests `p.get("reset")`, which is `""` for
   `?reset` and so ignores the form a person types first; here `=0` is the only
   way to write a flag off.

   The reset flag is dropped from the address bar once read, or every later
   refresh would throw away the progress made since. `win` is deliberately kept:
   it is a way of looking at something, and refreshing to see it again is the
   whole use. Reading the flags into constants before editing `LINK` is what
   makes that safe - the value is captured, not looked up a second time. */
const LINK = new URLSearchParams(location.search);
const flag = k => LINK.has(k) && LINK.get(k) !== "0";
const RESET_ASKED = flag("reset");
/* ?intro=NAME  every other piece counts as already met, so NAME is the one this
   level owes. For reading one walkthrough without playing up to it - ?reset=1
   on its own hands you the earliest one you have not seen, which is the grey
   seat from level 7, not the one you came to look at. */
const INTRO_ONLY = LINK.get("intro");
/* ?pace=N forces one crossing pace on every board, for comparing one value
   against another without a rebuild. 1 is the pace measured off the recording;
   left off, the pace comes off the room's size - see walkPace() in engine.js.
   Out of range values are ignored rather than clamped: a typo should not hand
   anybody a board that takes a minute to cross. */
const PACE_ASKED = parseFloat(LINK.get("pace"));
if (PACE_ASKED >= 0.2 && PACE_ASKED <= 3) PACE_FORCED = PACE_ASKED;
const WIN_ASKED = flag("win");
if (RESET_ASKED) {
  LINK.delete("reset");
  const rest = LINK.toString();
  history.replaceState(null, "", location.pathname + (rest ? "?" + rest : ""));
}

/* The room changes every five levels and then starts the rotation over, so a run
   of play keeps moving somewhere new without needing 633 rooms to do it.
   ?theme=<name> pins one for testing and stops the rotation. */
const MOVIE_SRC = "/*__MOVIE__*/";
const COVER_SRC = "/*__COVER__*/";       // the home screen's own render
const BUILT = "/*__BUILT__*/";           // the stamp on the home screen's foot
const THEME_RUN = 5;                    // levels before the room changes
const THEME_ORDER = ["classroom", "station", "stadium", "concert", "cinema"];
const pinnedTheme = LINK.get("theme");
const pinnedHard = LINK.get("hard");

/** The still on the cinema screen. Loaded once at boot rather than when a cinema
    level comes up: it is inlined in the build, so there is nothing to wait for,
    and a level should never open on a blank screen while an image decodes. */
{
  const m = new Image();
  m.onload = () => { MOVIE = m; if (THEME === "cinema") draw(); };
  // the served build reads the file; a published one carries it inline
  m.src = MOVIE_SRC || "bg/movie1.jpg";
  // the still hangs still, so this screen needs no beat of its own
}

function themeFor(level) {
  if (THEMES[pinnedTheme]) return pinnedTheme;
  return THEME_ORDER[Math.floor((level - 1) / THEME_RUN) % THEME_ORDER.length];
}

function applyTheme(level) {
  const wasTheme = THEME;
  THEME = themeFor(level);
  /* A marked board is played in the same room with the party thrown in it - see
     PARTY in the engine. Read off the board, exactly like the chip and the
     warning card, so the three of them cannot disagree about which levels are
     hard: a list of level numbers written here would be a second copy of the
     grading, and the campaign numbering has already moved once. */
  const b = boardOf(level);
  // A bare ?hard counts as grade 1, the way a bare flag counts everywhere else
  // in this block - it is the form a person types first.
  HARD = pinnedHard == null ? (b ? b.diff | 0 : 0)
       : pinnedHard === "" ? 1
       : Math.max(0, Math.min(2, +pinnedHard || 0));
  // whatever the canvas does not cover should be the room's own colour, not the
  // one left behind by the level before it. themeNow(), not THEMES: a party
  // paints a different page behind the same room.
  // ⚠ A cue belongs to the board that was cleared. Moving to a room of another
  // kind while its tail is still sounding plays a station horn in a classroom.
  if (THEME !== wasTheme) ambStop();
  const page = themeNow().page;
  document.getElementById("play").style.background = page || "#98a1ab";
}

/* Drop a painted room at bg/room.png (or pass ?bg=<name>) and it replaces the
   procedural station. Missing file, no harm: the station stays. */
(() => {
  // Only when asked for by name: guessing at a file meant every single load
  // reported a 404 for a plate nobody had made yet.
  const name = LINK.get("bg");
  if (!name) return;
  const img = new Image();
  img.onload = () => { BG = img; draw(); };
  img.src = "bg/" + name + ".png";
})();

/* ---- the numbers the shipped game runs on -----------------------------
   Injected from its own RemoteConfig at build time. Every threshold, price and
   reward below is the live value, not a guess. */
const CF = /*__CONFIG__*/;
const unlockedAt = f => { const n = CF.unlock[f]; return n > 0 ? n : Infinity; };
/* A booster is open once the player has reached the level that opens it.
   `save.unlocked` alone answers that for ordinary play - it is always at or
   past the level being played - but not for a board opened straight from
   `?level=N`, where it says 1 and the whole bottom bar comes up locked on a
   level that is meant to have it. Standing on the level is what counts. */
const has = f => Math.max(save.unlocked, CUR || 0) >= unlockedAt(f);

/* ---- saved progress ---------------------------------------------------- */
/* ⚠ This name is fixed from launch on. CrazyGames' Progress Save backs up
   localStorage verbatim, so renaming the key later restores the old name into a
   game that reads the new one and every player loses everything. The window in
   which a rename is free is before anyone has played, and this build spends it:
   renamed from `seatawayo.save.v1` on 8 Sep 2026, deliberately, to carry the
   game's real title instead of the repo's folder name.

   ⚠ `.v2`, and NOT `seatmatch.save.v1`, which looks like the obvious name and
   is already taken. localStorage is keyed by origin and pays no attention to
   path, so everything under https://cuongpc19.github.io shares one storage
   area, and the sibling port in ../../seataway writes `seatmatch.save.v1` from
   its own source. Its deploy answers 404 today, which makes the collision look
   theoretical - it is one redeploy away from being two different campaigns
   writing one save. The suffix is what keeps them apart, so do not "tidy" it.

   OLD_KEYS is empty on purpose, and stays empty. Adopting a key is the same
   mistake in slower motion - it would copy another campaign's progress into
   this one on first load, and levels do not mean the same thing across the two,
   so an `unlocked` from over there is a number this campaign never earned. That
   applies to `seatawayo.save.v1` as well: the rename above is a fresh start,
   not a migration, and any test progress under the old name is meant to be left
   behind rather than carried over.

   Keeping it empty also settles the other direction: a reset here clears this
   key alone, and cannot reach into a save that belongs to another build. */
/* ⚠ v3, because v2's level numbers no longer name the same boards. The ladder
   moved to the APK's own order from level 15 on, so a v2 save saying "unlocked:
   30" would open a board its owner has never seen and hand them stars for it.
   OLD_KEYS stays empty: adopting that save is exactly what must not happen. */
const SAVE_KEY = "seatmatch.save.v3";
const OLD_KEYS = [];
const blank = () => ({
  unlocked: 1, stars: {}, coins: 0,
  seenBoosters: [],                // which unlock notices have been shown
  streak: 0,                       // wins in a row
  hearts: CF.heartMax, heartAt: 0, // heartAt: when the next one lands, ms epoch
  jumps: 0,                        // jump booster charges bought
  lines: 0,                        // add-line booster charges bought
  freeTime: 0,                     // free goes at the time booster, from its tutorial
  sound: true, vibe: true,         // the two switches in Settings
});
/* ⚠ The read is deferred to boot(), after PLATFORM.init() has resolved. On a
   host that keeps a cloud save, reading before init returns the local copy and
   the next write pushes that stale copy over the player's real save. Until then
   this is the blank save, which nothing writes because nothing can be pressed
   while the home screen has not been shown. */
let save = blank();
function loadSave() {
  if (RESET_ASKED) {
    for (const k of [SAVE_KEY].concat(OLD_KEYS)) PLATFORM.storage.removeItem(k);
    return;
  }
  try {
    let raw = PLATFORM.storage.getItem(SAVE_KEY), adopted = false;
    for (const k of OLD_KEYS) {
      if (raw) break;
      raw = PLATFORM.storage.getItem(k);
      adopted = !!raw;
    }
    save = Object.assign(blank(), JSON.parse(raw || "{}"));
    /* ⚠ `!raw` too. A brand-new player had no save written until they finished
       something, so the first session left nothing behind at all - and on a host
       with cloud storage that is progress which starts existing one level later
       than the player thinks it does. */
    if (adopted || !raw) persist();
  }
  catch (e) { /* private window, cleared data, a browser that refuses storage */ }
}
function persist() { PLATFORM.storage.setItem(SAVE_KEY, JSON.stringify(save)); }
const totalStars = () => Object.values(save.stars).reduce((a, v) => a + v, 0);

/* Hearts refill on the clock whether the page is open or not, so the count is
   worked out from the stored timestamp rather than ticked down. */
function hearts() {
  /* ⚠ Lives off - see LIVES in build.py. Full, always, and the save is not
     touched: the stored count and the timestamp are left exactly as they are so
     that turning lives back on picks up whatever the player had rather than
     handing everyone a fresh set. */
  if (!CF.lives) return CF.heartMax;
  if (save.hearts >= CF.heartMax) { save.heartAt = 0; return save.hearts; }
  const now = Date.now();
  if (!save.heartAt) { save.heartAt = now + CF.heartSecs * 1000; persist(); }
  while (save.hearts < CF.heartMax && now >= save.heartAt) {
    save.hearts++;
    save.heartAt = save.hearts >= CF.heartMax ? 0 : save.heartAt + CF.heartSecs * 1000;
  }
  return save.hearts;
}
const heartIn = () => (!CF.lives || save.hearts >= CF.heartMax || !save.heartAt) ? 0
  : Math.max(0, Math.ceil((save.heartAt - Date.now()) / 1000));

/** What a win pays: a flat purse, plus the win-streak bonus once it is unlocked. */
function purse() {
  let gold = CF.goldWin, bonus = 0;
  if (has("winstreak")) {
    for (const [at, v] of CF.streakGold) if (save.streak + 1 >= at) bonus = v;
  }
  return { gold, bonus, total: gold + bonus };
}

/** Stars come off the clock, the one thing the level data itself scores. */
function starsFor(g) {
  const frac = g.left / g.time;
  return frac >= .55 ? 3 : frac >= .25 ? 2 : 1;
}

/* ---- screens ----------------------------------------------------------- */
const screens = { home: "home", levels: "levels", play: "play" };
function show(name) {
  /* ⚠ Leaving the board is what stops play, so the screen change is what says
     so - see setPaused(). Every exit used to say it for itself, which is the
     arrangement that guarantees one is missed: HOME from the settings menu
     unpaused on its way out and told the host play had just STARTED, and then
     never stopped it. The clock kept running on the home screen too. */
  setPaused(name !== "play");
  for (const id of Object.values(screens))
    document.getElementById(id).classList.toggle("on", id === name);
  if (name === "home") refreshHome();
  if (name === "levels") buildGrid();
  if (name === "play") requestAnimationFrame(draw);
}
/* ---- the design box ----------------------------------------------------
   The home screen and the results card are ports of Marble Sort's, and that
   game lays both out in a fixed 540 x 1160 box which Phaser then FITs to the
   frame. Rather than convert several dozen coordinates into percentages and
   lose the ability to diff them against their source, the box is kept: `--k`
   scales it, and everything inside is written in design units.

   Home is the one screen that may be wide, and the reason is that it is the one
   screen with no board on it - `fitCanvas` gives the carriage a portrait strip
   whatever the window does, so a landscape frame on any other screen is empty
   room the game cannot grow into. Home is a picture and two buttons, and has
   nothing to lose by filling the frame, so it widens its own box instead.     */
const DW = 540, DH = 1160;
/* The furniture at the foot of the home screen, measured up from the foot of
   the design box. Nothing here may be an absolute y: the box is 1160 tall on a
   phone and shorter on a squat desktop frame, and a PLAY button written as
   "952" is drawn below the bottom edge of the one screen it exists for. */
/* ⚠ 228, not 208. Two lines now hang under the purse and the whole column -
   button, purse, two lines, build stamp - has to fit between the art and the
   foot of the box. The only slack left was above the button. */
const PLAY_UP = 228;
/* ⚠ 140, not 98. Two lines now sit under the purse and the build stamp is
   pinned at 1120, so at 98 they landed on top of it. The ceiling is the PLAY
   button: its foot is at 990, so the purse cannot rise past about 1011 without
   touching it. */
const WALLET_UP = 140;

const WIDE_FROM = 1.2;             // where furniture becomes a landscape menu
const WIDE_COL = .95;              // how much room the column beside the art may take

/* The cover is inlined by the build; a served page reads the file beside it.
   Both layers are the same image - the crisp one, and a blurred copy that fills
   the box either side of it on a wide frame. */
{
  const src = COVER_SRC || "art/home_cover.png";
  document.getElementById("h-cover").src = src;
  // the same file again, for the two strips that fill a wide box either side
  document.getElementById("home").style.setProperty("--cover-url", 'url("' + src + '")');
}

function fitDesign() {
  const app = document.getElementById("app");
  const w = app.clientWidth, h = app.clientHeight;
  if (!w || !h) return;
  const k = Math.min(w / DW, h / DH);
  app.style.setProperty("--k", k);

  // Home's own box: never narrower than the design width, or a portrait phone
  // asks for a box taller than 540 x 1160 and letterboxes the one screen that
  // has no letterbox anywhere else in the game.
  const W = Math.max(DW, w / k);
  const wide = W / DH >= WIDE_FROM;
  // Cover, not contain: the 2:3 render fills the screen and there is no painted
  // ground under it. Wide, it is fitted to the height and moved left instead of
  // being blown up - covering a 16:9 box with a 2:3 render keeps 37% of its
  // height, and the pieces are in the part that would go.
  const scale = wide ? DH / 1620 : Math.max(W / 1080, DH / 1620);
  const artW = 1080 * scale, artH = 1620 * scale;
  const colWant = wide ? Math.min(W - artW, artW * WIDE_COL) : 0;
  // The art and the column are laid out as one group, centred, rather than the
  // art taking a fixed share of the width: on a 21:9 monitor a fixed share puts
  // a third of the screen of nothing between them.
  const groupL = wide ? (W - artW - colWant) / 2 : 0;
  const groupR = wide ? groupL + artW + colWant : W;
  const artCx = wide ? groupL + artW / 2 : W / 2;
  const uiCx = wide ? artCx + artW / 2 + colWant / 2 : W / 2;
  const playY = wide ? DH * .5 : DH - PLAY_UP;

  const st = document.getElementById("home").style;
  const set = (n, v) => st.setProperty(n, v);
  set("--dw", W);
  /* ⚠ Portrait hangs the render from the TOP of the box rather than centring
     it, and that is about where the empty part goes. The render is 2:3 with a
     quarter of bare gradient above the title and better than a third below the
     seats; a phone is nearer 1:2, so something has to be cropped. Centred, the
     crop is split and half of it comes off the top - which pulls the title and
     the seats UP, away from the button, and opens the gap this was meant to
     close. Hung from the top, all of it comes off the bottom, which is the part
     the button and the purse are drawn over anyway.

     Zooming instead was tried and clipped the title: the crop is uniform, and
     "Seat Match" runs nearly the full width of the render, so any zoom that
     closes the vertical gap eats the S and the h on a narrow phone. */
  set("--art-l", artCx - artW / 2);
  set("--art-t", wide ? (DH - artH) / 2 : 0);
  set("--art-w", artW);              set("--art-h", artH);
  set("--art-cx", artCx);
  set("--ui-cx", uiCx);
  set("--play-y", playY);
  // Bigger on a wide box, not the same button moved sideways - and capped
  // against the column, because just past WIDE_FROM the space beside the art is
  // narrower than a 1.7x button.
  set("--play-s", wide ? Math.min(1.7, colWant * .78 / 260) : 1.35);
  set("--wallet-y", wide ? playY + 118 : DH - WALLET_UP);
  set("--wallet-s", wide ? 1.25 : 1);
  // The two corner buttons line up with the group, not with the canvas: pinned
  // to the edge they are the only things left touching it once everything else
  // has been pulled in, and read as the layout having missed them.
  set("--corner-l", wide ? groupL + 36 : 70);
  set("--corner-r", wide ? groupR - 36 : W - 70);
  set("--edge-r", W - (artCx + artW / 2));
  document.getElementById("h-scrim").hidden = wide;
  document.getElementById("h-edge-l").hidden = !wide;
  document.getElementById("h-edge-r").hidden = !wide;
}

function refreshHome() {
  fitDesign();
  const lvl = save.unlocked;
  // One button, always. It says where the player is rather than "PLAY", which
  // is the only place the level number appears on this screen now.
  $("h-play").textContent = lvl > 1 ? "LEVEL " + lvl : "PLAY";
  $("h-stars").textContent = totalStars();
  $("h-coins").textContent = save.coins;
  /* ⚠ Read off the boards, not off the 5-and-9 rule. The rule is what GRADES
     them, but the ladder drops fifteen boards the APK carries, so our level 88
     is its 89 and the marked ones do not land on a tidy rhythm of ours. Scanning
     for the next graded board is the only reading that cannot drift. */
  const nh = $("h-nexthard");
  if (nh) {
    const at = nextHardFrom(Math.min(save.unlocked, CAMPAIGN.length));
    nh.hidden = !at;
    if (at) nh.innerHTML = "Next hard level: <b>" + at + "</b>";
  }
  /* ⚠ Rounded down off CAMPAIGN.length, not written out. "2,000+" has to stay
     true if the ladder moves, and it has moved twice; a number typed here is a
     second copy of the campaign that goes stale without anything failing. */
  const wt = $("h-waiting");
  if (wt) {
    const round = Math.floor(CAMPAIGN.length / 500) * 500;
    wt.hidden = round < 500;
    wt.textContent = round.toLocaleString("en-US") + "+ levels waiting for you";
  }
  $("h-star-icon").innerHTML = STAR_ON;
  const left = hearts(), w = heartIn();
  const heart = $("h-hearts");
  heart.hidden = !CF.lives;          // a counter that cannot move is furniture
  heart.classList.toggle("full", left >= CF.heartMax);
  heart.querySelector("b").textContent = left;
  // A badge that is always on is furniture within a day, so the countdown only
  // appears while there is actually a life on its way.
  heart.querySelector("em").textContent = w ? fmt(w) : "";
  $("h-ver").textContent = BUILT ? "build " + BUILT : "";
}

/* ⚠ A progress board, not a picker. It used to start any cleared level, which
   made the ladder optional - a player could hop back to an easy one, and the
   number on the home button stopped meaning where they are. It answers one
   question now: how far along am I. Nothing here starts a level; PLAY is the
   only way onto a board, and the cells are divs rather than buttons so there is
   nothing to press.

   ⚠ Still a window, not all 2085. A wall of two thousand cells is not a
   picture of progress, it is a scroll bar - so it shows the run up to where the
   player is with a little of what is ahead, and the line above it carries the
   total. */
/* ⚠ What is AHEAD, not what is behind. The levels already cleared were most of
   what this screen showed, and they are the part the player has no use for: they
   cannot be replayed and the stars for them are already summed on the line
   above. What is worth showing is the road - where they stand, what is coming,
   and how much of it there is.

   The tail is the point of the ellipsis. Two thousand cells is a scroll bar, not
   a fact; a run of the next few, a gap, and the last level says "there are two
   thousand of these" in one glance. */
/* ⚠ Ours. Past this level a win ends at the home screen instead of on the next
   board - see overlay(). The first levels run one into the next because that is
   the stretch where stopping is what loses a player. */
const HOME_AFTER = 10;

/** The next level carrying a warning, from `n` on. Hard and super hard both
    count: to a player they are the same thing arriving, and splitting them here
    would be a distinction the home screen cannot afford the room to draw. */
function nextHardFrom(n) {
  for (let i = Math.max(1, n); i <= CAMPAIGN.length; i++) if (diffOf(i)) return i;
  return 0;
}

const GRID_AHEAD = 29;          // the level they are on, plus this many to come

function buildGrid() {
  const grid = document.getElementById("l-grid");
  grid.innerHTML = "";
  const last = CAMPAIGN.length;
  const here = Math.min(save.unlocked, last);
  const upto = Math.min(last, here + GRID_AHEAD);
  const sum = $("l-sum");
  if (sum) sum.innerHTML = "LEVEL <b>" + here + "</b> OF " + last
      + " &middot; " + totalStars() + " STARS";

  const cell = n => {
    const b = document.createElement("div");
    const d = diffOf(n);
    /* ⚠ `ahead`, not `locked`. Locked was styled to win over the difficulty
       colours, which was right when a cleared board and an unreachable one sat
       side by side. Every cell here is unreached, so that rule painted the whole
       screen one grey and swallowed the one thing it is meant to show. */
    b.className = "cellbtn " + (n === here ? "here" : "ahead") + (d ? " " + d.cls : "");
    b.innerHTML = (d ? '<span class="d">' + d.tile + "</span>" : "") + n;
    grid.appendChild(b);
  };

  for (let n = here; n <= upto; n++) cell(n);
  /* The gap, then the far end. Only when there is actually something between
     them - on the last thirty levels there is nothing to elide. */
  if (upto < last - 1) {
    const dots = document.createElement("div");
    dots.className = "cellbtn dots";
    dots.textContent = "\u2026";
    grid.appendChild(dots);
    cell(last);
  } else {
    for (let n = upto + 1; n <= last; n++) cell(n);
  }
}

/* ---- playing -----------------------------------------------------------
   1.63.1 ships exactly one board per level id, so the filter passes everything
   and the ladder is simply the campaign in order. It is kept because the binary
   levels it was written for are still on disk behind build.py's LEGACY, where
   33 of the 633 boards were second and third arrangements shipped under a level
   name the game already used, and a few of those are display pieces nobody can
   clear. Counting them as levels pushed every number after the third out of step
   with the APK - "level 10" was Level_00005 all over again. The game plays one
   board per name; the editor still has all 633.                              */
const CAMPAIGN = LEVELS.map((b, i) => i + 1).filter((_, i) => LEVELS[i].variant === 0);
let CUR = 1;                       // the level number the player sees

/* ---- what the game has not shown the player yet ------------------------
   Marble Sort's results card ends on a bar counting down to the next piece the
   player has not met, and that bar is the reason the card is worth reading on a
   level nobody found hard. Ported whole; only the list of things being counted
   down to is this game's.

   Seat Match introduces four: two boosters, and two seats. The seats are read
   off the boards rather than written down, because the ladder moves - it has
   already been renumbered once - and a hand-written "level 7 -> grey seat" table
   is a second copy of it that goes stale silently. The boosters cannot be found
   that way: a booster is a button and leaves no mark on a board, so those come
   from the same RemoteConfig gate that actually hands them over, which is what
   stops the bar promising one on a different level from the one it arrives on. */
const FEATURES = [
  { id: "grey", label: "FIXED SEAT",
    from: () => firstBoard(b => b.seats.some(s => s[3] === 0)) },
  { id: "jump", label: "JUMP BOOSTER", from: () => unlockedAt("booster_jump") },
  { id: "area", label: "ADD LINE", from: () => unlockedAt("booster_area") },
  { id: "twin", label: "DOUBLE SEAT",
    from: () => firstBoard(b => b.seats.some(s => s[2] > 1)) },
  /* ⚠ Read off the board like the others. The padlock arrives on its own level
     rather than with a booster, and reading it off the data means the card
     follows the seat if the ladder ever moves again - which it has, twice. */
  { id: "lock", label: "LOCKED SEAT",
    from: () => firstBoard(b => Object.values(b.mods || {}).some(m => m.isLocked)) },
  { id: "time", label: "TIME BOOSTER", from: () => unlockedAt("booster_time") },
];

const boardOf = n => LEVELS[CAMPAIGN[n - 1] - 1];

/* ---- the hard levels ---------------------------------------------------
   The APK carries an int per board called `difficultLevel`, 0 to 2, and this is
   that value rather than a judgement of our own: 118 of the 600 campaign levels
   are marked, 59 of each grade, and the spacing says it was laid out on purpose
   - from 25 on, every level ending in 5 is a 1 and every level ending in 9 is a
   2, with 9, 15 and 19 set early to get the run going.

   ⚠ Read off the board, never listed here. The campaign numbering has already
   moved once, when the 33 duplicate arrangements came out of it, and a table of
   level numbers written in this file is a second copy of the data that goes
   stale without anything failing. */
const DIFFS = {
  /* ⚠ The chip says SUPER, not SUPER HARD. The topbar is a three-column grid and
     the left group holds the gear, the level pill and this; at the full wording
     the group grew past the middle column and pushed the clock off centre on a
     phone. The card that opens the level carries the whole name. */
  // ⚠ bonus 0 while the clock is flat. It used to hand a hard board +15s and a
  // super +45s on top of its own time, which was a compensation for a clock
  // fitted per board. With build.py writing 240s for every graded level, the
  // bonus only means the HUD does not show the number that was asked for -
  // 4:15 and 4:45 instead of 4:00. Put 15 and 45 back the day the clock stops
  // being flat.
  1: { cls: "hard",  tile: "HARD",  chip: "Hard",  warn: "HARD LEVEL",       bonus: 0 },
  2: { cls: "shard", tile: "SUPER", chip: "Super", warn: "SUPER HARD LEVEL", bonus: 0 },
};
const diffOf = n => { const b = boardOf(n); return b ? DIFFS[b.diff] || null : null; };

/** The first campaign level whose board answers `test`, or Infinity. */
function firstBoard(test) {
  for (let n = 1; n <= CAMPAIGN.length; n++) if (test(boardOf(n))) return n;
  return Infinity;
}

/* Worked out once. Sorted by the level each arrives on rather than left in
   written order, so moving a gate in RemoteConfig cannot put the ladder out of
   sequence without anyone noticing. */
let featAt = null;
function featureLevels() {
  if (!featAt) {
    featAt = FEATURES.map(f => ({ id: f.id, label: f.label, at: f.from() }))
      .filter(f => isFinite(f.at)).sort((a, b) => a.at - b.at);
  }
  return featAt;
}

/** How close the player is to the next thing they have not met, having just
    cleared `cleared`. Null once there is nothing left to count down to - the bar
    then simply does not appear, which is better than a full one that never
    moves again. */
function featureProgress(cleared) {
  let from = 1;
  for (const f of featureLevels()) {
    if (f.at > cleared) {
      // `cleared + 1` on top, not `cleared`: the bar has to read full on the
      // card that hands the player the level carrying the piece. The other form
      // tops out one level short, which reads as the reward receding.
      const span = Math.max(1, f.at - from);
      return { id: f.id, label: f.label, at: f.at,
               pct: Math.min(1, (cleared + 1 - from) / span) };
    }
    from = f.at;
  }
  return null;
}

function startLevel(n) {
  if (hearts() <= 0) {
    /* ⚠ The card that asked for this is still up, and show() does not touch it.
       Without this, TRY AGAIN on the loss that spent the last life left OUT OF
       TIME standing over the home screen with no button on it that worked, and
       the toast saying why underneath it. */
    hideCard();
    show("home");
    say("Out of lives - one comes back every " + Math.round(CF.heartSecs / 60) + " minutes.");
    return;
  }
  JUMP = false;
  closeSettings();
  CUR = Math.max(1, Math.min(CAMPAIGN.length, n));
  openBoard();
  /* ⚠ After openBoard(), so the board being fingerprinted is the one that has
     actually loaded, and before the warning card, so the clock covers the whole
     time the level was on screen.

     Fires again on a retry, which is deliberate: a retry is a second game of
     the same level and the data should say so rather than folding two attempts
     into one. gaLevelStart also brings gtag.js up - the first level is the
     earliest it may load, see ANALYTICS.md §7. */
  const tb = boardOf(CUR);
  teleStart(CUR, tb);
  gaLevelStart(CUR, tb ? tb.diff | 0 : 0);
  // The warning first, then anything new on the board. Chained rather than run
  // side by side: both stop the clock and hold the queue, and two overlays that
  // each let go on their own way out leave the board running under the second.
  const after = () => {
    const owed = introDue(CUR);
    if (owed) showIntro(owed);
    else winIfAsked();
  };
  const d = diffOf(CUR);
  if (d) showWarning(d, after);
  else after();
}

/* ---- the hard-level warning -------------------------------------------
   Raised on the way in, EVERY time rather than once. It is a warning, not a
   lesson: the moment it is most worth reading is the retry after the board has
   just beaten you. The chip on the HUD brings it back mid-board.

   Its own overlay rather than a step bolted onto INTRO_RUNS - that machinery is
   keyed to a feature, records the feature as seen and hands over a free go, and
   none of it belongs to something that has to come back every time. */
let warnGo = null;

const WARN_MS = 1500;           // ⚠ matches the `stamp` keyframes in the head, both of them
let warnTimer = 0;

function showWarning(d, then) {
  if (!S || S.phase !== "play") return then && then();
  warnGo = then || null;
  const w = $("warn");
  $("warn-text").textContent = d.warn;
  // ⚠ Off, reflow, on. Re-adding a class the element already carries does not
  // restart a CSS animation, so tapping the chip twice would show nothing the
  // second time.
  w.className = "";
  void w.offsetWidth;
  w.className = "on " + d.cls;
  setPaused(true);
  HOLD = true;                   // nothing moves, and the beat costs no clock
  clearTimeout(warnTimer);
  warnTimer = setTimeout(closeWarning, WARN_MS);
  onHud();
}

/** Hidden with its follow-on dropped: for a board being left, not one starting.
    Anything queued behind it belonged to the board that is going. */
function killWarning() {
  clearTimeout(warnTimer);
  warnGo = null;
  $("warn").className = "";
}

function closeWarning() {
  if (!$("warn").classList.contains("on")) return;
  clearTimeout(warnTimer);
  $("warn").className = "";
  const go = warnGo; warnGo = null;
  if (go) go();
  // ⚠ Only when nothing took the hold on. showIntro() stops the clock again for
  // its own run, and letting go here would start the queue walking under it.
  if (!INTRO) { HOLD = false; setPaused(false); autoBoard(); }
  onHud();
}

/** ?win=1: hand the open board a win without solving it, so the celebration and
    the result card can be read on any of the 600 levels.

    The clock is left near full on purpose. Stars come off the time remaining, so
    a board handed a win on a stopped clock would show the one-star card - and
    the thing this is used to look at is the three-star one.

    Never under an intro card. On the four levels that introduce a piece the win
    waits for the run to be read, so `introGo` calls this when the last step is
    done. Calling it from `endIntro` instead would look tidier and be wrong: that
    also runs from the `clearIntro()` at the top of `openBoard`, where `S` is
    still the board being left. */
function winIfAsked() {
  if (!WIN_ASKED || !S || S.phase !== "play") return;
  S.seated = S.total;
  S.queue.length = 0;
  S.left = Math.max(S.left, S.time * 0.9);
  finish(true);
}

/** The board itself, once there is nothing left to explain. */
function openBoard() {
  clearIntro();                  // a half-run walkthrough must not outlive its board
  hideCard();
  show("play");
  // the opening beat is there to teach the boarding, so it stops with the lesson
  // Only board 1. The beat is there so a first-time player watches somebody walk
  // on and hop into a seat instead of opening the level to find them sitting -
  // that is a lesson, and one board is where it lands. On board 2 it is two
  // seconds of a still picture shown to a player who has just seen it.
  OPEN_MS = CUR <= 1 ? 1000 : 0;
  /* Set before load(), not in showIntro(): with no opening beat, load() starts
     the queue on the frame the board appears, which is before the walkthrough
     that is meant to hold them has been put up. */
  killWarning();                 // a warning belongs to the board it was raised on
  HOLD = !!introDue(CUR) || !!diffOf(CUR);
  applyTheme(CUR);                 // before load(), so the first frame is right
  load(CAMPAIGN[CUR - 1]);
  RUNNING = false;                 // ⚠ after load(): it is the new board's clock
  /* The seconds the marked boards carry on top of what the APK gave them.

     ⚠ Added to the budget the stars are scored against as well as to the clock.
     `starsFor` reads `left / time`, so putting it only on the clock would hand
     the player more time to finish and, in the same breath, a stricter bar for
     three stars - the gift taken back by the arithmetic. */
  const grade = diffOf(CUR);
  if (grade && grade.bonus) { S.time += grade.bonus; S.left = S.time; }
  onHud();
}

/* ---- when the clock starts ---------------------------------------------
   Not on the frame the board appears. It starts on the first thing that really
   happens: a passenger stepping off the stop, or - on a board where nobody can
   move yet, because the doorway is blocked - the player's first seat. Reading
   the board before anything is committed costs nothing, which is what the
   opening beat was already trying to buy on levels 1 and 2.

   ⚠ A latch, not a test run each frame. `S.anim` empties between one walker and
   the next, and both it and `S.moves` are cleared by load(), so a condition
   evaluated live would stop the clock again in every gap. */
let RUNNING = false;

let sayUntil = 0;
const toastEl = () => document.getElementById("hint");
let sayAnyway = false;
onSay = msg => {
  // A walkthrough is already saying its piece in the bubble, and the toast for
  // the same tap lands under it saying it again. What does get through is a
  // refusal - a step waiting on the player has to be able to tell them why
  // what they just did did not count.
  if (INTRO && !sayAnyway) return;
  const el = toastEl();
  el.textContent = msg; el.classList.add("on");
  sayUntil = performance.now() + 2600;
};

/** A message that gets through a walkthrough, for the few that have to. */
const nudge = m => { sayAnyway = true; say(m); sayAnyway = false; };

const $ = id => document.getElementById(id);
const setAll = (ids, text) => { for (const i of ids) { const e = $(i); if (e) e.textContent = text; } };

onHud = function () {
  if (!S) return;
  setAll(["g-level"], CUR);
  // the pill is left alone - the chip beside it is what carries the grade
  const d = diffOf(CUR);
  const chip = $("g-grade");
  chip.hidden = !d;
  if (d) { chip.textContent = d.chip; chip.className = "grade " + d.cls; }
  setAll(["g-clock"], fmt(S.left));
  setAll(["g-coins", "h-coins"], save.coins);
  setAll(["h-stars"], totalStars());
  boosterUi();
  $("g-clock").classList.toggle("warn", S.left < S.time * .25);
  // the standing hint is gone with the bottom bar; only real messages show now
  if (sayUntil && performance.now() > sayUntil) {
    sayUntil = 0; toastEl().classList.remove("on");
  }
  tutorCheck();
};

/* ---- boosters ----------------------------------------------------------
   Time is bought per use and is unlimited; Jump is bought in charges and the
   shipped game caps it at ten. Both appear only once the level they unlock at
   has been reached. */
/** A booster that has not unlocked yet stays on the row, greyed, showing the
    level it arrives at. It used to be hidden outright, which changed the shape
    of the row from one level to the next and never said that more was coming.
    The unlock levels are RemoteConfig's, out of the tutorial group. */
function lockChip(el, tagId, feat) {
  const open = has(feat);
  el.classList.toggle("locked", !open);
  if (!open) {
    const n = unlockedAt(feat);
    $(tagId).textContent = n === Infinity ? "SOON" : "LV " + n;
    $(tagId).classList.remove("own");
  }
  return open;
}

/** The chip across the bottom of a booster says one of two things, and they are
    not the same kind of thing: what it COSTS, or how many goes are already in
    hand. Only the first is money, so only the first carries the coin - beside a
    count the coin read as a price of one, which is why the count used to need
    an "x" after it to be told apart at all. Without the coin it does not: a
    bare number on a green chip is a number of goes. */
function costChip(id, own, price) {
  const el = $(id);
  el.textContent = own == null ? price : own;
  el.classList.toggle("own", own != null);
}

function boosterUi() {
  const t = $("b-time"), j = $("b-jump"), a = $("b-area");
  const tOpen = lockChip(t, "b-time-cost", "booster_time");
  const jOpen = lockChip(j, "b-jump-cost", "booster_jump");
  const aOpen = lockChip(a, "b-area-cost", "booster_area");
  if (tOpen) costChip("b-time-cost", save.freeTime > 0 ? "FREE" : null, CF.boosterTime.price);
  if (jOpen) costChip("b-jump-cost", save.jumps > 0 ? save.jumps : null, CF.boosterJump.price);
  // The chip is hidden once the lane is out - see .boost.spent in the head. A
  // button that quotes a price it will refuse to take is a lie, and a word in
  // its place is just a quieter one; the dimmed tile says it without either.
  const spent = !!(S && S.lines);
  a.classList.toggle("spent", aOpen && spent);
  if (aOpen) costChip("b-area-cost", save.lines > 0 ? save.lines : null, CF.boosterArea.price);
  t.classList.toggle("broke", tOpen && !save.freeTime && save.coins < CF.boosterTime.price);
  j.classList.toggle("broke", jOpen && save.jumps === 0 && save.coins < CF.boosterJump.price);
  a.classList.toggle("broke", aOpen && !spent
    && save.lines === 0 && save.coins < CF.boosterArea.price);
  j.classList.toggle("armed", JUMP);
}

/** A locked booster is still worth pressing: it is the only place that says when
    it opens. */
function lockedSay(feat, what) {
  const n = unlockedAt(feat);
  say(n === Infinity ? what + " is not in this build yet."
                     : what + " unlocks at level " + n + ".");
}

$("b-time").onclick = () => {
  if (introWaitingOnBoard()) return;
  if (!S || S.phase !== "play") return;
  if (!has("booster_time")) return lockedSay("booster_time", "Extra time");
  const freeT = save.freeTime > 0;
  if (!freeT && save.coins < CF.boosterTime.price) return say("Not enough gold for more time.");
  if (freeT) save.freeTime--; else save.coins -= CF.boosterTime.price;
  // A free go and a bought one are told apart: the free ones come from the
  // walkthrough, so counting them as spending would make the tutorial look like
  // a board people had to pay to get past.
  teleBooster(freeT ? "time-free" : "time");
  SFX.buy(); buzz(14);
  S.left += CF.boosterTime.value;
  S.time = Math.max(S.time, S.left);          // keep the bar honest
  persist(); say("+" + CF.boosterTime.value + " seconds."); onHud();
  introSaw("timed");
};

/* While a walkthrough is waiting for the board to be tapped its overlay lets
   taps through, which puts the whole HUD back within reach. Nothing there may
   answer for the player: cancelling the armed jump, or restarting the level,
   would take away the one way on from a step that has no other. */
const introWaitingOnBoard = () =>
  !!(INTRO && INTRO.steps[INTRO.i] && INTRO.steps[INTRO.i].thru);

$("b-jump").onclick = () => {
  if (introWaitingOnBoard()) return;
  if (!S || S.phase !== "play") return;
  if (!has("booster_jump")) return lockedSay("booster_jump", "Jump");
  if (JUMP) { JUMP = false; say("Jump cancelled."); onHud(); draw(); return; }
  if (save.jumps === 0) {
    if (save.coins < CF.boosterJump.price) return say("Not enough gold for a jump.");
    save.coins -= CF.boosterJump.price;
    save.jumps = CF.boosterJump.uses > 0 ? CF.boosterJump.uses : 1;
    SFX.buy(); buzz(14);
    persist();
  }
  JUMP = true;
  say("Jump armed - tap the seat you want the next passenger flown into.");
  onHud(); draw();
  introSaw("armed");
};

/* Unlike the jump there is nothing to aim: the lane opens the moment it is
   bought. Charged only when the board actually takes it, so a press that lands
   while somebody is still walking, or on a board that already has its lane,
   costs nothing. */
$("b-area").onclick = () => {
  if (introWaitingOnBoard()) return;
  if (!S || S.phase !== "play") return;
  if (!has("booster_area")) return lockedSay("booster_area", "Add line");
  if (S.lines) return say("This board already has its extra lane.");
  if (S.anim.length || S.launching) return say("Wait for the queue to settle.");
  const paid = save.lines > 0;
  if (!paid && save.coins < CF.boosterArea.price) return say("Not enough gold for a lane.");
  if (!addLine(S)) return say("No room for another lane here.");
  if (paid) save.lines--;
  else {
    save.coins -= CF.boosterArea.price;
    if (CF.boosterArea.uses > 1) save.lines = CF.boosterArea.uses - 1;
  }
  teleBooster("area");
  SFX.buy(); buzz(14);
  persist(); say("A lane opens down the left."); onHud(); draw();
  autoBoard();
  introSaw("area");
};

/* One charge per seat actually moved, and the arming ends with it. */
// ⚠ The buzz stays. It is not the sound - it is the drag landing, felt rather
// than heard, and it costs nothing on a page the player has silenced.
onSeatMoved = () => { buzz(12); };

/* Armed, a tap on a seat is the booster being used: the front of the queue
   flies into it. A tap on a seat they cannot sit in is not a wasted charge -
   it says so and stays armed, because the one thing worse than a booster that
   does nothing is one that charges for it. */
onSeatPick = seat => {
  if (!JUMP) return false;
  if (!S.queue.length) { say("Nobody left in the queue."); return true; }
  if (!jumpBoard(S, seat)) {
    bump();
    nudge("Tap a ringed seat - one the passenger at the front of the queue can use.");
    return true;
  }
  JUMP = false;
  save.jumps = Math.max(0, save.jumps - 1);
  // ⚠ Where the charge is actually spent, not where the button was pressed.
  // Arming and then changing your mind is free, and a row saying otherwise
  // would put jumps on boards nobody jumped on.
  teleBooster("jump");
  persist(); buzz(16); onHud(); draw();
  introSaw("jumped");
  return true;
};

/* ---- introducing a feature ---------------------------------------------
   Four pieces need explaining, and each one gets a short walkthrough the first
   time the player reaches the level that carries it. Which level that is comes
   from the FEATURES ladder above rather than from a second list here, so moving
   a gate cannot leave the introductions pointing at the wrong board.

   A run is a list of steps, and a step points at exactly one thing:

     - a seat step rings the seats on the board and washes the room out around
       them, so the sentence lands on something the player is already looking at;
     - a booster step lifts the button through the wash, hands over a free go,
       and then waits for it to actually be pressed. A booster described in a
       paragraph is a paragraph; one you have pressed once is a button you know.
       The step after it points at what the press did - the arming, the seconds
       going onto the clock - because that is the half a paragraph cannot show.

   The clock is held for the whole run, so none of it is paid for in seconds.

   Nothing is locked out. Every waiting step grows a way past it after a few
   seconds: a board can always turn out to have no move left in it, and a
   tutorial nobody can leave is a fault rather than a lesson. */
const INTRO_RUNS = {
  /* No `twin`. A double seat explains itself the first time one is dragged - it
     is visibly two cells long and it either fits or it does not - and the
     FEATURES ladder still counts it for the progress bar either way. A run is
     written here only for a piece that cannot be worked out by looking. */
  grey: [
    { spot: "seats", btn: "GOT IT",
      text: "The ringed seat is bolted down. It does not move, whatever you drag." },
  ],
  /* Two sentences because it is two facts, and the second is the one that makes
     it a puzzle piece rather than an obstacle: the padlock is not permanent, and
     what opens it is the thing the player is doing anyway. */
  lock: [
    { spot: "seats", btn: "GOT IT",
      text: "The ringed seat is padlocked and will not budge. Seat a passenger in it and "
          + "the lock comes off - then it slides like any other." },
  ],
  /* Each booster is explained and pressed in the same step. There is no NEXT to
     click past first: a card that can be dismissed is a card that gets
     dismissed, and the player ends up owning a booster they have never used.
     The only way on is the button itself, which is why it comes with a free
     go. */
  jump: [
    { spot: "b-jump", wait: "armed",
      text: "A passenger has to walk to their seat, so a seat with no way through to it "
          + "is no use. Jump flies them straight in instead. Here is a free one - tap "
          + "the arrow button." },
    { spot: "seats", wait: "jumped", thru: true, dock: "high", slim: true,
      text: "Now tap the lit seat. There is no way to walk to it - the passenger at the "
          + "front of the queue flies straight there, over everything in between." },
  ],
  /* Two steps, like the clock. The first buys the press; the second is worth a
     card of its own because what just happened is easy to misread - the board
     did not move, it grew, and the lane that opened is the one the panel was
     already carrying. */
  area: [
    { spot: "b-area", wait: "area",
      text: "Every bus has one spare lane down its left side, folded away. This opens "
          + "it, so there is somewhere to slide a seat to. Here is a free one - tap "
          + "the green button." },
    { spot: "seats", btn: "GOT IT",
      text: "The whole board shifted right and that left column is clear floor now. "
          + "One lane per board, so spend it on the one that has you stuck." },
  ],
  time: [
    { spot: "b-time", wait: "timed",
      text: "Running out of clock is the only way to lose a board. This booster puts "
          + "seconds back on it. Here is a free one - tap the clock button." },
    { spot: "clock", btn: "GOT IT",
      text: "+{t} seconds, straight onto the clock. Tap it whenever time gets tight." },
  ],
};

/* What a step can point at, and what has to be lifted through the wash for the
   player to be able to reach it. */
const SPOTS = {
  "b-jump": ["#b-jump", "#boosters"],
  "b-time": ["#b-time", "#boosters"],
  "b-area": ["#b-area", "#boosters"],
  clock:    [".pill-time", "#play .topbar"],
};

/** The introduction owed on this level, or null. `at <= n` rather than `at === n`
    so a player who jumps ahead from the level picker still gets it. */
const INTRO_NEEDS = { jump: "booster_jump", time: "booster_time",
                      area: "booster_area" };
function introDue(n) {
  for (const f of featureLevels()) {
    if (f.at > n || !INTRO_RUNS[f.id] || save.seenBoosters.includes(f.id)) continue;
    // never walk somebody through a button they cannot press yet
    if (INTRO_NEEDS[f.id] && !has(INTRO_NEEDS[f.id])) continue;
    return f;
  }
  return null;
}

let INTRO = null;                      // { id, label, steps, i } while a run is going
let introRunning = false;

/** The free go that makes "tap it" an offer rather than a price tag. */
function giveFreeGo(id) {
  if (id === "jump") save.jumps = Math.max(save.jumps, 1);
  if (id === "time") save.freeTime = Math.max(save.freeTime, 1);
  if (id === "area") save.lines = Math.max(save.lines, 1);
  persist();
}

function showIntro(f) {
  const steps = INTRO_RUNS[f.id];
  if (!steps) return;
  save.seenBoosters.push(f.id); persist();
  giveFreeGo(f.id);
  INTRO = { id: f.id, label: f.label, steps, i: 0 };
  setPaused(true);
  HOLD = true;                   // the queue waits outside until this is over
  $("intro").classList.add("on");
  onHud();
  introGo(0);
  introFrame();
}

/** Nothing on the HUD or the boosters is lifted or ringed any more. */
function clearSpot() {
  for (const el of document.querySelectorAll(".spotlight")) el.classList.remove("spotlight");
  for (const el of document.querySelectorAll(".hint")) el.classList.remove("hint");
}

function introGo(i) {
  if (!INTRO) return;
  clearSpot();
  if (i >= INTRO.steps.length) { endIntro(); return winIfAsked(); }
  INTRO.i = i;
  INTRO.acted = false;             // nothing lit once the step has been answered
  const st = INTRO.steps[i], tip = $("intro-tip");
  /* There is no way past a step but doing it, so a step with nothing to do
     cannot be shown at all: on a board where no seat suits the front of the
     queue there would be nothing to tap and no way on. Nothing can empty the
     set once the step is up - the clock is stopped, the queue is held, and the
     only thing a tap can do there is spend the jump. */
  if (st.wait === "jumped" && !introSeats().length) return introGo(i + 1);
  $("intro-title").textContent = INTRO.label;
  $("intro-text").textContent = st.text
    .replace("{t}", CF.boosterTime.value).replace("{p}", CF.boosterJump.price);
  // one dot per step, filled up to this one, so a run reads as a run
  $("intro-dots").textContent =
    INTRO.steps.map((_, k) => (k === i ? "\u25CF" : "\u25CB")).join("");
  $("intro-ok").textContent = st.btn || "NEXT";
  tip.classList.toggle("waiting", !!st.wait);
  $("intro").classList.toggle("thru", !!st.thru);
  $("intro").classList.toggle("on-board", st.spot === "seats");
  if (st.spot && st.spot !== "seats") {
    const [sel, host] = SPOTS[st.spot];
    document.querySelector(host).classList.add("spotlight");
    document.querySelector(sel).classList.add("hint");
  }
  dockTip(st);
  draw();
}

/** Where the seats being ringed are on the screen, as a fraction of its height,
    or null when there are none. */
function seatFocusY() {
  const marked = introSeats();
  if (!marked.length || !LAY) return null;
  const r = cv.getBoundingClientRect();
  let sum = 0;
  for (const b of marked) sum += ringCentre(b)[1];
  return (r.top + (sum / marked.length) * r.height / cv.height) / innerHeight;
}

/** The bubble goes wherever the thing being pointed at is not. */
function dockTip(st) {
  const tip = $("intro-tip");
  let y = null;
  if (st.spot === "seats") y = seatFocusY();
  else if (st.spot) {
    const r = document.querySelector(SPOTS[st.spot][0]).getBoundingClientRect();
    y = (r.top + r.height / 2) / innerHeight;
  }
  const dock = st.dock ? "dock-" + st.dock
             : y == null ? "dock-mid" : y > .5 ? "dock-top" : "dock-bottom";
  tip.classList.remove("dock-high", "dock-top", "dock-mid", "dock-bottom");
  tip.classList.toggle("slim", !!st.slim);
  tip.classList.add(dock);
}

$("intro-ok").onclick = () => { if (INTRO) introGo(INTRO.i + 1); };

/** Something a step was waiting for has happened. The pause before moving on is
    the point of the step: it is where the player sees what their tap did. */
function introSaw(what) {
  if (!INTRO) return;
  const st = INTRO.steps[INTRO.i];
  if (!st || st.wait !== what) return;
  /* Stop lighting anything the moment they have done it. The jump step lights
     the seats the front of the queue can use, and the front of the queue has
     just changed - leaving it live moves the spotlight onto a different set of
     seats for as long as the beat before the next step lasts. */
  INTRO.acted = true;
  setTimeout(() => { if (INTRO && INTRO.steps[INTRO.i] === st) introGo(INTRO.i + 1); }, 620);
}

function endIntro() {
  clearSpot();
  $("intro").classList.remove("on", "thru", "on-board");
  INTRO = null;
  setPaused(false);
  HOLD = false;
  autoBoard();                   // and now they can get on
  onHud(); introFrame(); draw();
}

/** A run left half-finished - the board was won under it, or the player restarted
    - must not leave the clock paused or a button lit. */
function clearIntro() {
  if (INTRO) endIntro();
}

/** The ring is painted on the canvas, in the room's own projection, and the
    canvas only redraws when something asks it to. */
function introFrame() {
  if (introRunning) return;
  introRunning = true;
  const step = () => {
    if (!INTRO) { introRunning = false; draw(); return; }
    if (introSeats().length) draw();
    requestAnimationFrame(step);
  };
  step();
}

/** Where to put the ring: the mean of a seat's cells rather than its middle
    cell - a two-cell seat has no middle one and the ring lands over its
    right-hand half.

    ⚠ The engine already has a `seatCentre`, which answers a different
    question in different units. Declaring that name again here quietly replaced
    it, and every seat on every board went off the side of the canvas. */
function ringCentre(b) {
  const cs = cellsOf(b);
  const mc = cs.reduce((a, [c]) => a + c, 0) / cs.length;
  const mr = cs.reduce((a, [, r]) => a + r, 0) / cs.length;
  return P(cellW(mc), .02, cellZ(mr));
}

/** Which seats on this board the current step is talking about. */
function introSeats() {
  const st = INTRO && INTRO.steps[INTRO.i];
  if (!st || st.spot !== "seats" || !S || INTRO.acted) return [];
  if (INTRO.id === "grey") return S.seats.filter(b => b.colour === 0);
  /* Every padlock on the board. Unlike the jump step there is nothing to choose
     between them - the lesson is what the padlock means, and on the board it
     first appears on there is exactly one. */
  if (INTRO.id === "lock") return S.seats.filter(b => b.chain);
  // One seat, not every seat the jump could be spent on. Ringing all of them
  // taught nothing except which seats are the front colour, and on a full board
  // it covered the board. The jump is for a seat the queue cannot walk to, so
  // the one worth pointing at is exactly that: unreachable first, then whichever
  // is furthest from the door.
  if (INTRO.id === "jump" && S.queue.length) {
    const ok = S.seats.filter(b => !b.locked && accepts(b, S.queue[0]) && freeSlot(b) >= 0);
    if (!ok.length) return [];
    const reach = reachRegion(S, 0);
    const [dc, dr] = (S.doors && S.doors[0]) || [S.W - 1, S.door];
    const walk = b => (touches(S, b, reach) ? 0 : 1);          // 1 = no way in on foot
    const far = b => Math.abs(b.c - dc) + Math.abs(b.r - dr);
    ok.sort((a, b) => (walk(b) - walk(a)) || (far(b) - far(a)));
    return [ok[0]];
  }
  return [];
}

/* ---- the tutorial, on the first two boards -----------------------------
   These two levels carry the one rule that is not guessable: you never tap a
   passenger. You slide a seat, and the queue walks itself in. So on board 1 and
   2 the game works out the move the player is missing and points at it - the
   seat to pick up, and the tile to put it down on.

   Nothing is forced and nothing is locked out. The mark is a suggestion painted
   over the room; any other legal move still goes through, and the next frame
   re-aims at whatever is missing then. It disappears the moment the board no
   longer needs it, which is what makes it a tutorial and not a hint bar. */
const TEACH = new Set([1, 2]);
let TUT = null, tutKey = "";

/** The move worth teaching on this board, or null when there is nothing to say.

    Two lessons, in the order a player runs into them: a seat parked in the
    doorway so nobody can get on at all, and a door that is clear but a front of
    queue that cannot reach any seat it fits in. One seat slide fixes either,
    and that is the whole game. */
function tutorStep() {
  if (!S || S.phase !== "play" || !TEACH.has(CUR)) return null;
  if (!S.queue.length || S.anim.length || S.boarding) return null;
  const blocked = !isFree(S, S.W - 1, S.door);
  // A blocked doorway is no longer proof that nobody can move: the seat in the
  // way may be one the front of the queue can simply sit in. Teach only when
  // they genuinely have nowhere to go.
  if (pickSeat(S, S.queue[0])) return null;              // the queue is already moving

  // With the doorway blocked there is only one seat worth talking about. With
  // it clear the fault is somewhere in the floor, so weigh every seat that moves.
  const cands = blocked ? [S.seats[S.occ[idx(S, S.W - 1, S.door)]]] : S.seats;
  let best = null;
  for (const b of cands) {
    const home = [b.c, b.r];
    for (const [c, r] of placements(S, b)) {
      place(S, b, c, r);
      // ⚠ `pickSeat` on its own, with no "and the doorway is clear" in front of
      // it. That test read as a safety check and was really a veto on the
      // shortest move there is - sliding a seat onto the door cell itself, which
      // the queue boards by stepping straight into it off the stop. On level 2
      // that move IS the solution: the corner seat, down one. The coach mark
      // could not point at it, and pointed two cells away instead. `pickSeat` is
      // the question `autoBoard` asks before it launches anybody, so it is the
      // honest one to ask here too.
      const ok = !!pickSeat(S, S.queue[0]);
      const open = ok ? reachRegion(S).reduce((a, v) => a + v, 0) : 0;
      place(S, b, home[0], home[1]);                       // and straight back
      if (!ok) continue;
      // ⚠ The shortest drag, not the one that opens the most floor. Opening the
      // most floor is a good move and a bad lesson: it sends the finger the
      // length of the board when the next cell would have done, and what these
      // two levels teach is the gesture, not the tactic. Floor opened stays as
      // the tie-break, so the roomiest of the equally short moves still wins.
      const steps = Math.abs(c - home[0]) + Math.abs(r - home[1]);
      if (!best || steps < best.steps || (steps === best.steps && open > best.open))
        best = { seat: b, to: [c, r], steps, open };
    }
  }
  if (!best) return null;
  return { seat: best.seat, to: best.to,
    title: blocked ? "A seat is in the doorway" : "Open them a path",
    text: blocked
      ? "Drag and drop: press and hold the seat, drag it onto the glowing tile, then let go. The queue boards on its own - you never tap a passenger."
      : "The front of the queue cannot reach a seat it fits. Slide this one onto the glowing tile to open the way." };
}

/** Recomputed only when the board actually changes, not once a frame. */
function tutorCheck() {
  const key = (!S || !TEACH.has(CUR)) ? "" : [CUR, S.phase, S.door, S.queue.length,
    S.anim.length, S.boarding, S.seats.map(b => b.c + "," + b.r).join(";")].join("|");
  if (key === tutKey) return;
  tutKey = key;
  TUT = tutorStep();
  const box = $("coach");
  if (TUT) { $("coach-title").textContent = TUT.title; $("coach-text").textContent = TUT.text; }
  box.hidden = !TUT;
  draw();
}

/* Marble Sort's pointing hand, the same drawing: `textures.ts` bakes it as a
   path rather than reaching for an emoji, because a pictograph is a different
   shape on every device and missing outright on some Androids. Two details in
   it are load-bearing and three earlier versions there failed for want of them
   - the thumb has to protrude as its own lobe, and the three folded fingers
   have to stay separate humps with creases between. Smoothed into one curve
   what is left is a fist with one finger out, which is a different gesture.

   Drawn at 86 x 70 with the fingertip on (43, 4). The translate below puts that
   tip on the point passed in, so a call site aims the tip and never the palm. */
function drawHand(x, y, s) {
  ctx.save();
  ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-43, -4);
  ctx.lineJoin = "round"; ctx.lineCap = "round";
  ctx.lineWidth = 4; ctx.strokeStyle = "#2b3550"; ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.moveTo(36, 36);
  ctx.lineTo(36, 12);                       // index finger, left side
  ctx.quadraticCurveTo(36, 4, 43, 4);       // the tip - on the drawing's centre line
  ctx.quadraticCurveTo(50, 4, 50, 12);
  ctx.lineTo(50, 26);                       // index finger, right side
  ctx.quadraticCurveTo(50, 21, 56, 21);     // folded finger 1
  ctx.quadraticCurveTo(62, 21, 62, 28);
  ctx.quadraticCurveTo(62, 24, 68, 24);     // folded finger 2
  ctx.quadraticCurveTo(74, 24, 74, 31);
  ctx.quadraticCurveTo(74, 28, 78, 29);     // folded finger 3
  ctx.quadraticCurveTo(82, 31, 82, 37);
  ctx.lineTo(82, 48);                       // outside of the palm
  ctx.quadraticCurveTo(82, 64, 64, 64);
  ctx.lineTo(48, 64);
  ctx.quadraticCurveTo(37, 64, 34, 54);     // heel
  ctx.lineTo(31, 50);
  ctx.quadraticCurveTo(20, 50, 19, 42);     // the thumb, out clear of the palm
  ctx.quadraticCurveTo(18, 34, 28, 33);
  ctx.quadraticCurveTo(34, 33, 36, 36);
  ctx.closePath();
  ctx.fill(); ctx.stroke();
  // the creases: two between the folded fingers, one where the thumb folds over
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(62, 29); ctx.lineTo(62, 40);
  ctx.moveTo(74, 32); ctx.lineTo(74, 43);
  ctx.moveTo(33, 38); ctx.quadraticCurveTo(39, 45, 40, 54);
  ctx.stroke();
  ctx.restore();
}

/* The pointing itself, drawn in the room's own projection so it lands on the
   right tile at every window size. The engine hands the overlay the last word
   on the frame; everything here is painted over the finished room. */
onOverlay = () => {
  /* Armed, the seats the front of the queue could be flown into are ringed.
     Without it "tap a seat" is a guess, and a guess that lands on the wrong
     colour reads as the booster being broken. */
  if (JUMP && LAY && S && S.queue.length && !introSeats().length) {
    const ci = S.queue[0], t = performance.now() / 1000;
    const pulse = .5 + .5 * Math.sin(t * 3.6);
    ctx.save();
    ctx.strokeStyle = "#ffd75e"; ctx.lineWidth = Math.max(2, LAY.s * .05);
    ctx.globalAlpha = .45 + .4 * pulse;
    for (const b of S.seats) {
      if (b.locked || !accepts(b, ci) || freeSlot(b) < 0) continue;
      const A = ringCentre(b);
      const rx = SX * (.44 + .05 * pulse) * (b.len > 1 ? b.len * .72 : 1) * LAY.s;
      ctx.beginPath(); ctx.ellipse(A[0], A[1], rx, SX * .4 * LAY.s, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();
  }
  const marked = LAY ? introSeats() : [];
  if (marked.length) {
    const t = performance.now() / 1000, pulse = .5 + .5 * Math.sin(t * 3.6);
    const rad = b => [SX * (.46 + .06 * pulse) * (b.len > 1 ? b.len * .72 : 1) * LAY.s,
                      SX * .42 * LAY.s];
    ctx.save();
    // The room goes dark everywhere except around the seats being talked about.
    // One even-odd fill and not a punched-out composite: `destination-out` would
    // take the room away with the wash and show the page through the hole.
    ctx.beginPath();
    ctx.rect(0, 0, cv.width, cv.height);
    for (const b of marked) {
      const A = ringCentre(b), [rx, ry] = rad(b);
      // raised, because a seat's sprite stands well above the tile the ring is on
      const cy = A[1] - ry * .55;
      ctx.moveTo(A[0] + rx * 1.5, cy);
      ctx.ellipse(A[0], cy, rx * 1.5, ry * 2.0, 0, 0, Math.PI * 2);
    }
    ctx.fillStyle = "rgba(9,8,30,.82)";
    ctx.fill("evenodd");
    // and the ring itself, in the same gold the coach mark uses to say "this one"
    ctx.strokeStyle = "#ffd75e"; ctx.lineWidth = Math.max(3, LAY.s * .085);
    ctx.shadowColor = "rgba(255,215,94,.9)"; ctx.shadowBlur = LAY.s * .5;
    ctx.globalAlpha = .8 + .2 * pulse;
    for (const b of marked) {
      const A = ringCentre(b), [rx, ry] = rad(b);
      ctx.beginPath(); ctx.ellipse(A[0], A[1], rx, ry, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();
  }
  if (!TUT || !LAY) return;
  const b = TUT.seat, [tc, tr] = TUT.to;
  const t = performance.now() / 1000, pulse = .5 + .5 * Math.sin(t * 3.6);

  const cs = cellsOf(b), mid = cs[(cs.length / 2) | 0];
  const A = P(cellW(mid[0]), .02, cellZ(mid[1]));
  const dst = [];
  for (let k = 0; k < b.len; k++) dst.push(b.dir & 1 ? [tc, tr + k] : [tc + k, tr]);
  const dm = dst[(dst.length / 2) | 0];
  const B = P(cellW(dm[0]), .02, cellZ(dm[1]));

  ctx.save();
  // where it goes: a tile that breathes, inside a crawling dashed outline
  for (const [c, r] of dst) {
    const q = tileQuad(c, r, .022);
    ctx.globalAlpha = .16 + .18 * pulse;
    quad(q, "#ffd75e");
    ctx.globalAlpha = .9;
    ctx.strokeStyle = "#ffd75e"; ctx.lineWidth = Math.max(2, LAY.s * .05);
    ctx.setLineDash([LAY.s * .2, LAY.s * .15]); ctx.lineDashOffset = -t * LAY.s * .9;
    ctx.beginPath(); ctx.moveTo(q[0][0], q[0][1]);
    for (let i = 1; i < 4; i++) ctx.lineTo(q[i][0], q[i][1]);
    ctx.closePath(); ctx.stroke(); ctx.setLineDash([]);
  }
  // what to pick up
  ctx.globalAlpha = .95;
  ctx.strokeStyle = "#fff"; ctx.lineWidth = Math.max(2, LAY.s * .06);
  const rx = SX * (.48 + .07 * pulse) * LAY.s;
  ctx.beginPath(); ctx.ellipse(A[0], A[1], rx, rx * .42, 0, 0, Math.PI * 2); ctx.stroke();
  // the drag: a line to follow, and a fingertip that keeps walking it
  ctx.globalAlpha = .65;
  ctx.setLineDash([LAY.s * .12, LAY.s * .12]); ctx.lineDashOffset = -t * LAY.s * 1.2;
  ctx.beginPath(); ctx.moveTo(A[0], A[1]); ctx.lineTo(B[0], B[1]); ctx.stroke();
  ctx.setLineDash([]);

  const f = Math.min(1, ((t * .6) % 1) / .74);          // travel, then a beat of rest
  const fade = f < .08 ? f / .08 : f > .92 ? (1 - f) / .08 : 1;
  const bob = Math.sin(t * (2 * Math.PI / 1.24)) * LAY.s * .05;   // Marble Sort's 620ms yoyo
  ctx.globalAlpha = fade;
  drawHand(A[0] + (B[0] - A[0]) * f, A[1] + (B[1] - A[1]) * f + bob,
           SX * LAY.s * .85 / 86);
  ctx.restore();
};

/* ---- sound and haptics -------------------------------------------------
   There is no audio file anywhere in this build and there is not going to be
   one: a single-file game that has to carry a sound bank stops being a single
   file. Every cue below is a shaped oscillator instead, a couple of lines each.
   The context is built on the first cue rather than at load, because a browser
   will not let one start before the player has touched something. */
let AC = null;
function blip(freq, dur, type, peak, delay) {
  // ⚠ The host's mute wins. The in-game switch must not be able to bring audio
  // back over a page the player silenced - which is what the submission form's
  // "supports CrazyGames muting" box is a promise about.
  if (!save.sound || PLATFORM.hostMuted()) return;
  try {
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    if (AC.state === "suspended") AC.resume();
    const t = AC.currentTime + (delay || 0);
    const o = AC.createOscillator(), g = AC.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    g.gain.setValueAtTime(.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + .012);
    g.gain.exponentialRampToValueAtTime(.0001, t + dur);
    o.connect(g); g.connect(AC.destination);
    o.start(t); o.stop(t + dur + .02);
  } catch (e) { /* no output device, or a browser that refuses one */ }
}
/* ⚠ No `move`. Dragging a seat is the thing the player does most - dozens of
   times a level - and any cue on it becomes a rattle rather than feedback. It
   went from .09 to .015 and then out altogether; the drag has the seat moving
   under the finger and a short buzz, which is feedback enough.

   ⚠ `seated` is a tenth of what it was, halved once more after .018 still read
   as a chime. It is the sound of the level going right so it stays, but it fires
   once per passenger and a board seats thirty - at that rate it has to sit under
   the room rather than on top of it. .009 renders 0.0090 peak and 0.0020 RMS,
   nineteen dB under the win jingle and level with the station horn, which is the
   band a sound this frequent belongs in. */
const SEATED_PEAK = .009;

/* A body dropping onto a cushion, not a note. Two things make it that rather
   than a drum:

   ⚠ The pitch FALLS. A held tone at any frequency is a note; weight landing is
   a pitch that drops as it settles, 165Hz to 62 in an eighth of a second. The
   old cue was 560 and 840 held flat, which is a chime however quietly it is
   played - the frequency was the problem, not only the level.

   ⚠ A breath of noise under it, low-passed to a few hundred hertz. That is the
   cushion; without it the drop is a kick drum. It is a fifth of the tone's
   level - any louder and it reads as a hiss rather than as upholstery. */
function thud(peak) {
  if (!save.sound || PLATFORM.hostMuted()) return;
  try {
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    if (AC.state === "suspended") AC.resume();
    const t = AC.currentTime;
    const lp = AC.createBiquadFilter();
    lp.type = "lowpass"; lp.frequency.value = 430; lp.Q.value = .7;
    lp.connect(AC.destination);

    const o = AC.createOscillator(), g = AC.createGain();
    o.type = "sine";
    o.frequency.setValueAtTime(165, t);
    o.frequency.exponentialRampToValueAtTime(62, t + .13);
    g.gain.setValueAtTime(.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + .010);
    g.gain.exponentialRampToValueAtTime(.0001, t + .21);
    o.connect(g); g.connect(lp);
    o.start(t); o.stop(t + .23);

    const src = AC.createBufferSource(), ng = AC.createGain();
    src.buffer = ambNoiseBuf();
    src.loop = true;
    ng.gain.setValueAtTime(.0001, t);
    ng.gain.exponentialRampToValueAtTime(peak * .2, t + .008);
    ng.gain.exponentialRampToValueAtTime(.0001, t + .12);
    src.connect(ng); ng.connect(lp);
    src.start(t); src.stop(t + .14);
  } catch (e) { /* no output device, or a browser that refuses one */ }
}

const SFX = {
  seated: () => thud(SEATED_PEAK),
  buy:    () => { blip(680, .07, "square", .05); blip(1020, .10, "square", .04, .07); },
  win:    () => [523, 659, 784, 1046].forEach((f, i) => blip(f, .28, "triangle", .09, i * .11)),
  lose:   () => { blip(300, .22, "sawtooth", .06); blip(190, .34, "sawtooth", .06, .13); },
  no:     () => blip(160, .13, "square", .05),

};
/* ---- room sound ---------------------------------------------------------
   Not a soundtrack, and no longer a bed: the noises a place makes, now and
   then, with silence in between.

   ⚠ The first cut ran a continuous filtered-noise bed under the board - a
   station rumble, slowly drifting, with trains passing through it. It measured
   correctly and it was rejected on the only test that matters, which is
   listening to it: a drone under a puzzle game is a thing to switch off. What
   carried the place was never the bed. It was the horn.

   So: no bed anywhere, in any theme. If a room needs a sound, it gets an event,
   spaced far enough apart to stay welcome.

   No audio file either, for the same reason there is no sound bank - this build
   is one HTML file and a minute of music is a megabyte. A handful of
   oscillators costs nothing to ship and nothing to license, which for a game
   going to a host that requires you to own your music is not a small thing.

   ⚠ Gated on the same two switches as every cue: the in-game sound setting and
   the host's mute, and the host wins. */
const AMB_LEVEL = 1.0;
let AMB = null;                   // { theme, master } while a cue is sounding

/** A tone that belongs to the room rather than to the game.

    ⚠ Not blip(). blip connects straight to AC.destination, so anything routed
    through it bypasses the ambience master: it would not fade out when the
    player leaves the board, and would still be sounding over the home screen. */
function ambTone(freq, dur, peak, delay, type) {
  if (!AMB) return;
  const t = AC.currentTime + (delay || 0);
  const o = AC.createOscillator(), g = AC.createGain();
  o.type = type || "sine"; o.frequency.setValueAtTime(freq, t);
  g.gain.setValueAtTime(.0001, t);
  g.gain.exponentialRampToValueAtTime(peak, t + .03);
  g.gain.exponentialRampToValueAtTime(.0001, t + dur);
  o.connect(g); g.connect(AMB.master);
  o.start(t); o.stop(t + dur + .05);
}

/** Several partials under one envelope, through one filter.

    ⚠ Three notes, not one. A single oscillator is a test tone however it is
    shaped; what makes a horn sound like air forced through metal is the beating
    between partials a few cents apart. The low-pass is what puts it in the
    distance - take it off and the same chord is standing on the platform. */
function ambChord(freqs, dur, peak, delay) {
  if (!AMB) return;
  const t = AC.currentTime + (delay || 0);
  const f = AC.createBiquadFilter(), g = AC.createGain();
  f.type = "lowpass"; f.frequency.value = 1150; f.Q.value = .6;
  g.gain.setValueAtTime(.0001, t);
  // A slow attack is most of what "far away" means: close sounds start abruptly.
  g.gain.exponentialRampToValueAtTime(peak, t + .18);
  g.gain.setValueAtTime(peak, t + dur * .5);
  g.gain.exponentialRampToValueAtTime(.0001, t + dur);
  f.connect(g); g.connect(AMB.master);
  freqs.forEach((hz, i) => {
    const o = AC.createOscillator();
    o.type = "sawtooth";
    o.frequency.setValueAtTime(hz * (1 + (i - 1) * .0016), t);
    o.connect(f);
    o.start(t); o.stop(t + dur + .1);
  });
}

/** A train horn, somewhere off down the line. Long, then short - the shape a
    horn is actually blown in, and the reason two blasts read as a train where
    one reads as a note. */
/* ⚠ Set against RMS, not against peak, and that is the whole point. Two
   things had to be found the hard way here:

   ambChord() puts all three partials under ONE envelope, so what leaves it is
   about three times `peak`. At .033 the horn rendered at 0.105 - louder at the
   peak than the win jingle it lands on top of.

   ⚠ And cutting the peak was not enough. At .009 the peak was 0.029, ten dB
   under the jingle, and it still startled - because a 1.6-second chord is
   judged on the energy it carries, and its RMS was 0.0058 against the jingle's
   0.0086. Three and a half dB. The ear was right and the peak reading was
   measuring the wrong thing.

   At .003 the horn renders 0.0096 peak and 0.0020 RMS - thirteen dB of energy
   below the jingle, which is a room heard through a wall rather than an event
   of its own. Measured by rendering it offline through the same filter and
   envelope, not by listening and guessing. */
const HORN_PEAK = .003;

function ambHorn() {
  const chord = [311, 370, 466];        // a minor triad; air horns are chords
  ambChord(chord, 1.6, HORN_PEAK, 0);
  ambChord(chord, .60, HORN_PEAK * .76, 2.05);
}

/** Two seconds of pink-ish noise, made once and kept.

    ⚠ Noise is back, but only inside events. Nothing here loops under a board:
    the rejected version was a noise bed running the whole level, and the lesson
    was about the drone, not about the waveform. A crowd cannot be made any
    other way - detuned oscillators give a choir, not a stand.

    ⚠ Pink, not white. White through a band-pass is hiss with the ends cut off;
    rolling the spectrum first is what makes it read as people. */
let ambNoise = null;
function ambNoiseBuf() {
  if (ambNoise) return ambNoise;
  const n = Math.floor(AC.sampleRate * 2);
  ambNoise = AC.createBuffer(1, n, AC.sampleRate);
  const d = ambNoise.getChannelData(0);
  let b0 = 0, b1 = 0, b2 = 0;
  for (let i = 0; i < n; i++) {
    const w = Math.random() * 2 - 1;
    b0 = .99765 * b0 + w * .0990460;
    b1 = .96300 * b1 + w * .2965164;
    b2 = .57000 * b2 + w * 1.0526913;
    d[i] = (b0 + b1 + b2 + w * .1848) * .22;
  }
  return ambNoise;
}

/** A crowd, rising and falling. The filter opens as it swells: a stand getting
    louder also gets brighter, and holding the colour still is most of what
    makes a noise envelope sound like a fade on a tape rather than like people. */
function ambCheer(secs, peak, f0, f1, delay) {
  if (!AMB) return;
  const t = AC.currentTime + (delay || 0);
  const src = AC.createBufferSource(), f = AC.createBiquadFilter(), g = AC.createGain();
  src.buffer = ambNoiseBuf(); src.loop = true;         // stopped below, never left running
  f.type = "bandpass"; f.Q.value = .9;
  f.frequency.setValueAtTime(f0, t);
  f.frequency.linearRampToValueAtTime(f1, t + secs * .40);
  f.frequency.linearRampToValueAtTime(f0, t + secs);
  g.gain.setValueAtTime(.0001, t);
  g.gain.linearRampToValueAtTime(peak, t + secs * .40);
  g.gain.linearRampToValueAtTime(.0001, t + secs);
  src.connect(f); f.connect(g); g.connect(AMB.master);
  src.start(t); src.stop(t + secs + .1);
}

/** The stand finding its voice for a few seconds. */
function ambRoar() { ambCheer(2.8, .200, 620, 1500); }

/** An electric school bell: a clapper on a metal dome.

    ⚠ Inharmonic partials, and a square LFO on the gain. A harmonic stack is a
    church bell and a smooth tone is a doorbell; what says "school" is the ratio
    between the partials being nothing musical, and the hammer buzzing against
    the dome twenty times a second. */
function ambThump(hz, dur, peak, delay) {
  if (!AMB) return;
  const t = AC.currentTime + (delay || 0);
  const o = AC.createOscillator(), f = AC.createBiquadFilter(), g = AC.createGain();
  o.type = "sine";
  o.frequency.setValueAtTime(hz * 1.5, t);
  o.frequency.exponentialRampToValueAtTime(hz, t + .06);
  f.type = "lowpass"; f.frequency.value = 190;
  g.gain.setValueAtTime(.0001, t);
  g.gain.exponentialRampToValueAtTime(peak, t + .015);
  g.gain.exponentialRampToValueAtTime(.0001, t + dur);
  o.connect(f); f.connect(g); g.connect(AMB.master);
  o.start(t); o.stop(t + dur + .05);
}

/** A few bars leaking out of the hall, the way they do when a door opens: the
    bass and the crowd, and nothing of the tune - a wall passes the bottom and
    stops everything else, which is why this is thuds rather than notes. */
function ambBars() {
  const riff = [55, 55, 73.4, 55, 65.4];
  riff.forEach((hz, i) => ambThump(hz, .40, .078, i * .44));
  ambCheer(2.6, .015, 480, 1200, .2);
}

/* One cue per theme, played ONCE, on a level being cleared - never during play.

   ⚠ The version before this ran them on a timer through the whole level. Two
   things were wrong with it and only one was audible: a room that makes a noise
   every half minute is a room the player is waiting on rather than reading, and
   a sound with no cause is a sound that means nothing. Tied to the win it has a
   job - it is the room reacting, arriving a beat before the card does.

   ⚠ There is no `cinema`, and that is the design rather than a gap. A cinema's
   defining sound is that it has none, and the honest alternatives were a
   projector nobody would place or a rumble from the film next door. A theme
   missing from this table is silent - see ambCue(). */
/* ⚠ No `classroom` either. It had a hand bell, which reads as the sound that
   ENDS a lesson rather than one that celebrates finishing it - and a classroom
   is quiet for the same reason a cinema is. The bell went with it rather than
   sitting here unreachable. */
const AMBIENCE = {
  station: ambHorn,
  stadium: ambRoar,
  concert: ambBars,
};

/* ⚠ An AudioContext built before the player has touched anything starts
   SUSPENDED, and calling resume() on it then does nothing - the browser wants a
   trusted gesture, and a promise that was rejected before one arrived is not
   retried by anybody. Nothing above notices: AMB is set, the timers run, the
   oscillators start and stop on schedule, and not one sample reaches the
   speaker. From the console it looks like it is working.

   ⚠ It bites the deep link specifically - /?level=6 reaches a board with no
   click anywhere behind it - which is exactly how this game is handed round for
   testing. The route through the home screen has the PLAY button as its gesture
   and never showed the fault.

   So: try again on every gesture, forever, not once. `once: true` would spend
   the listener on whichever gesture happened to come first, which may be one
   that arrived before there was a context to resume. */
function ambWake() {
  if (AC && AC.state === "suspended") { try { AC.resume(); } catch (e) {} }
}
for (const ev of ["pointerdown", "touchstart", "keydown"])
  addEventListener(ev, ambWake, { capture: true, passive: true });

function ambStop() {
  if (!AMB) return;
  const dead = AMB;
  AMB = null;
  try {
    /* Faded, not cut. The cue is a second or two long and the player can press
       NEXT LEVEL in the middle of one - dropping the gain to zero on that frame
       is a click. The oscillators stop themselves at the time they were
       scheduled to. */
    dead.master.gain.cancelScheduledValues(AC.currentTime);
    dead.master.gain.setValueAtTime(dead.master.gain.value, AC.currentTime);
    dead.master.gain.linearRampToValueAtTime(.0001, AC.currentTime + .35);
    setTimeout(() => { try { dead.master.disconnect(); } catch (e) {} }, 700);
  } catch (e) { /* context already gone */ }
}

/** The room's own reaction to a board being cleared. One shot, then silence.

    ⚠ Called AFTER setPaused(true) in onFinish, not before. setPaused routes
    through ambSync(), which stops anything sounding - fired first, the cue would
    be started and then cut down within the same function. */
function ambCue() {
  const play = AMBIENCE[THEME];
  if (!play) return;                           // a theme with no cue: cinema
  if (!save.sound || PLATFORM.hostMuted()) return;
  ambStop();                                   // never two cues over each other
  try {
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    if (AC.state === "suspended") AC.resume();
    const master = AC.createGain();
    master.gain.setValueAtTime(AMB_LEVEL, AC.currentTime);
    master.connect(AC.destination);
    AMB = { theme: THEME, master };
    play();
  } catch (e) { AMB = null; /* no output device, or a browser that refuses one */ }
}

/** Anything that gates audio moving - the switch, the host's mute, leaving the
    board - can only ever SILENCE now. Nothing starts a cue but a win. */
function ambSync() {
  if (PAUSED || !save.sound || PLATFORM.hostMuted()) ambStop();
}

/* ⚠ A tab in the background must go quiet. Unlike an rAF loop, a running
   AudioContext is not paused by the browser - a phone with its screen off
   would keep the station rumbling. */
document.addEventListener("visibilitychange", () => {
  if (document.hidden) ambStop();
});

/* Android buzzes. iOS Safari has no Vibration API at all, so there the switch is
   simply inert - which is better than hiding it and guessing wrong about a
   browser we cannot test from here. */
function buzz(ms) {
  if (!save.vibe || !navigator.vibrate) return;
  try { navigator.vibrate(ms); } catch (e) {}
}

/* a passenger reaching a seat is the one event in the game the player is waiting
   for, so it is the one that gets a sound of its own */
onSeated = () => SFX.seated();

/* ---- settings ----------------------------------------------------------
   Built on the result card's own panel, so the two overlays read as one family
   rather than as two dialogs from different games. Only switches that do
   something are here: there is no music track in the build, so there is no
   music switch above them pretending there is. */
const setEl = $("settings");
function syncToggles() {
  $("set-sound").setAttribute("aria-checked", String(!!save.sound));
  $("set-vibe").setAttribute("aria-checked", String(!!save.vibe));
}

/** The clock, while the card is up.

    ⚠ It used to keep running, which is the whole reason this card is a pause and
    not a settings sheet: the player opens it, reads two rows, turns the sound
    off, and comes back to a level they have lost. Marble Sort sets `paused` for
    exactly this and clears it on the way out.

    Only the clock stops. A passenger already walking to a seat keeps walking -
    those are the engine's own timers and stopping them mid-stride would need the
    walk to be resumable, which is a much bigger change than the fault warrants. */
/* ⚠ Starts true: nothing is in play until a board is actually open. Starting
   false made the first show("home") emit a gameplayStop the host had never been
   told to expect - a stop with no start - while the first show("play") emitted
   nothing at all, because false was already the value. The pair only comes out
   in order if the game admits it is not playing yet. */
let PAUSED = true;

/** ⚠ The single place the host is told whether play is live. Marble Sort's note
    is that emitting from each call site guarantees missing one, and the one you
    miss is where an ad lands in the middle of a turn. Everything that pauses
    goes through here. */
function setPaused(v) {
  if (v === PAUSED) return;
  PAUSED = v;
  if (v) PLATFORM.gameplayStop(); else PLATFORM.gameplayStart();
  /* ⚠ Here, and only here. This function is already the one choke point for
     leaving and re-entering a board - the comment on show() explains what it
     cost to learn that - so the room tone hangs off it rather than off each
     exit. A bed started in startLevel() and stopped in three other places is a
     bed still playing over the home screen the first time one is missed. */
  ambSync();
}
function openSettings() {
  if (!S || S.phase !== "play" || cardEl.classList.contains("on")) return;
  setPaused(true);
  syncToggles();
  setEl.classList.add("on");
}
function closeSettings() { setPaused(false); setEl.classList.remove("on"); }
/** Shut it on the way somewhere else: no unpause, because nothing is resuming. */
function dropSettings() { setEl.classList.remove("on"); }

/** Turning a switch on demonstrates itself - a sound cue for sound, a buzz for
    vibration - which is the only way a player can tell the switch did anything
    on a device whose ringer is down or whose motor is missing. */
function toggleSetting(key) {
  save[key] = !save[key];
  persist(); syncToggles();
  if (key === "sound" && save.sound) SFX.seated();
  if (key === "vibe" && save.vibe) buzz(18);
  if (key === "sound") ambSync();      // switching sound off silences a cue mid-tail
}
$("set-sound").onclick = () => toggleSetting("sound");
$("set-vibe").onclick = () => toggleSetting("vibe");
$("set-close").onclick = closeSettings;
$("set-dim").onclick = closeSettings;
$("set-retry").onclick = () => { closeSettings(); startLevel(CUR); };
$("set-home").onclick = () => { dropSettings(); hideCard(); show("home"); };
/* The way back to the board, and the reason the card needs one: with only a
   close disc in the corner, the one obvious thing to press was HOME, so
   opening the settings meant leaving the level. */
$("set-resume").onclick = closeSettings;
/* ⚠ Settings stays open behind it, so closing the policy lands back where it
   was opened from rather than dropping the player onto a running board. The
   panel is a div in this same page, never a link out - see CRAZYGAMES.md. */
$("set-privacy").onclick = () => $("privacy").classList.add("on");
$("pv-close").onclick = () => $("privacy").classList.remove("on");
$("pv-dim").onclick = () => $("privacy").classList.remove("on");

/* ---- the result card ---------------------------------------------------
   Marble Sort's `GameScene.overlay`, ported: the sunburst, the three-plate
   panel, the stars that land one after another with a flash and a scatter of
   twinkles, the bar counting down to the next new thing, the purse, and two
   buttons. Written in that game's design units - see `fitDesign` above.     */
const cardEl = document.getElementById("card");
/* Stamped, because the win now holds the card back for a beat and the level can
   be left inside it - by a retry, or by anything that starts a level. Without
   this the card would arrive over whatever came next. */
let cardGen = 0;
function hideCard() {
  cardGen++; cardEl.classList.remove("on", "cheer");
  // Everything that tears the card down - a retry, HOME, the next level - is
  // also leaving the board the offer was about, so the offer goes with it.
  $("revive").classList.remove("on"); REVIVE_THEN = null;
}
onNewLevel = hideCard;

/* The star is Marble Sort's: a flat gold ten-point path with one darker outline,
   the same construction as everything else it draws - no gradients past a single
   highlight, so it sits beside the pieces rather than looking imported. */
const STAR_PATH = "M26 2L32.35 17.26L48.82 18.58L36.27 29.34L40.11 45.42L26 36.8"
  + "L11.89 45.42L15.73 29.34L3.18 18.58L19.65 17.26Z";
const star = on => '<svg viewBox="0 0 52 52"><path d="' + STAR_PATH + '" fill="'
  + (on ? "#ffc21e" : "#7c88a6") + '" stroke="' + (on ? "#c67a06" : "#5a6480")
  + '" stroke-width="3" stroke-linejoin="round"/></svg>';
const STAR_ON = star(true), STAR_OFF = star(false);

/** Paper falling past the card. */
function confetti(on) {
  const box = $("c-confetti");
  box.innerHTML = "";
  if (!on) return;
  const cols = ["#e83e48", "#fa822a", "#fac42e", "#4ac65c", "#37c6d8", "#3f7ce8", "#a05de0", "#ff7ab8"];
  for (let i = 0; i < 26; i++) {
    const p = document.createElement("i");
    p.style.left = (40 + Math.random() * 460) + "px";
    p.style.background = cols[(Math.random() * cols.length) | 0];
    p.style.animationDuration = (2.6 + Math.random() * 2.2) + "s";
    p.style.animationDelay = (-Math.random() * 3) + "s";
    box.appendChild(p);
  }
}

/** The beat between winning and the card: paper, and a few bursts over the
    board. Losing has nothing to celebrate and still gets its card at once. */
const CHEER_MS = 1500;
function cheer() {
  finale(CHEER_MS);              // the room plays its own ending under the paper
  confetti(true);
  cardEl.classList.add("cheer");
  const box = $("c-confetti");
  for (let i = 0; i < 4; i++)                 // spread over the beat, not all at once
    setTimeout(() => cardEl.classList.contains("cheer")
      && starBurst(box, 90 + Math.random() * 360, 250 + Math.random() * 430), 140 + i * 250);
}

/** Punch of light where a star lands, plus a scatter of twinkles. */
function starBurst(into, x, y) {
  const fl = document.createElement("i");
  fl.className = "flash"; fl.style.left = x + "px"; fl.style.top = y + "px";
  into.appendChild(fl);
  setTimeout(() => fl.remove(), 440);
  for (let k = 0; k < 6; k++) {
    const a = Math.random() * Math.PI * 2, d = 30 + Math.random() * 40;
    const sp = document.createElement("i");
    sp.className = "spark";
    sp.style.left = x + "px"; sp.style.top = y + "px";
    sp.style.setProperty("--sx", Math.cos(a) * d + "px");
    sp.style.setProperty("--sy", Math.sin(a) * d + "px");
    into.appendChild(sp);
    setTimeout(() => sp.remove(), 520);
  }
}

/* The prize on the end of the bar. The two seats are drawn from the atlas the
   board draws them from - a milestone illustrated with a piece the player will
   not recognise when it arrives is worse than no picture - and the two boosters
   borrow the glyph off their own button, for the same reason. */
function featIcon(id) {
  if (id === "jump" || id === "time") {
    const svg = $(id === "jump" ? "b-jump" : "b-time").querySelector("svg").cloneNode(true);
    svg.removeAttribute("class");
    return svg;
  }
  const f = META.frames[id === "twin" ? "s2_0_yellow" : "s1_0_grey"];
  const c = document.createElement("canvas");
  if (!f || !ready) return c;
  c.width = f[2]; c.height = f[3];
  c.getContext("2d").drawImage(atlas, f[0], f[1], f[2], f[3], 0, 0, f[2], f[3]);
  return c;
}

/** "You are this far from something new."

    It animates from where the player was, not from zero and not straight to the
    answer: a bar drawn at 63% is a fact, a bar that visibly moves from 56% to
    63% is the reward for the level they just played, which is the only reason it
    is on the card at all. When the last level crossed a milestone the previous
    value belongs to a different piece, so it starts empty rather than jumping
    backwards. */
function featureBar(feat, cleared) {
  const box = $("c-feat");
  box.hidden = !feat;
  if (!feat) return;
  const before = featureProgress(cleared - 1);
  const from = before && before.id === feat.id ? before.pct : 0;
  const fill = $("c-feat-fill"), lab = $("c-feat-lab"), badge = $("c-feat-badge");
  const TRACK = 294;                       // the 300 track, less its 3px inset each side
  const paint = p => {
    fill.classList.toggle("empty", p <= .001);
    fill.style.width = Math.max(0, TRACK * p) + "px";
  };
  badge.classList.remove("hit");
  badge.innerHTML = "";
  badge.appendChild(featIcon(feat.id));
  fill.style.transition = "none"; paint(from);
  void fill.offsetWidth;                   // land the start before the move is armed
  fill.style.transition = "";
  const say = p => lab.textContent = Math.round(p * 100) + "% TO NEXT FEATURE";
  say(from);

  // ⚠ Generation-stamped, because the card can be built twice in a breath - the
  // board finishes itself as the level loads, and a second finish lands on top -
  // and two of these running at once take turns writing the same label. The
  // loser used to be the one that got the last word, so a full bar stopped at
  // "100% TO NEXT FEATURE" and never said what it had unlocked.
  const gen = featureBar.gen = (featureBar.gen || 0) + 1;
  clearTimeout(featureBar.t);
  featureBar.t = setTimeout(() => {
    if (featureBar.gen !== gen) return;
    paint(feat.pct);
    const t0 = performance.now();
    (function step(now) {
      if (featureBar.gen !== gen) return;
      const t = Math.min(1, (now - t0) / 900);
      say(from + (feat.pct - from) * (1 - Math.pow(1 - t, 3)));
      if (t < 1) return requestAnimationFrame(step);
      if (feat.pct < 1) return;
      // Full. Say what it unlocked rather than leaving the player to read the icon.
      lab.textContent = feat.label + " UNLOCKED!";
      badge.classList.add("hit");
    })(t0);
  }, 700);
}

/* ---- revive ------------------------------------------------------------
   Running out of time is the only way to lose, and starting a board over is a
   long way back from a board that was nearly done. So the losing card sells a
   minute. It is not a restart: the seats stay where the player put them, the
   queue keeps its place, and the clock picks up from where it stopped.

   ⚠ What the loss already took is handed back. onFinish() spends a life and
   breaks the streak the moment the clock hits zero, because that is the only
   place that knows the board ended - but a revived board never really ended.
   Taking it and giving it back, rather than waiting to see whether the player
   revives, is deliberate: a player who closes the tab on the losing card has
   still lost, which is not true of a penalty that is only written on TRY AGAIN. */
let LOST = null;                     // what the last loss cost, until it is spent

/* The results card, held back until the offer has been answered. The X is the
   only way to it, which is the whole point of the order: a player who has just
   run out of time is asked whether they want to keep this board before being
   shown the two ways of leaving it. */
let REVIVE_THEN = null;

/** Put the offer up, priced, ahead of `then`. */
function offerRevive(then) {
  REVIVE_THEN = then;
  const go = $("rv-go"), secs = CF.keepPlaying.secs;
  $("rv-plus").textContent = "+" + secs;
  $("rv-secs").textContent = secs;
  go.querySelector(".cost").textContent = CF.keepPlaying.price;
  go.classList.toggle("broke", save.coins < CF.keepPlaying.price);
  go.classList.remove("shake");
  $("revive").classList.add("on");
}

/** Turned down: on to the card that was waiting behind it. */
function declineRevive() {
  $("revive").classList.remove("on");
  const then = REVIVE_THEN; REVIVE_THEN = null;
  if (then) then();
}

function revive() {
  const go = $("rv-go"), price = CF.keepPlaying.price;
  if (save.coins < price) {
    // The toast lives under this, so the button has to carry the refusal.
    go.classList.remove("shake"); void go.offsetWidth; go.classList.add("shake");
    SFX.no(); buzz(50);
    return;
  }
  REVIVE_THEN = null;                  // the card behind this is not wanted now
  $("revive").classList.remove("on");
  save.coins -= price;
  if (LOST) { save.streak = LOST.streak; save.hearts = LOST.hearts; save.heartAt = LOST.heartAt; }
  LOST = null;
  persist();
  hideCard();
  S.phase = "play";
  S.left += CF.keepPlaying.secs;
  S.time = Math.max(S.time, S.left);   // the star bar reads left/time - keep it honest
  RUNNING = true;                      // it was running a moment ago; do not wait to be asked again
  /* ⚠ onFinish has already posted the losing row by the time this runs, so the
     run's clock has to be re-armed or the bought game would report nothing at
     all. Two rows is the honest account: a loss, then a second game carrying
     `revive` in `used`. See telemetry.js. */
  teleResume("revive");
  setPaused(false);
  SFX.buy();
  onHud(); boosterUi(); draw();      // onHud repaints the purse; 500 gone can price a booster out
}

/** The card itself. `stars` at 0 is the losing face; `feat` is the bar, and
    everything below the stars slides down by one number to make room for it. */
function overlay(title, stars, coins, streak, sum, feat, cleared) {
  const design = $("c-card");
  design.style.setProperty("--dy", (feat ? 66 : 0) + "px");
  design.style.setProperty("--dz", (stars && streak ? 34 : 0) + "px");
  design.classList.toggle("lose", !stars);
  $("c-title").textContent = title;
  $("c-rays").hidden = !stars;
  $("c-coins").hidden = !stars;
  $("c-coins").lastElementChild.textContent = coins;
  $("c-streak").hidden = !stars || !streak;
  $("c-streak").textContent = streak;
  $("c-sum").hidden = !!stars;
  $("c-sum").innerHTML = sum;
  /* ⚠ From HOME_AFTER on, a win ends at the home screen rather than on the next
     board. The first levels run one into the next because that is the stretch
     where stopping is what loses a player; past it, going through Home is what
     puts the progress board, the purse and the next hard level in front of them
     between attempts. Only one button then - NEXT LEVEL and HOME both leading
     home is the same button twice. */
  const goHome = !!stars && cleared >= HOME_AFTER;
  $("c-next").textContent = !stars ? "TRY AGAIN" : goHome ? "CONTINUE" : "NEXT LEVEL";
  $("c-home").hidden = goHome;

  const box = $("c-stars");
  box.innerHTML = "";
  for (let i = 0; stars && i < 3; i++) {
    const big = i === 1;
    const x = 270 + (i - 1) * 84, y = big ? 486 : 500;
    const s = document.createElement("div");
    s.className = "star" + (big ? " big" : "");
    s.style.left = x + "px";
    s.innerHTML = i < stars ? STAR_ON : STAR_OFF;
    box.appendChild(s);
    // staggered, so three stars land one after another rather than all at once
    setTimeout(() => {
      s.classList.add("pop");
      if (i < stars) setTimeout(() => starBurst(box, x, y), 300);
    }, 200 + i * 180);
  }
  featureBar(stars ? feat : null, cleared);
  // The paper has been falling since the win. Building it again here would send
  // every piece back to the top of the screen on the frame the card arrives.
  if (!cardEl.classList.contains("cheer")) confetti(!!stars);
  cardEl.classList.remove("cheer");
  cardEl.classList.add("on");
}

onFinish = function (won) {
  clearIntro();                  // won under the walkthrough: unpause before the card
  if (won) { SFX.win(); buzz([18, 60, 18]); } else { SFX.lose(); buzz(90); }
  TUT = null; tutKey = ""; $("coach").hidden = true;   // the lesson is over either way
  setPaused(true);                                     // a card is up: an ad may land here
  if (won) PLATFORM.happytime();
  /* ⚠ After setPaused(true), which silences anything already sounding - fired
     above it, this cue would be started and cut down inside the same function.
     The card is already CHEER_MS behind the win, so the room is heard first and
     then read over: a beat of the place reacting, then LEVEL COMPLETE. */
  if (won) ambCue();
  const stars = won ? starsFor(S) : 0;
  const lvl = CUR;
  const pay = purse();
  /* ⚠ Here, while `S` is still the board that was just played - teleEnd reads
     `S.moves` off it, and the next startLevel replaces it. The row goes out
     before the card so a player who closes the tab on the win still counts.
     teleEnd hands back the run's length so GA and the database agree. */
  gaLevelEnd(lvl, won, Math.round(teleEnd(won, stars) / 1000), stars);
  if (won) {
    if (stars > (save.stars[lvl] || 0)) save.stars[lvl] = stars;   // only ever raises
    if (lvl + 1 > save.unlocked) save.unlocked = Math.min(CAMPAIGN.length, lvl + 1);
    save.streak++;
    save.coins += pay.total;
  } else {
    LOST = { streak: save.streak, hearts: save.hearts, heartAt: save.heartAt };
    save.streak = 0;
    if (CF.lives && hearts() > 0) { save.hearts--; if (!save.heartAt) save.heartAt = Date.now() + CF.heartSecs * 1000; }
  }
  if (won) LOST = null;
  persist();
  // Asked for `lvl`, the level just cleared - the bar is the reward for this
  // game, not for the one being handed over.
  const gen = cardGen;
  const card = () => gen === cardGen &&
    overlay(won ? "LEVEL COMPLETE!" : "OUT OF TIME", stars, "+" + pay.total,
    has("winstreak") && pay.bonus ? save.streak + " IN A ROW · +" + pay.bonus + " BONUS" : "",
    has("booster_time") ? "There is more time on the booster row, if the gold is there."
                        : "Clear the doorway first - the queue does the rest.",
    featureProgress(lvl), lvl);
  if (won) { cheer(); setTimeout(card, CHEER_MS); } else offerRevive(card);
};

/* ---- wiring ------------------------------------------------------------ */
document.getElementById("h-play").onclick = () => startLevel(save.unlocked);
/* The lives are the one number on the home screen that changes on its own, so
   the button that carries them is the one place that says when the next lands. */
document.getElementById("h-hearts").onclick = () => {
  const w = heartIn();
  say(w ? hearts() + " of " + CF.heartMax + " lives - the next lands in " + fmt(w) + "."
        : "Lives are full: " + CF.heartMax + " of " + CF.heartMax + ".");
  show("home");
};
document.getElementById("h-levels").onclick = () => show("levels");
document.getElementById("l-back").onclick = () => show("home");
// the chip is a real control: it plays the stamp again mid-board
$("g-grade").onclick = () => { const d = diffOf(CUR); if (d) showWarning(d, null); };
// the menu button opens Settings; Home lives inside it, beside the switches
/* The gear pauses the game and opens the card. It used to be a hamburger
   wired straight to `show("home")`, so the one control on the HUD that was
   not the clock took the player off the board in a single tap. */
$("g-menu").onclick = openSettings;
document.getElementById("rv-go").onclick = revive;
document.getElementById("rv-x").onclick = declineRevive;
document.getElementById("c-home").onclick = () => { hideCard(); show("home"); };
document.getElementById("c-next").onclick = () => {
  if (S.phase === "win" && CUR >= HOME_AFTER) { hideCard(); show("home"); return; }
  startLevel(S.phase === "win" ? CUR + 1 : CUR);
};
addEventListener("resize", () => { fitDesign(); draw(); });

let last = performance.now();
function tick(now) {
  const dt = (now - last) / 1000; last = now;
  if (JUMP && S && S.phase === "play") draw();   // the armed rings breathe
  if (S && S.phase === "play" && !PAUSED) {
    // anybody walking, or a seat the player has already committed
    if (!RUNNING && (S.anim.length || S.boarding || S.moves > 0)) RUNNING = true;
    if (RUNNING) {
      S.left -= dt;
      if (S.left <= 0) { S.left = 0; finish(false); }
    }
    onHud();
    if (TUT) draw();               // the only thing on screen that moves by itself
  }
  requestAnimationFrame(tick);
}
fitDesign();
requestAnimationFrame(tick);

/* ⚠ Nothing the player can press exists until the host has answered. The save is
   read here and not at module scope because on a host with a cloud save an early
   read hands back the local copy, and the first write after it would push that
   stale copy over their real progress. init() cannot hang - it owns a timeout
   and resolves either way - so this is a wait with a ceiling, not a gamble. */
/** ⚠ Anything that drives the game from outside - a test, a screenshot script -
    has to wait for this, not just for `ready`. `ready` only means the atlases
    decoded; boot is still going to read the save and pick a screen after it, and
    a startLevel() called in between is undone by the show("home") that follows. */
let BOOTED = false;

(async function boot() {
  PLATFORM.loadingStart();
  await PLATFORM.init();
  loadSave();
  if (INTRO_ONLY) {
    save.seenBoosters = FEATURES.map(f => f.id).filter(id => id !== INTRO_ONLY);
    save.coins = Math.max(save.coins, 5000);   // so a locked-out price is not the thing being read
  }
  PLATFORM.onHostMuteChange(() => { syncToggles(); ambSync(); });
  PLATFORM.loadingStop();

  const asked = parseInt(LINK.get("level"), 10);
  if (asked >= 1) {
    startLevel(asked);       // straight onto the board named in the address
  } else {
    CUR = Math.min(save.unlocked, CAMPAIGN.length);
    load(CAMPAIGN[CUR - 1]); // a board exists from the start, behind the home screen
    show("home");
  }
  BOOTED = true;
})();
