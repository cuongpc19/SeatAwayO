# -*- coding: utf-8 -*-
"""Does the 3D build talk to the host - and survive the host not being there?

  A. a live SDK      - the calls the submission form declares must fire
  B. a blocked SDK   - an adblocker must degrade the session, not end it
  C. ?muteAudio=true - the flag their QA opens the game with
"""
import sys
from _base import ok, open_game, end_lesson, run

# A Data Module that is a SEPARATE store from localStorage, so "saved to the
# host" cannot be passed by a write that only ever reached localStorage.
FAKE = """
window.__calls = []; window.__cloud = {};
window.CrazyGames = { SDK: {
  init: async () => { window.__calls.push("init"); },
  data: {
    getItem: k => { __calls.push("data.get:"+k); return __cloud[k] ?? null; },
    setItem: (k,v) => { __calls.push("data.set:"+k); __cloud[k] = v; },
    removeItem: k => { __calls.push("data.remove:"+k); delete __cloud[k]; },
  },
  game: {
    settings: { muteAudio: false },
    loadingStart: () => __calls.push("loadingStart"),
    loadingStop:  () => __calls.push("loadingStop"),
    gameplayStart:() => __calls.push("gameplayStart"),
    gameplayStop: () => __calls.push("gameplayStop"),
    happytime:    () => __calls.push("happytime"),
    addSettingsChangeListener: cb => { window.__setMute = cb; __calls.push("addSettingsChangeListener"); },
  },
}};
"""


def main(br):
    # ================================================ A. a live SDK
    pg, errs = open_game(br, "?dbg=1&reset=1&level=19&intro=jump", init=FAKE, block_sdk=False)
    calls = pg.evaluate("window.__calls")
    ok("init() is awaited", "init" in calls)
    ok("loading is bracketed, start before stop",
       "loadingStart" in calls and "loadingStop" in calls
       and calls.index("loadingStart") < calls.index("loadingStop"))
    ok("the mute listener is registered", "addSettingsChangeListener" in calls)
    ok("the save is READ from the Data Module", any(c.startswith("data.get:") for c in calls))
    ok("?reset wipes the HOST copy too", any(c.startswith("data.remove:") for c in calls))

    pg.evaluate("save.coins=4242; persist();")
    ok("progress is WRITTEN to the Data Module",
       any("4242" in str(v) for v in pg.evaluate("window.__cloud").values()))
    ok("...and to localStorage, so an offline session is not stale",
       "4242" in (pg.evaluate("localStorage.getItem('seatmatch3d.save.v1')") or ""))

    # ⚠ The walkthrough PAUSES the board, so dismiss it first, or every check
    # below measures a no-op rather than the bracket.
    ok("a walkthrough card stops gameplay", calls.count("gameplayStop") >= 1)
    end_lesson(pg)
    ok("dismissing the lesson resumes play", pg.evaluate("PAUSED") is False)

    def counts():
        c = pg.evaluate("window.__calls")
        return c.count("gameplayStart"), c.count("gameplayStop")

    s0, p0 = counts()
    pg.evaluate("openSettings()"); pg.wait_for_timeout(150)
    ok("opening settings stops gameplay", counts()[1] == p0 + 1)
    pg.evaluate("closeSettings()"); pg.wait_for_timeout(150)
    ok("closing it starts gameplay again", counts()[0] == s0 + 1)

    pg.evaluate("save.sound=true")
    ok("sound is on before the host mutes", pg.evaluate("!PLATFORM.hostMuted()"))
    pg.evaluate("CrazyGames.SDK.game.settings.muteAudio=true; __setMute({muteAudio:true})")
    ok("host mute silences it even with the in-game switch ON",
       pg.evaluate("PLATFORM.hostMuted()") and pg.evaluate("save.sound") is True)

    pg.evaluate("CrazyGames.SDK.game.settings.muteAudio=false; __setMute({muteAudio:false})")
    pg.evaluate("setPaused(false); S.seated=S.total; S.queue.length=0; S.queue2.length=0; finish(true)")
    pg.wait_for_timeout(250)
    ok("happytime() on a win", "happytime" in pg.evaluate("window.__calls"))
    ok("a finished board stops gameplay, and starts == stops",
       pg.evaluate("PAUSED") is True and counts()[0] == counts()[1], "%s" % (counts(),))
    ok("A: no page errors", not errs, "; ".join(errs[:3]))
    pg.close()

    # ================================================ B. the SDK never arrives
    pg, errs = open_game(br, "?dbg=1&reset=1&level=19&intro=jump")
    ok("B: it boots with the SDK blocked", pg.evaluate("DBG.cur") == 19)
    ok("B: a half-initialised SDK is NOT adopted", pg.evaluate("sdk") is None)
    pg.evaluate("save.coins=777; persist()")
    ok("B: progress still saves locally",
       "777" in (pg.evaluate("localStorage.getItem('seatmatch3d.save.v1')") or ""))
    ok("B: sound is not stuck off", pg.evaluate("!PLATFORM.hostMuted()"))
    ok("B: no page errors", not errs, "; ".join(errs[:3]))
    pg.close()

    # ================================================ C. their QA mute flag
    pg, errs = open_game(br, "?dbg=1&reset=1&level=19&muteAudio=true")
    ok("C: ?muteAudio=true silences it with no SDK at all", pg.evaluate("PLATFORM.hostMuted()"))
    ok("C: no page errors", not errs, "; ".join(errs[:3]))
    pg.close()


if __name__ == "__main__":
    sys.exit(1 if run(main) else 0)
