/* ---------------- the host door ----------------
   The one place anything host-specific goes through, ported from Marble Sort's
   `platform/base.ts`.

   ⚠ One shape, one implementation per target, chosen at BUILD time - never a
   runtime `if`. The host forbids third-party ad networks outright, so a single
   line of another store's SDK inside the uploaded build is a compliance failure.
   Picking the file in build.py makes that structural rather than something to
   keep remembering, and build.py proves it both ways: the upload bundle must
   carry the host's SDK URL and every other build must not.

   ⚠ The guard is pointed at the SDK URL, not at the brand name. An earlier
   version of this comment quoted the grep it was describing, so this shared
   file - which ships in every build - contained the very string the web build
   was checked for, and the check failed on its own documentation. Marble Sort
   hit the same thing and left the same note: keep the guard on code.

   `PLATFORM` is what the shell calls. What it has to answer:

     init()            bring the host SDK up. Never throws, never hangs.
     storage           getItem/setItem/removeItem, same shape as localStorage.
                       ⚠ Nothing may WRITE through this before init() resolves -
                       the host preloads the player's cloud save during init, so
                       an early write pushes a stale local copy over their real one.
     loadingStart/Stop bracket the asset load, so the host can show its spinner.
     gameplayStart/Stop ⚠ not telemetry. This is how the host knows when it may
                       interrupt with an ad. Emit from the pause flag, not from
                       each call site: the one site you miss is the one that breaks.
     happytime()       a flourish on the host page when the player does well.
     hostMuted()       ⚠ outranks the in-game sound switch. An in-game toggle must
                       not be able to bring audio back over a page the player
                       silenced.
     onHostMuteChange(cb)
*/

/** A storage that works when localStorage throws - private mode, sandboxed frame. */
const localStore = {
  getItem(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  setItem(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* progress just will not persist */ } },
  removeItem(k) { try { localStorage.removeItem(k); } catch (e) { /* nothing to do */ } },
};
