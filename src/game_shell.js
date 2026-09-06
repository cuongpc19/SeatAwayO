/* ---------------- the game shell ----------------
   Everything the editor page does not need: saved progress, a home screen, a
   level picker, and a result card. The rules all live in the engine above; this
   file only decides what the player sees around them.                        */

RICH = true;                       // the engine draws a room, not a bare grid

/* The room changes every five levels and then starts the rotation over, so a run
   of play keeps moving somewhere new without needing 633 rooms to do it.
   ?theme=<name> pins one for testing and stops the rotation. */
const MOVIE_SRC = "/*__MOVIE__*/";
const THEME_RUN = 5;                    // levels before the room changes
const THEME_ORDER = ["classroom", "station", "stadium", "concert", "cinema"];
const pinnedTheme = new URLSearchParams(location.search).get("theme");

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
  THEME = themeFor(level);
  // whatever the canvas does not cover should be the room's own colour, not the
  // one left behind by the level before it
  const page = THEMES[THEME].page;
  document.getElementById("play").style.background = page || "#98a1ab";
}

/* Drop a painted room at bg/room.png (or pass ?bg=<name>) and it replaces the
   procedural station. Missing file, no harm: the station stays. */
(() => {
  const q = new URLSearchParams(location.search);
  // Only when asked for by name: guessing at a file meant every single load
  // reported a 404 for a plate nobody had made yet.
  const asked = q.get("bg");
  if (!asked) return;
  const img = new Image();
  img.onload = () => { BG = img; draw(); };
  img.src = "bg/" + asked + ".png";
})();

/* ---- the numbers the shipped game runs on -----------------------------
   Injected from its own RemoteConfig at build time. Every threshold, price and
   reward below is the live value, not a guess. */
const CF = /*__CONFIG__*/;
const unlockedAt = f => { const n = CF.unlock[f]; return n > 0 ? n : Infinity; };
const has = f => save.unlocked >= unlockedAt(f);

/* ---- saved progress ---------------------------------------------------- */
const SAVE_KEY = "seataway.save.v2";
const blank = () => ({
  unlocked: 1, stars: {}, coins: 0,
  seenBoosters: [],                // which unlock notices have been shown
  streak: 0,                       // wins in a row
  hearts: CF.heartMax, heartAt: 0, // heartAt: when the next one lands, ms epoch
  jumps: 0,                        // jump booster charges bought
});
let save = blank();
try { save = Object.assign(blank(), JSON.parse(localStorage.getItem(SAVE_KEY) || "{}")); }
catch (e) { /* private window, cleared data, a browser that refuses storage */ }
function persist() {
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(save)); } catch (e) {}
}
const totalStars = () => Object.values(save.stars).reduce((a, v) => a + v, 0);

/* Hearts refill on the clock whether the page is open or not, so the count is
   worked out from the stored timestamp rather than ticked down. */
function hearts() {
  if (save.hearts >= CF.heartMax) { save.heartAt = 0; return save.hearts; }
  const now = Date.now();
  if (!save.heartAt) { save.heartAt = now + CF.heartSecs * 1000; persist(); }
  while (save.hearts < CF.heartMax && now >= save.heartAt) {
    save.hearts++;
    save.heartAt = save.hearts >= CF.heartMax ? 0 : save.heartAt + CF.heartSecs * 1000;
  }
  return save.hearts;
}
const heartIn = () => (save.hearts >= CF.heartMax || !save.heartAt) ? 0
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
  for (const id of Object.values(screens))
    document.getElementById(id).classList.toggle("on", id === name);
  if (name === "home") refreshHome();
  if (name === "levels") buildGrid();
  if (name === "play") requestAnimationFrame(draw);
}
function refreshHome() {
  $("h-level").textContent = save.unlocked;
  $("h-stars").textContent = totalStars();
  $("h-coins").textContent = save.coins;
  const w = heartIn();
  $("h-hearts").innerHTML = "Lives <b>" + hearts() + " / " + CF.heartMax + "</b>"
    + (w ? " <span style=\"opacity:.7\">" + fmt(w) + "</span>" : "");
}
function buildGrid() {
  const grid = document.getElementById("l-grid");
  grid.innerHTML = "";
  // Far more boards than anyone will scroll: show what is reachable plus a
  // little runway, so the picker stays a picker and not a 633-row wall.
  const upto = Math.min(CAMPAIGN.length, save.unlocked + 24);
  for (let n = 1; n <= upto; n++) {
    const b = document.createElement("button");
    const st = save.stars[n] || 0;
    b.className = "cellbtn " + (n > save.unlocked ? "locked" : st ? "done" : "");
    b.innerHTML = n + (st ? '<span class="s">' + "★".repeat(st) + "</span>" : "");
    if (n <= save.unlocked) b.onclick = () => startLevel(n);
    grid.appendChild(b);
  }
}

/* ---- playing -----------------------------------------------------------
   33 of the 633 boards are second and third arrangements shipped under a level
   name the game already used, and a few of those are display pieces nobody can
   clear. Counting them as levels pushed every number after the third out of step
   with the APK - "level 10" was Level_00005 all over again. The game plays one
   board per name; the editor still has all 633.                              */
const CAMPAIGN = LEVELS.map((b, i) => i + 1).filter((_, i) => LEVELS[i].variant === 0);
let CUR = 1;                       // the level number the player sees

function startLevel(n) {
  if (hearts() <= 0) {
    show("home");
    say("Out of lives - one comes back every " + Math.round(CF.heartSecs / 60) + " minutes.");
    return;
  }
  JUMP = false;
  CUR = Math.max(1, Math.min(CAMPAIGN.length, n));
  setTimeout(announceBoosters, 600);
  hideCard();
  show("play");
  applyTheme(CUR);                 // before load(), so the first frame is right
  load(CAMPAIGN[CUR - 1]);
  onHud();
}

let sayUntil = 0;
const toastEl = () => document.getElementById("hint");
onSay = msg => {
  const el = toastEl();
  el.textContent = msg; el.classList.add("on");
  sayUntil = performance.now() + 2600;
};

const $ = id => document.getElementById(id);
const setAll = (ids, text) => { for (const i of ids) { const e = $(i); if (e) e.textContent = text; } };

onHud = function () {
  if (!S) return;
  setAll(["g-level"], CUR);
  setAll(["g-clock"], fmt(S.left));
  setAll(["g-seated"], S.seated + " / " + S.total + " seated");
  setAll(["g-left"], S.queue.length + " waiting");
  setAll(["g-coins", "h-coins"], save.coins);
  setAll(["h-stars"], totalStars());
  boosterUi();
  const pct = Math.max(0, S.left / S.time) * 100;
  const b = $("g-bar");
  b.style.width = pct + "%"; b.classList.toggle("warn", pct < 25);
  $("g-clock").classList.toggle("warn", pct < 25);
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
/** Announce a booster the first time the player is high enough to use it. */
function announceBoosters() {
  for (const [f, label] of [["booster_jump", "Jump - lift a seat over everything"],
                            ["booster_time", "+15 seconds on the clock"]]) {
    if (!has(f) || save.seenBoosters.includes(f)) continue;
    save.seenBoosters.push(f); persist();
    say("New booster: " + label + ".");
    return;                        // one at a time, or the second overwrites the first
  }
}

function boosterUi() {
  const t = $("b-time"), j = $("b-jump");
  t.hidden = !has("booster_time");
  j.hidden = !has("booster_jump");
  $("b-time-cost").textContent = CF.boosterTime.price;
  $("b-jump-cost").textContent = save.jumps > 0 ? save.jumps + " left" : CF.boosterJump.price;
  t.classList.toggle("broke", save.coins < CF.boosterTime.price);
  j.classList.toggle("broke", save.jumps === 0 && save.coins < CF.boosterJump.price);
  j.classList.toggle("armed", JUMP);
}

$("b-time").onclick = () => {
  if (!S || S.phase !== "play") return;
  if (save.coins < CF.boosterTime.price) return say("Not enough gold for more time.");
  save.coins -= CF.boosterTime.price;
  S.left += CF.boosterTime.value;
  S.time = Math.max(S.time, S.left);          // keep the bar honest
  persist(); say("+" + CF.boosterTime.value + " seconds."); onHud();
};

$("b-jump").onclick = () => {
  if (!S || S.phase !== "play") return;
  if (JUMP) { JUMP = false; say("Jump cancelled."); onHud(); draw(); return; }
  if (save.jumps === 0) {
    if (save.coins < CF.boosterJump.price) return say("Not enough gold for a jump.");
    save.coins -= CF.boosterJump.price;
    save.jumps = CF.boosterJump.uses > 0 ? CF.boosterJump.uses : 1;
    persist();
  }
  JUMP = true;
  say("Jump armed - drag any seat straight to where you want it.");
  onHud(); draw();
};

/* One charge per seat actually moved, and the arming ends with it. */
onSeatMoved = () => {
  if (!JUMP) return;
  JUMP = false;
  save.jumps = Math.max(0, save.jumps - 1);
  persist(); onHud();
};

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
  if (!blocked && pickSeat(S, S.queue[0])) return null;   // the queue is already moving

  // With the doorway blocked there is only one seat worth talking about. With
  // it clear the fault is somewhere in the floor, so weigh every seat that moves.
  const cands = blocked ? [S.seats[S.occ[idx(S, S.W - 1, S.door)]]] : S.seats;
  let best = null;
  for (const b of cands) {
    const home = [b.c, b.r];
    for (const [c, r] of placements(S, b)) {
      place(S, b, c, r);
      // Only a move that both frees the doorway and leaves the front of the
      // queue a seat it can walk to counts; among those, take the one that
      // opens the most floor, which is the one that keeps the board going.
      const gain = isFree(S, S.W - 1, S.door) && pickSeat(S, S.queue[0])
        ? reachRegion(S).reduce((a, v) => a + v, 0) : 0;
      place(S, b, home[0], home[1]);                       // and straight back
      if (gain > (best ? best.gain : 0)) best = { seat: b, to: [c, r], gain };
    }
  }
  if (!best) return null;
  return { seat: best.seat, to: best.to,
    title: blocked ? "A seat is in the doorway" : "Open them a path",
    text: blocked
      ? "Nobody can get on. Press and hold that seat, drag it onto the glowing tile and let go - the queue boards on its own."
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

/* The pointing itself, drawn in the room's own projection so it lands on the
   right tile at every window size. The engine hands the overlay the last word
   on the frame; everything here is painted over the finished room. */
onOverlay = () => {
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
  const fx = A[0] + (B[0] - A[0]) * f, fy = A[1] + (B[1] - A[1]) * f;
  const fr = Math.max(6, LAY.s * .16);
  ctx.fillStyle = "#fff";
  ctx.globalAlpha = .3 * fade;
  ctx.beginPath(); ctx.arc(fx, fy, fr * 1.8, 0, Math.PI * 2); ctx.fill();
  ctx.globalAlpha = .95 * fade;
  ctx.beginPath(); ctx.arc(fx, fy, fr, 0, Math.PI * 2); ctx.fill();
  ctx.globalAlpha = .85 * fade;
  ctx.strokeStyle = "#22283c"; ctx.lineWidth = Math.max(1.5, LAY.s * .028);
  ctx.beginPath(); ctx.arc(fx, fy, fr, 0, Math.PI * 2); ctx.stroke();
  ctx.restore();
};

/* ---- the result card --------------------------------------------------- */
const cardEl = document.getElementById("card");
function hideCard() { cardEl.classList.remove("on"); }
onNewLevel = hideCard;

const STAR_ON = '<svg viewBox="0 0 24 24"><defs><linearGradient id="g%I%" x1="0" y1="0" x2="0" y2="1">'
  + '<stop offset="0" stop-color="#ffe89a"/><stop offset="1" stop-color="#e0a71d"/></linearGradient></defs>'
  + '<path d="M12 2.6l2.9 5.9 6.5.95-4.7 4.6 1.1 6.45L12 17.45 6.2 20.5l1.1-6.45-4.7-4.6 6.5-.95z" '
  + 'fill="url(#g%I%)" stroke="#a9761a" stroke-width="1.1" stroke-linejoin="round"/></svg>';
const STAR_OFF = '<svg viewBox="0 0 24 24">'
  + '<path d="M12 2.6l2.9 5.9 6.5.95-4.7 4.6 1.1 6.45L12 17.45 6.2 20.5l1.1-6.45-4.7-4.6 6.5-.95z" '
  + 'fill="#cfc6b4" stroke="#a79d8a" stroke-width="1.1" stroke-linejoin="round"/></svg>';

function confetti(on) {
  const box = document.getElementById("c-confetti");
  box.innerHTML = "";
  if (!on) return;
  const cols = ["#e83e48", "#fa822a", "#fac42e", "#4ac65c", "#37c6d8", "#3f7ce8", "#a05de0", "#ff7ab8"];
  for (let i = 0; i < 26; i++) {
    const p = document.createElement("i");
    p.style.left = Math.random() * 100 + "%";
    p.style.background = cols[(Math.random() * cols.length) | 0];
    p.style.animationDuration = (2.4 + Math.random() * 2.2) + "s";
    p.style.animationDelay = (-Math.random() * 3) + "s";
    box.appendChild(p);
  }
}

onFinish = function (won) {
  TUT = null; tutKey = ""; $("coach").hidden = true;   // the lesson is over either way
  const stars = won ? starsFor(S) : 0;
  const lvl = CUR;
  const pay = purse();
  if (won) {
    if (stars > (save.stars[lvl] || 0)) save.stars[lvl] = stars;   // only ever raises
    if (lvl + 1 > save.unlocked) save.unlocked = Math.min(CAMPAIGN.length, lvl + 1);
    save.streak++;
    save.coins += pay.total;
  } else {
    save.streak = 0;
    if (hearts() > 0) { save.hearts--; if (!save.heartAt) save.heartAt = Date.now() + CF.heartSecs * 1000; }
  }
  persist();
  document.getElementById("c-card").classList.toggle("lose", !won);
  document.getElementById("c-title").textContent = won ? "LEVEL CLEAR!" : "OUT OF TIME";
  document.getElementById("c-rays").style.display = won ? "" : "none";
  document.getElementById("c-coins").style.display = won ? "" : "none";
  document.getElementById("c-coins").lastElementChild.textContent =
    "+" + pay.total + (pay.bonus ? "  (streak +" + pay.bonus + ")" : "");
  document.getElementById("c-sum").innerHTML = won
    ? "Everyone seated with <b>" + fmt(S.left) + "</b> to spare, in <b>" + S.moves + "</b> seat move"
      + (S.moves === 1 ? "." : "s.")
      + (has("winstreak") && save.streak > 1 ? " <b>" + save.streak + "</b> in a row." : "")
    : "The show started with <b>" + S.queue.length + "</b> still outside.";
  document.getElementById("c-next").textContent = won ? "NEXT" : "RETRY";

  const box = document.getElementById("c-stars");
  box.innerHTML = "";
  for (let i = 0; i < 3; i++) {
    const s = document.createElement("div");
    s.className = "star" + (i === 1 ? " big" : "");
    s.innerHTML = i < stars ? STAR_ON.replace(/%I%/g, i) : STAR_OFF;
    box.appendChild(s);
    // staggered, so three stars land one after another rather than all at once
    setTimeout(() => s.classList.add("pop"), 180 + i * 190);
  }
  confetti(won);
  cardEl.classList.add("on");
};

/* ---- wiring ------------------------------------------------------------ */
document.getElementById("h-play").onclick = () => startLevel(save.unlocked);
document.getElementById("h-levels").onclick = () => show("levels");
document.getElementById("l-back").onclick = () => show("home");
$("g-retry").onclick = () => startLevel(CUR);
$("g-home").onclick = () => { hideCard(); show("home"); };
document.getElementById("c-home").onclick = () => { hideCard(); show("home"); };
document.getElementById("c-next").onclick = () =>
  startLevel(S.phase === "win" ? CUR + 1 : CUR);
addEventListener("resize", draw);

let last = performance.now();
function tick(now) {
  const dt = (now - last) / 1000; last = now;
  if (S && S.phase === "play") {
    S.left -= dt;
    if (S.left <= 0) { S.left = 0; finish(false); }
    onHud();
    if (TUT) draw();               // the only thing on screen that moves by itself
  }
  requestAnimationFrame(tick);
}
CUR = Math.min(save.unlocked, CAMPAIGN.length);
load(CAMPAIGN[CUR - 1]);   // a board exists from the start, behind the home screen
show("home");
requestAnimationFrame(tick);
