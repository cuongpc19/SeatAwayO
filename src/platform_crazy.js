/* CrazyGames. Built into the `crazy` target only - see build.py.

   ⚠ Everything here has to survive the SDK never arriving. An adblocker that
   blocks `crazygames-sdk-v3.js` does NOT fire `onerror` on the script tag, so
   waiting on it without a timeout parks that whole class of player on a dead
   screen forever. init() owns its own timeout and resolves either way; every
   method below no-ops when `sdk` is null. A session without cloud save is a
   degraded session; a session that never boots is a lost player. */

/** ⚠ Must stay under whatever the boot screen allows. The host preloads the
    player's cloud save during init(), and a splash that gives up first opens the
    game on local data, whose next write overwrites their real save with it. */
const INIT_TIMEOUT_MS = 2500;

/** Budget for fetching the script alone, inside INIT_TIMEOUT_MS. Needed ON TOP
    of onerror, not instead of it: an adblocked request can hang without firing
    either handler. Marble Sort measured this fetch from Vietnam at 7.9s cold and
    1.0-1.4s warm, so a cold player genuinely does lose the SDK here. */
const LOAD_TIMEOUT_MS = 2000;

/** Their script. ⚠ Fetched here at runtime, never a tag in the page head: a
    classic blocking <script src> stops the HTML parser, and a slow answer from
    this host then stops everything after it. The platform hosts the file and
    forbids bundling it, so it has to stay a fetch of their URL. */
const SDK_URL = "https://sdk.crazygames.com/crazygames-sdk-v3.js";

let sdk = null;
let muted = false, mutedSeeded = false;
const muteListeners = [];

function loadSdkScript() {
  return new Promise(resolve => {
    let settled = false;
    const done = ok => { if (!settled) { settled = true; resolve(ok); } };
    try {
      if (window.CrazyGames) return done(true);   // a host page that preloads it
      const el = document.createElement("script");
      el.src = SDK_URL; el.async = true;
      el.onload = () => done(true);
      el.onerror = () => done(false);
      document.head.appendChild(el);
      setTimeout(() => done(false), LOAD_TIMEOUT_MS);
    } catch (e) { done(false); }
  });
}

/** ⚠ `?muteAudio=true` is the flag their QA tests with. Without seeding from it
    the game only ever goes quiet when a live SDK says so - which is exactly what
    a reviewer opening the URL by hand does not have. Read lazily on first use. */
function seedMuted() {
  if (mutedSeeded) return;
  mutedSeeded = true;
  try { muted = new URLSearchParams(location.search).get("muteAudio") === "true"; }
  catch (e) { /* no location - leave it off */ }
}

function setMuted(v) {
  mutedSeeded = true;                     // an explicit SDK value outranks the query param
  if (v === muted) return;
  muted = v;
  for (const cb of muteListeners) { try { cb(v); } catch (e) { /* one bad listener must not stop the rest */ } }
}

/** Write to BOTH stores, read the host's first.

    ⚠ Writing to both is not belt and braces. A session where the SDK never
    arrived must still leave a FRESH local copy; writing only to the host leaves
    the local one frozen at whenever the SDK last worked, and that stale copy is
    what the next offline session shows the player. */
const dualStore = {
  getItem(k) {
    if (sdk) {
      try { const v = sdk.data.getItem(k); if (v != null) return v; }
      catch (e) { /* fall through to local */ }
    }
    return localStore.getItem(k);
  },
  setItem(k, v) {
    localStore.setItem(k, v);
    try { if (sdk) sdk.data.setItem(k, v); } catch (e) { /* the local write already happened */ }
  },
  removeItem(k) {
    localStore.removeItem(k);
    try { if (sdk) sdk.data.removeItem(k); } catch (e) { /* as above */ }
  },
};

/** ⚠ Read live from the SDK, with the listener only as a mirror.
    `SDK.game.settings.muteAudio` is the truth; a cached flag is one missed
    callback away from playing sound over a page the player silenced. */
function readMute() {
  seedMuted();
  try {
    const live = sdk && sdk.game.settings && sdk.game.settings.muteAudio;
    if (typeof live === "boolean") return live;
  } catch (e) { /* settings not exposed on this SDK build */ }
  return muted;
}

const PLATFORM = {
  name: "crazy",

  async init() {
    const start = Date.now();
    // ⚠ Fetch first, then poll. onload firing does not mean window.CrazyGames.SDK
    // is assigned yet on every build of their script.
    await loadSdkScript();
    const found = await new Promise(resolve => {
      const timer = setTimeout(() => resolve(null), INIT_TIMEOUT_MS);
      const tick = () => {
        const s = window.CrazyGames && window.CrazyGames.SDK;
        if (s) { clearTimeout(timer); resolve(s); }
        else if (Date.now() - start < INIT_TIMEOUT_MS) setTimeout(tick, 60);
      };
      tick();
    });
    if (!found) return;
    try {
      // ⚠ Awaited before anything else is touched - including the first storage
      // read, because this is where the player's cloud save is preloaded.
      await Promise.race([
        found.init(),
        new Promise(r => setTimeout(r, Math.max(0, INIT_TIMEOUT_MS - (Date.now() - start)))),
      ]);
      sdk = found;
    } catch (e) { sdk = null; }
    // ⚠ addSettingsChangeListener, not a window event. There is no volume event
    // to listen for; guessing one would make the submission form's "supports
    // muting through the SDK" box a false declaration.
    try {
      setMuted(!!(sdk && sdk.game.settings && sdk.game.settings.muteAudio));
      if (sdk && sdk.game.addSettingsChangeListener)
        sdk.game.addSettingsChangeListener(next => setMuted(!!(next && next.muteAudio)));
    } catch (e) { /* older SDK - the in-game toggle stays the only control */ }
  },

  storage: dualStore,

  loadingStart()  { try { if (sdk) sdk.game.loadingStart();  } catch (e) {} },
  loadingStop()   { try { if (sdk) sdk.game.loadingStop();   } catch (e) {} },
  gameplayStart() { try { if (sdk) sdk.game.gameplayStart(); } catch (e) {} },
  gameplayStop()  { try { if (sdk) sdk.game.gameplayStop();  } catch (e) {} },
  happytime()     { try { if (sdk) sdk.game.happytime();     } catch (e) {} },

  hostMuted: readMute,
  onHostMuteChange(cb) { muteListeners.push(cb); },
};
