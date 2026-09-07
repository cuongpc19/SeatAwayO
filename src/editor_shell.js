/* ---------------- export ----------------
   The live board as one entry of lv/boards_campaign.json, so a layout edited
   here can be saved off the page and built back in. Every field this page
   cannot touch - name, variant, track, diff, cam, gate, big, hidden - is copied
   through from the source board, so a re-import is byte-identical apart from
   what actually moved. `door` is the one addition: the shipped data never
   records it, and load() reads it back when a board carries one.

   The queue comes off the source board, not off S: S.queue is what is still
   waiting at the stop, and a board saved half-played would otherwise lose every
   passenger who had already found a seat. Seats, though, are taken where they
   stand right now - that is the edit. */
function boardJSON() {
  const raw = LEVELS[S.level - 1];
  const holes = [];
  for (let i = 0; i < S.hole.length; i++) if (S.hole[i]) holes.push(i);
  const seats = S.seats.slice().sort((a, b) => a.id - b.id)
                 .map(b => [b.c, b.r, b.len, b.colour, b.dir]);
  return { ...raw, w: S.W, h: S.H, holes, seats,
           queue: raw.queue.slice(), time: S.time, door: S.door };
}

let sayUntil = 0;
onSay = msg => {
  document.getElementById("hint").textContent = msg;
  sayUntil = performance.now() + 2600;      // hud() leaves the hint alone until then
};
onNewLevel = () => document.getElementById("ov").classList.remove("on");
onFinish = won => {
  document.getElementById("ov-title").textContent = won ? "Level complete" : "Out of time";
  document.getElementById("ov-text").textContent = won
    ? "Everyone seated with " + fmt(S.left) + " left, in " + S.moves + " seat moves."
    : "The bus pulled away with " + S.queue.length + " still at the stop.";
  document.getElementById("ov-next").style.display = won ? "" : "none";
  document.getElementById("ov").classList.add("on");
};
onHud = function hud() {
  if (!S) return;
  const m = /Level_0*(\d+)(?:_(\d+))?(?:#(\d+))?/.exec(S.name);
  document.getElementById("s-level").textContent = m
    ? m[1] + (m[2] ? "-" + m[2] : "") + (m[3] ? "\u00b7" + m[3] : "")
    : S.level;
  document.getElementById("s-seated").textContent = S.seated + " / " + S.total;
  document.getElementById("s-grid").textContent = S.W + "×" + S.H;
  document.getElementById("s-col").textContent = S.colours;
  document.getElementById("s-time").textContent = fmt(S.left);
  const pct = Math.max(0, S.left / S.time) * 100;
  const bar = document.getElementById("s-bar");
  bar.style.width = pct + "%";
  bar.classList.toggle("warn", pct < 22);
  document.getElementById("s-time").classList.toggle("warn", pct < 22);
  document.getElementById("q-chips").innerHTML = S.queue.slice(0, 9).map((ci, i) =>
    `<span class="chip ${i === 0 ? "next" : ""}" style="background:${CSS[colName(ci)]}"></span>`).join("");
  document.getElementById("q-more").textContent = S.queue.length > 9 ? "+" + (S.queue.length - 9) : "";
  const blocked = !isFree(S, S.W - 1, S.door);
  const reach = reachRegion(S).reduce((a, v) => a + v, 0);
  const freeTotal = S.W * S.H - S.hole.reduce((a, v) => a + v, 0) - S.seats.reduce((a, b) => a + b.len, 0);
  if (!sayUntil || performance.now() > sayUntil)
   document.getElementById("hint").textContent = blocked
    ? "A seat is parked in the doorway - drag it clear so people can get on."
    : (S.queue.length && !S.nextSeat
        ? "Nobody at the front can reach a seat they fit - slide seats to open a path."
        : "Press and hold a seat, drag it clear of the aisle, let go. Passengers board on their own.");
  document.getElementById("method").textContent =
    "Board " + S.name + ", exactly as shipped: same grid, seats, colours, passenger list and clock. "
    + "The level data never records the door, so it sits at a fixed spot on the right wall (row "
    + S.door + " of " + S.H + ", adjustable with the Door buttons) and, as in the game, a seat is often "
    + "parked in front of it. Right now " + reach + " of the " + freeTotal + " empty floor tiles connect to the door"
    + (blocked ? " - none, because the doorway itself is blocked." : ".");

  // The export panel tracks the board, so a seat dragged with it open is already
  // in the JSON. Rewriting it under a selection would cancel the copy, so a box
  // the pointer is in is left alone until it loses focus.
  const panel = document.getElementById("exp"), box = document.getElementById("exp-json");
  if (!panel.hidden && document.activeElement !== box) {
    const b = boardJSON(), text = JSON.stringify(b);
    if (box.value !== text) {
      box.value = text;
      document.getElementById("exp-note").textContent =
        b.id + " \u00b7 " + b.w + "\u00d7" + b.h + " \u00b7 " + b.seats.length + " seats \u00b7 "
        + b.queue.length + " passengers \u00b7 door row " + b.door
        + (S.seated ? " \u00b7 " + S.seated + " already aboard, so this saves the seats where they now sit" : "");
    }
  }
};
document.getElementById("b-retry").onclick = () => load(S.level);
document.getElementById("ov-retry").onclick = () => load(S.level);
document.getElementById("ov-next").onclick = () => load(S.level + 1);
document.getElementById("b-prev").onclick = () => load(S.level - 1);
document.getElementById("b-next").onclick = () => load(S.level + 1);
document.getElementById("b-door-up").onclick = () => { DOOR_ROW = Math.max(0, S.door - 1); load(S.level); };
document.getElementById("b-door-dn").onclick = () => { DOOR_ROW = Math.min(S.H - 1, S.door + 1); load(S.level); };
document.getElementById("b-door-auto").onclick = () => { DOOR_ROW = null; load(S.level); };
document.getElementById("b-guides").onclick = ev => {
  GUIDES = !GUIDES;
  ev.target.textContent = GUIDES ? "Guides on" : "Guides off";
  draw();
};
document.getElementById("b-trace").onclick = e => {
  TRACING = !TRACING;
  e.target.textContent = "Trace " + (TRACING ? "on" : "off");
  document.getElementById("trace").hidden = !TRACING;
};
document.getElementById("b-speed").onclick = ev => {
  SPEED = SPEED === 1 ? 2 : SPEED === 2 ? 0.5 : 1;
  ev.target.textContent = "Speed " + (SPEED === 0.5 ? "\u00bd" : SPEED) + "\u00d7";
};
document.getElementById("b-jump").onclick = () => {
  const v = prompt("Board 1-" + LEVELS.length + " (" + LEVELS.length + " boards):", S.level);
  const n = parseInt(v, 10);
  if (n >= 1 && n <= LEVELS.length) load(n);
};
document.getElementById("b-export").onclick = ev => {
  const panel = document.getElementById("exp");
  panel.hidden = !panel.hidden;
  ev.target.textContent = panel.hidden ? "Export JSON" : "Hide JSON";
  onHud();                                     // fills the box the moment it opens
};
document.getElementById("b-exp-copy").onclick = async ev => {
  const box = document.getElementById("exp-json");
  try { await navigator.clipboard.writeText(box.value); }
  catch (e) { box.select(); document.execCommand("copy"); }   // file:// has no clipboard API
  ev.target.textContent = "Copied";
  setTimeout(() => { ev.target.textContent = "Copy"; }, 1500);
};
document.getElementById("b-exp-save").onclick = () => {
  const b = boardJSON();
  const url = URL.createObjectURL(new Blob([JSON.stringify(b)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = String(b.id).replace(/[^\w.-]+/g, "_") + ".json";
  a.click();
  URL.revokeObjectURL(url);
};

addEventListener("resize", draw);

let last = performance.now();
function tick(now) {
  const dt = (now - last) / 1000; last = now;
  if (S && S.phase === "play") {
    S.left -= dt;
    if (S.left <= 0) { S.left = 0; finish(false); }
    onHud();
  }
  requestAnimationFrame(tick);
}
load(1);
requestAnimationFrame(tick);
