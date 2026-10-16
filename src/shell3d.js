/* ---------------- additions to the shell, for the 3D build only ----------------
   Built into the `3d` target only - see build.py - and appended AFTER
   game_shell.js, inside the same script. The shell is not edited, and the 2D
   game that ships has none of this.

   The celebration a win makes.

   Fireworks: every burst over the board during the cheer goes off as a handful
   of close firecrackers - "đôm đốp". Chosen by ear off a page of candidates
   (game3d/sfx.html, choice 1, "Đôm đốp gần") after five rounds of guessing were
   turned down: a high-passed hiss, Marble Sort's cork-pop and bell, a low boom,
   a pop, a string. Every one of those was filtered noise 30-120 ms long, and
   that is what was wrong with all of them - a hiss, a thud or a crunch, never a
   pop. What put it right was measuring real ones: public-domain New Year
   recordings off Wikimedia Commons, every pop in them found and taken apart.

     - a close firecracker is ONE pressure pulse: a spike 0.1-0.4 ms wide, a
       rebound of the other sign 0.5-2 ms wide, 20 dB down within ~10 ms;
     - it is bright - centred near 1.5-2.7 kHz - which is also why a phone,
       with no bass to speak of, plays it well;
     - after it, the street it went off in: ~22 dB under the hit, gone by
       100-300 ms;
     - in the thick of it ~13 pops a second, the gaps median 75-130 ms, the
       levels within a few dB of each other.

   A pulse that short cannot be made from an envelope on a node, so the pops are
   written sample by sample into a buffer; the street is a convolver. Rendered
   offline and measured with the same script as the recordings, choice 1 landed
   inside their range on every one of those numbers.

   Stars landing on the card keep Marble Sort's starPop, a triangle note a step
   higher for each star: the star animation is Marble Sort's already, and this
   was its sound.

   Synthesised, like every other sound in this game: there is no audio file in
   the build. The recordings were measured, not shipped. */
(function () {
  if (typeof starBurst !== "function") return;     // build.py asserts it exists

  /** The audio context, or null when sound is off. ⚠ The host's mute wins,
      exactly as it does for every other cue in the shell. */
  function audio() {
    if (!save.sound || PLATFORM.hostMuted()) return null;
    try {
      AC = AC || new (window.AudioContext || window.webkitAudioContext)();
      if (AC.state === "suspended") AC.resume();
      return AC;
    } catch (e) { return null; }
  }

  /* ---- the firecrackers ------------------------------------------------- */
  function rnd(a, b) { return a + Math.random() * (b - a); }
  /** Most gaps short and a few long, which is how the recordings space them. */
  function lognorm(median, sigma) {
    const u = 1 - Math.random(), v = Math.random();
    return median * Math.exp(sigma * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v));
  }
  function gains(amp, pan) {
    return [Math.cos((pan + 1) * Math.PI / 4) * amp, Math.sin((pan + 1) * Math.PI / 4) * amp];
  }
  /** One pressure pulse into a stereo pair: the spike, then the rebound. */
  function pulse(L, R, sr, t, amp, pan, w1, w2) {
    const [gl, gr] = gains(amp, pan);
    let i = Math.round(t * sr);
    const seg = (w, g) => {
      const n = Math.max(2, Math.round(w * sr));
      for (let k = 0; k < n && i < L.length; k++, i++) {
        const v = g * Math.sin(Math.PI * (k + .5) / n); L[i] += v * gl; R[i] += v * gr;
      }
    };
    seg(w1, -1); seg(w2, .62);
  }
  /** The noise after the hit - paper and smoke - dying away in a few ms. */
  function grit(L, R, sr, t, amp, pan, tau, len, fc) {
    const [gl, gr] = gains(amp, pan), k1 = 1 - Math.exp(-2 * Math.PI * fc / sr);
    const comp = Math.sqrt((2 - k1) / k1);     // the same level whatever the cutoff
    let i = Math.round(t * sr), y = 0;
    for (let k = 0; k < len * sr && i < L.length; k++, i++) {
      y += k1 * ((Math.random() * 2 - 1) - y);
      const v = y * comp * .58 * amp * Math.exp(-k / (tau * sr)); L[i] += v * gl; R[i] += v * gr;
    }
  }
  /** One firecracker; `size` near 1.
      ⚠ The narrow spike and the noise after it lasting ARE the brightness. A
      first cut with a pulse twice as wide and a shorter tail measured 530 Hz
      and 2 ms against the recording's 2.7 kHz and 12 ms - a thud, not a pop.
      Often the same pulse comes again off the ground, a few ms later. */
  function cracker(L, R, sr, t, amp, pan, size) {
    const w1 = rnd(.00008, .00016) * size, w2 = rnd(.0005, .0010) * size;
    pulse(L, R, sr, t, amp, pan, w1, w2);
    grit(L, R, sr, t + .0002, amp * .8, pan, .006 * Math.sqrt(size), .045, 10000);
    if (Math.random() < .6) pulse(L, R, sr, t + rnd(.002, .008), amp * rnd(.3, .6), pan, w1 * 1.5, w2 * 1.2);
  }

  /** The street: noise dying over 0.45 s and darkening as it goes, with four
      walls in it. Unit energy, so the wet gain alone says how much there is. */
  function streetIR(a) {
    const T60 = .45, FC0 = 14000, FC1 = 5000, PRE = .004;
    const sr = a.sampleRate, n = Math.ceil(T60 * sr), b = a.createBuffer(2, n, sr);
    const fcAt = i => FC0 * Math.pow(FC1 / FC0, i / sr / T60);
    for (let ch = 0; ch < 2; ch++) {
      const x = b.getChannelData(ch), hit = new Float32Array(n);
      for (const [d, g] of [[.007, .35], [.018, .25], [.031, .18], [.049, .12]]) {
        const i = Math.round(d * rnd(.85, 1.15) * sr); if (i < n) hit[i] = g * rnd(.7, 1);
      }
      let y = 0, e = 0;
      for (let i = 0; i < n; i++) {
        const t = i / sr, k1 = 1 - Math.exp(-2 * Math.PI * fcAt(i) / sr);
        const on = t < PRE ? 0 : Math.min(1, (t - PRE) / .012);
        y += k1 * ((Math.random() * 2 - 1) * on * Math.exp(-6.91 * t / T60) - y);
        x[i] = y; e += y * y;
      }
      const s = 1 / Math.sqrt(e);
      for (let i = 0; i < n; i++) x[i] *= s;
      // the walls, low-passed like the rest, added after at their own level
      y = 0;
      for (let i = 0; i < n; i++) {
        const k1 = 1 - Math.exp(-2 * Math.PI * fcAt(i) / sr);
        y = y * (1 - k1) + hit[i]; x[i] += 3 * k1 * y;
      }
    }
    return b;
  }
  /** Dry and street into a limiter: four bursts overlap, and none may clip. */
  function makeBus(a, dest) {
    const lim = a.createDynamicsCompressor();
    lim.threshold.value = -2; lim.knee.value = 0; lim.ratio.value = 20; lim.attack.value = 0; lim.release.value = .08;
    lim.connect(dest);
    const input = a.createGain(), conv = a.createConvolver(), wet = a.createGain();
    conv.normalize = false; conv.buffer = streetIR(a); wet.gain.value = .45;   // ⚠ normalize before buffer
    input.connect(lim); input.connect(conv); conv.connect(wet); wet.connect(lim);
    return input;
  }
  let BUS = null;                          // one per context: the street is built once
  function bus(a) {
    if (!BUS || BUS.a !== a) BUS = { a, input: makeBus(a, a.destination) };
    return BUS.input;
  }
  /** One burst: four or five pops inside 0.7 s. A win fires four, 0.25 s apart,
      and they overlap into about 1.3 s of crackle - the density of the
      recordings at their thickest. */
  function crackle(a, dest, t) {
    const sr = a.sampleRate, b = a.createBuffer(2, Math.ceil(1.1 * sr), sr);
    const L = b.getChannelData(0), R = b.getChannelData(1);
    let at = 0;
    for (let i = 0, n = 4 + (Math.random() * 2 | 0); i < n && at < .7; i++) {
      cracker(L, R, sr, at, Math.pow(10, -rnd(0, 8) / 20) * .85, rnd(-.7, .7), rnd(.8, 1.3));
      at += Math.min(.25, Math.max(.025, lognorm(.1, .6)));
    }
    const s = a.createBufferSource(); s.buffer = b; s.connect(dest); s.start(t);
  }
  function firework() {
    const a = audio(); if (!a) return;
    crackle(a, bus(a), a.currentTime + .005);
  }

  /** A star landing on the card: Marble Sort's starPop. */
  function starPop(n) {
    const a = audio(); if (!a) return;
    const t = a.currentTime + .005, o = a.createOscillator(), g = a.createGain();
    o.type = "triangle"; o.frequency.setValueAtTime(600 + n * 220, t);
    g.gain.setValueAtTime(.0001, t);
    g.gain.exponentialRampToValueAtTime(.09, t + .012);
    g.gain.exponentialRampToValueAtTime(.0001, t + .24);
    o.connect(g); g.connect(a.destination); o.start(t); o.stop(t + .26);
  }

  /* For the check in tests: one burst rendered into an OfflineAudioContext
     through its own street, so it can be measured rather than only listened
     to. Nothing in the game reads it. */
  window.__crackle3d = (a, dest, t) => crackle(a, makeBus(a, dest), t);

  /* ⚠ Reassigned, not redeclared. A `function starBurst` written here would
     REPLACE the shell's - in one script the last declaration is the one every
     caller gets - and this wants the shell's sparks and flash as they are, with
     a sound added.

     Which sound is read off the card: while it is in its `cheer` state the
     bursts are over the board, and once it is up they are stars landing on it.
     The star count restarts for each win - a gap longer than the whole sequence
     (about 2.5s from the first burst to the last star) means a new one. */
  const burst = starBurst;
  let star = 0, last = 0;
  starBurst = function () {
    const now = performance.now();
    if (now - last > 2500) star = 0;
    last = now;
    if (cardEl.classList.contains("cheer")) firework();
    else starPop(star++);
    return burst.apply(this, arguments);
  };
})();

/* ================= footsteps, and the two Settings additions =================
   Also 3D-only, also asked for on this build. */
(function () {
  /** The audio context, or null when sound is off. ⚠ The host's mute wins. */
  function audio() {
    if (!save.sound || PLATFORM.hostMuted()) return null;
    try {
      AC = AC || new (window.AudioContext || window.webkitAudioContext)();
      if (AC.state === "suspended") AC.resume();
      return AC;
    } catch (e) { return null; }
  }

  /* ---- footsteps ------------------------------------------------------
     A passenger walking the floor makes a footfall every STEP_AT of ground
     covered. The line waiting outside makes none - see listen().
     Built the way Marble Sort builds a contact: a struck low body with a short
     band-passed tick on top, the tick being what a phone speaker carries.

     ⚠ Rate-limited across everybody, not per walker. Three people crossing at
     once at seven steps a second each is a rattle - the fault that took the
     drag cue out of the shell - so footfalls are never closer than STEP_GAP
     whoever makes them, and the room patters instead of drumming.

     ⚠ Not while they are in the air. The hop onto the seat is the shell's own
     moment and already ends in the seating thud; a footstep under it would put
     a foot on the ground in the middle of a jump.

     ⚠ Read off the engine's own state each frame - walker positions, and the
     line's places still to walk - rather than by hooking the walk: the walk is
     a closure inside autoBoard, and there is nothing to hook without editing
     the engine, which this build does not do. */
  const STEP_AT = 1.1;          // world units of floor per footfall (a cell is 1.6)
  const STEP_GAP = 70;          // ms: the closest two footfalls ever come
  let stepAt = 0, foot = 0;
  const seen = new WeakMap();

  function struck(a, dest, t, freq, gain, dur, partials) {
    const norm = partials.reduce((s, v) => s + v, 0) || 1;
    partials.forEach((amp, i) => {
      const o = a.createOscillator(), g = a.createGain();
      o.type = "sine"; o.frequency.setValueAtTime(freq * (i + 1), t);
      g.gain.setValueAtTime(.0001, t);
      g.gain.exponentialRampToValueAtTime(gain * amp / norm, t + .003);
      g.gain.exponentialRampToValueAtTime(.0001, t + dur);
      o.connect(g); g.connect(dest); o.start(t); o.stop(t + dur + .02);
    });
  }
  function tick(a, dest, t, gain, rate) {
    const len = Math.floor(a.sampleRate * .025), buf = a.createBuffer(1, len, a.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 5);
    const src = a.createBufferSource(); src.buffer = buf; src.playbackRate.value = rate;
    const bp = a.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 1400 * rate; bp.Q.value = 1.1;
    const g = a.createGain(); g.gain.value = gain;
    src.connect(bp); bp.connect(g); g.connect(dest); src.start(t);
  }
  /* ⚠ Pitched and pitched UP for the speaker it will play on. The first cut sat
     its body at 104-118 Hz and its tap at .03, and was reported as no footsteps
     at all: a phone speaker hardly moves below about 300 Hz, so the body was
     inaudible and the tap was all that was left, at a level under the room.
     This is the same lesson the shell learned with the seating thud ("a low
     sound is not a quiet one"). Now the body is around 200 Hz with its
     harmonics doing the carrying, and the tap leads. Levels set offline against
     the win chord - see STEP_TAP. */
  /** ⚠ Measured offline in the 300 Hz - 4 kHz band a phone actually plays. A
      footfall is 45 ms long, so it is the PEAK that decides whether it is heard,
      not the average: at .16/.06 it peaked at half a chord note and was still
      too faint; at these levels it peaks near 80% of one - every step heard,
      none of them louder than the music. */
  const STEP_TAP = .27, STEP_BODY = .085;
  function stepSound(a, dest, t, level, left) {
    struck(a, dest, t, (left ? 214 : 192) * (.95 + Math.random() * .1), STEP_BODY * level, .075, [1, .6, .3]);
    tick(a, dest, t, STEP_TAP * level, .95 + Math.random() * .15);
  }
  window.__step3d = (a, dest, t, level) => stepSound(a, dest, t, level, true);   // for the offline check
  /** One footfall: `level` 1 for a walker crossing the room.
      Left and right sit a few hertz apart, so a walk is a gait, not a click. */
  function footstep(level, force) {
    if (save.steps === false && !force) return;
    const a = audio(); if (!a) return;
    const now = performance.now();
    if (!force && now - stepAt < STEP_GAP) return;
    stepAt = now;
    foot ^= 1;
    stepSound(a, a.destination, a.currentTime + .004, level, foot);
  }

  function listen() {
    requestAnimationFrame(listen);
    if (!S || S.phase !== "play" || PAUSED || save.steps === false) return;
    for (const a of S.anim) {
      let w = seen.get(a);
      if (!w) { seen.set(a, { x: a.x, z: a.z, acc: STEP_AT * .5 }); continue; }
      const d = Math.hypot(a.x - w.x, a.z - w.z);
      w.x = a.x; w.z = a.z;
      if ((a.y || 0) > .15) continue;                 // in the air: the hop
      if ((w.acc += d) >= STEP_AT) { w.acc %= STEP_AT; footstep(1); }
    }
    // ⚠ Only the people crossing the room. The line shuffling up outside the
    // door stepped too - every boarding moved the whole queue a place, so each
    // seat taken came with a patter from seven people at once - and it was
    // asked to go: footsteps are for the ones walking to a seat.
  }
  requestAnimationFrame(listen);

  /* ---- Settings: the Footsteps switch, and RESET PROGRESS ------------------
     Put into the page here rather than into game_head.html, so the 2D build's
     settings card is untouched. Positions are in game3d.css.

     ⚠ RESET PROGRESS, not "START OVER FROM LEVEL 1": it is what a phone game's
     settings call this, so a player looking for it finds it, and it cannot be
     read as RESTART LEVEL, the button for this board that sits above it. */
  const vibeRow = $("set-row-vibe"), privacy = $("set-privacy");
  if (!vibeRow || !privacy) return;
  vibeRow.insertAdjacentHTML("afterend",
    '<div class="set-row" id="set-row-steps">'
    + '<svg class="set-ico" viewBox="0 0 24 24" aria-hidden="true">'
    + '<path d="M7.6 3.8c1.7 0 2.6 1.7 2.6 3.8s-.9 4-2.5 4S5 9.9 5 7.7s.9-3.9 2.6-3.9z"></path>'
    + '<path d="M6 14h3.6l-.3 3.1a1.7 1.7 0 0 1-3.4-.1z"></path>'
    + '<path d="M16.4 8.6c1.7 0 2.6 1.7 2.6 3.8s-.9 4-2.5 4-2.7-1.8-2.7-4 .9-3.8 2.6-3.8z"></path>'
    + '<path d="M14.8 18.8h3.6l-.3 2.9a1.7 1.7 0 0 1-3.4-.1z"></path></svg>'
    + '<span class="set-lab">Footsteps</span>'
    + '<button class="tog" id="set-steps" role="switch" aria-checked="true" aria-label="Footsteps"><i></i></button>'
    + '</div>');
  privacy.insertAdjacentHTML("afterend",
    '<button class="set-link" id="set-reset">RESET PROGRESS</button>'
    + '<div id="set-confirm" role="dialog" aria-modal="true" aria-labelledby="sc-head">'
    + '<div class="sc-dim"></div><div class="sc-panel"></div>'
    + '<div class="sc-head" id="sc-head">RESET PROGRESS?</div>'
    + '<div class="sc-text">You go back to level 1. Stars, gold and boosters are cleared; your sound settings stay.</div>'
    + '<button class="wide-btn set-btn" id="sc-no">KEEP PLAYING</button>'
    + '<button class="wide-btn red set-btn" id="sc-yes">RESET</button>'
    + '</div>');

  /* ⚠ Reassigned, not redeclared, for the same reason as starBurst above: the
     shell's two switches still have to be set by the shell's own body. */
  const sync = syncToggles;
  syncToggles = function () {
    sync.apply(this, arguments);
    $("set-steps").setAttribute("aria-checked", String(save.steps !== false));
  };
  // The switch demonstrates itself when it comes on, as the shell's do.
  $("set-steps").onclick = () => {
    save.steps = save.steps === false;
    persist(); syncToggles();
    if (save.steps) footstep(1, true);
  };

  const confirmBox = $("set-confirm");
  $("set-reset").onclick = () => confirmBox.classList.add("on");
  $("sc-no").onclick = () => confirmBox.classList.remove("on");
  confirmBox.querySelector(".sc-dim").onclick = () => confirmBox.classList.remove("on");
  /* ⚠ Progress goes, preferences stay (UI_UX_RULES 4.5): somebody who turned
     the sound off because they had heard the seating thud two hundred times
     should not be punished for starting again by getting it back. */
  $("sc-yes").onclick = () => {
    const keep = { sound: save.sound, vibe: save.vibe, steps: save.steps };
    save = Object.assign(blank(), keep);
    persist();
    confirmBox.classList.remove("on");
    setEl.classList.remove("off-board");
    dropSettings(); hideCard();
    startLevel(1);
  };

  /* ---- Settings away from a board: a gear on Home and on the progress screen
     The shell only opens Settings from the gear in a level - openSettings()
     refuses without a board in play - so the switches and RESET PROGRESS were out
     of reach anywhere else. The same card opens from both screens now, with the
     three level-only buttons (RESTART LEVEL, HOME, RESUME) taken off it.

     The gear is a clone of the in-game one, so the three look the same.

     ⚠ Closing it must not UNPAUSE. The shell's close is setPaused(false), which
     tells the host gameplay has started - from the home screen that is a start
     with nothing being played, an ad window opened on a menu. So off a board the
     card just goes away, and the shell's own handlers are rebound to a close
     that knows the difference: they were bound to the old function object when
     the shell ran, and reassigning the name alone would not reach them. */
  const head = document.querySelector("#settings .set-head");
  function openMenu() {
    setEl.classList.add("off-board");
    if (head) head.textContent = "SETTINGS";
    syncToggles();
    setEl.classList.add("on");
  }
  const close = closeSettings;
  closeSettings = function () {
    if (setEl.classList.contains("off-board")) {
      setEl.classList.remove("on", "off-board");
      confirmBox.classList.remove("on");
      return;
    }
    return close.apply(this, arguments);
  };
  const open = openSettings;
  openSettings = function () {
    setEl.classList.remove("off-board");
    if (head) head.textContent = "PAUSED";
    return open.apply(this, arguments);
  };
  $("g-menu").onclick = openSettings;
  $("set-close").onclick = closeSettings;
  $("set-dim").onclick = closeSettings;
  $("set-resume").onclick = closeSettings;

  function gear(id) {
    const g = $("g-menu").cloneNode(true);
    g.id = id;
    g.onclick = openMenu;
    return g;
  }
  // Home: the top-left corner, where the lives disc sits when lives are on.
  // They are off in this build's config, so the corner is empty.
  const home = document.querySelector("#home .design");
  if (home) home.appendChild(gear("h-gear"));
  // The progress screen: the empty right-hand slot of its top bar.
  const slot = document.querySelector("#levels .topbar > span:last-child");
  if (slot) slot.replaceWith(gear("l-gear"));
})();

/* ================= the gradients the result card's stars are lit with =================
   game3d.css points the stars' fills at these. A gradient has to live in an
   SVG in the page to be referenced from CSS, so one is put in, out of sight. */
(function () {
  document.body.insertAdjacentHTML("beforeend",
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
    + '<radialGradient id="g3d-star-on" cx="36%" cy="28%" r="78%">'
    + '<stop offset="0" stop-color="#fff8cf"/><stop offset=".32" stop-color="#ffd84a"/>'
    + '<stop offset=".72" stop-color="#ffb41c"/><stop offset="1" stop-color="#e5870a"/></radialGradient>'
    + '<radialGradient id="g3d-star-off" cx="36%" cy="28%" r="78%">'
    + '<stop offset="0" stop-color="#dbe8e4"/><stop offset=".6" stop-color="#a3c3bc"/>'
    + '<stop offset="1" stop-color="#7daaa2"/></radialGradient>'
    + '</defs></svg>');
})();


/* ================= the prize badge shows the booster's own tile =================
   The result card's bar ends in a badge for the next thing to unlock. For a
   booster the shell clones the button's line icon into it - which the 3D
   build's buttons no longer show, they are drawn tiles (game3d.css). So the
   badge shows the tile itself: the thing the player will be handed is the
   thing they are shown. ADD LINE gets one too; the shell had no icon for it
   and drew a grey seat.

   ⚠ Reassigned, not redeclared, as starBurst is above. Everything that is not
   a booster still goes to the shell's own drawing. */
(function () {
  const shellIcon = featIcon;
  featIcon = function (id) {
    if (id !== "time" && id !== "jump" && id !== "area") return shellIcon(id);
    const tile = document.createElement("i");
    tile.className = "feat-tile " + id;
    return tile;
  };
})();

/* ================= the time booster, seen to add time =================
   Asked for on the 3D build: buying time was a sound, a buzz and a toast,
   and the clock simply showed a bigger number. Now the "+30s" leaves the
   button, arcs up to the clock, and the clock takes it - a pop, a ring, a
   spray of sparks, a chime - while its digits count up from where they were.

   ⚠ The shell's own handler still does the buying; this only watches S.left
   across it and shows the difference, so every rule about price, free goes and
   the walkthrough stays where it was. The one rule added here is the limit:
   one extra time per board.
   ⚠ The digits: from the press until the count ends, onHud shows the clock
   WITHOUT the part still in flight - the real S.left less what has not landed
   - so the number never jumps up before the "+30s" arrives, and keeps ticking
   down underneath the whole time. */
(function () {
  const btn = $("b-time"), clock = $("g-clock"), pill = clock && clock.closest(".pill");
  if (!btn || !clock || !pill) return;
  const still = window.matchMedia ? matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };

  function audio() {
    if (!save.sound || PLATFORM.hostMuted()) return null;
    try {
      AC = AC || new (window.AudioContext || window.webkitAudioContext)();
      if (AC.state === "suspended") AC.resume();
      return AC;
    } catch (e) { return null; }
  }
  function note(a, t, f, type, peak, len) {
    const o = a.createOscillator(), g = a.createGain();
    o.type = type; o.frequency.setValueAtTime(f, t);
    g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + .006);
    g.gain.exponentialRampToValueAtTime(.0001, t + len);
    o.connect(g); g.connect(a.destination); o.start(t); o.stop(t + len + .02);
  }
  /** Landing: three rising bell notes, "ting-ting-ting", and the clock winding
      on under the count - small ticks, quieter than any other cue. */
  function chime(countMs) {
    const a = audio(); if (!a) return;
    const t = a.currentTime + .005;
    [1047, 1568, 2093].forEach((f, i) => note(a, t + i * .07, f, "triangle", .07, .26));
    for (let i = 0; i < 7; i++) note(a, t + .05 + i * countMs / 1000 / 7, 2400, "square", .012, .014);
  }

  let COUNT = null;                        // { s, delta, e } while a "+30s" is on its way in
  const shellHud = onHud;
  onHud = function () {
    shellHud.apply(this, arguments);
    if (COUNT && COUNT.s === S) clock.textContent = fmt(S.left - COUNT.delta * (1 - COUNT.e));
    // once a board has had its time the tile dims and drops its price, as the
    // lane booster's does once its lane is out. On S, so a new board - or the
    // same one restarted - starts with it back.
    const used = !!(S && S.timeBought);
    btn.classList.toggle("spent", used);
    if (used) btn.classList.remove("broke");
  };

  const centre = el => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2, r]; };
  function spark(x, y, dx, dy, ms, delay) {
    const s = document.createElement("i"); s.className = "tfx-spark";
    document.body.appendChild(s);
    s.animate([
      { transform: `translate(${x}px, ${y}px) translate(-50%, -50%) scale(1)`, opacity: 1 },
      { transform: `translate(${x + dx}px, ${y + dy}px) translate(-50%, -50%) scale(.2)`, opacity: 0 },
    ], { duration: ms, delay: delay || 0, easing: "cubic-bezier(.2,.7,.4,1)", fill: "both" }).onfinish = () => s.remove();
  }

  /** The "+30s", along a curve from the button to the clock. */
  function fly(delta, done) {
    const [x0, y0] = centre(btn), [x1, y1, r] = centre(pill);
    const cx = Math.min(x0, x1) - Math.max(40, Math.abs(y0 - y1) * .18), cy = (y0 + y1) / 2;   // bows out to the left
    const at = u => [(1 - u) * (1 - u) * x0 + 2 * (1 - u) * u * cx + u * u * x1,
                     (1 - u) * (1 - u) * y0 + 2 * (1 - u) * u * cy + u * u * y1];
    const el = document.createElement("div"); el.className = "tfx-fly";
    el.textContent = "+" + Math.round(delta) + "s";
    el.style.fontSize = Math.round(Math.max(24, r.height * .7)) + "px";
    document.body.appendChild(el);
    const MS = 720, frames = [];
    for (let i = 0; i <= 14; i++) {
      const t = i / 14, u = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      const [x, y] = at(u);
      const s = t < .2 ? .7 + .6 * (t / .2) : 1.3 - .45 * ((t - .2) / .8);
      frames.push({ transform: `translate(${x}px, ${y}px) translate(-50%, -50%) scale(${s})`,
                    opacity: t < .1 ? t / .1 : t > .92 ? (1 - t) / .08 : 1, offset: t });
    }
    el.animate(frames, { duration: MS, easing: "linear", fill: "both" }).onfinish = () => { el.remove(); done(); };
    for (let i = 1; i <= 6; i++) {           // a trail: sparks dropped where it has just been
      const t = i / 7, u = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2, [x, y] = at(u);
      spark(x, y, (Math.random() - .5) * 18, 14 + Math.random() * 10, 420, t * MS);
    }
  }

  /** The clock takes it: pop, ring, sparks, chime, and the digits count up. */
  function land(delta) {
    const [x, y, r] = centre(pill), COUNT_MS = 560;
    pill.animate([{ scale: 1 }, { scale: 1.3, offset: .35 }, { scale: 1 }],
                 { duration: 440, easing: "cubic-bezier(.3,1.6,.5,1)" });
    clock.classList.add("tfx-up"); setTimeout(() => clock.classList.remove("tfx-up"), COUNT_MS + 380);
    chime(COUNT_MS);
    if (!still.matches) {
      const ring = document.createElement("i"); ring.className = "tfx-ring";
      Object.assign(ring.style, { left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px" });
      document.body.appendChild(ring);
      ring.animate([{ transform: "scale(1)", opacity: .95 }, { transform: "scale(1.7)", opacity: 0 }],
                   { duration: 560, easing: "ease-out", fill: "both" }).onfinish = () => ring.remove();
      for (let i = 0; i < 10; i++) {
        const a = i / 10 * Math.PI * 2 + Math.random() * .4, d = r.width * .55 + Math.random() * 24;
        spark(x, y, Math.cos(a) * d, Math.sin(a) * d * .7, 520 + Math.random() * 160);
      }
    }
    const c = COUNT, t0 = performance.now();
    (function step(now) {
      if (COUNT !== c || c.s !== S) return;  // a new level, or a newer "+30s", took over
      const k = Math.min(1, (now - t0) / COUNT_MS);
      c.e = 1 - Math.pow(1 - k, 3);
      clock.textContent = fmt(S.left - c.delta * (1 - c.e));
      if (k < 1) requestAnimationFrame(step); else { COUNT = null; onHud(); }
    })(t0);
  }

  const shellClick = btn.onclick;
  btn.onclick = function () {
    // ⚠ Once per board, asked for on the 3D build: the shell sells time per
    // use without a limit. Refused before the shell sees the press, so nothing
    // is charged - and only where the shell would have sold it, so the locked,
    // walkthrough and not-playing answers stay the shell's own.
    if (S && S.timeBought && S.phase === "play" && has("booster_time") && !introWaitingOnBoard()) {
      say("Extra time is once per level."); buzz(8);
      return;
    }
    const before = S ? S.left : 0;
    const out = shellClick.apply(this, arguments);
    if (S && S.left > before + .5) {
      const delta = S.left - before, c = { s: S, delta, e: 0 };
      S.timeBought = true;
      COUNT = c; onHud();
      if (still.matches) land(delta);
      else fly(delta, () => { if (COUNT === c) land(delta); });
    }
    return out;
  };
})();
