# -*- coding: utf-8 -*-
"""Does a finished level actually post a row, and does the policy open?

Level 1000 is the one build.py forces to a 5-second clock (TEST_CLOCK), so a
loss arrives on its own without anything having to be played - which is what
makes this runnable headless.

⚠ The POST is intercepted, not allowed through. This asserts the shape of what
the game would send; letting it fly would put a fake row in the live database
under whatever build stamp happened to be current, and level 1000 does not
exist in the campaign a player counts through.

    python test_stats.py
"""
import json, pathlib, re, sys
from playwright.sync_api import sync_playwright

URL = pathlib.Path("../index.html").resolve().as_uri()
READY = "typeof BOOTED !== 'undefined' && BOOTED"
RUNS = re.compile(r"firebasedatabase\.app/runs\.json")

posted, ga_hits, errs = [], [], []

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 420, "height": 860})
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    # ⚠ The routes below abort gtag on purpose, and an aborted request logs
    # "Failed to load resource: net::ERR_FAILED" with no URL to tell it apart
    # by. Counting that made this script fail itself. Only a real script error
    # is a failure here; a blocked fetch is what the test asked for.
    pg.on("console", lambda m: errs.append(m.text)
          if m.type == "error" and "ERR_FAILED" not in m.text else None)

    def grab(route):
        r = route.request
        try:
            posted.append(json.loads(r.post_data or "{}"))
        except ValueError:
            posted.append({"UNPARSEABLE": r.post_data})
        route.fulfill(status=200, content_type="application/json", body='{"name":"test"}')
    pg.route(RUNS, grab)
    # Counted, then blocked: whether gtag was ASKED for is the thing being
    # checked, and a real request to Google from a test is noise in the property.
    # ⚠ A regex, not a glob. `**/googletagmanager.com/**` looks right and matches
    # nothing - the host is `www.googletagmanager.com`, so the `**/` has already
    # eaten `https://` and the literal that follows never lines up. It reported
    # "gtag not requested" about a build that was requesting it perfectly.
    pg.route(re.compile(r"googletagmanager\.com/"),
             lambda r: (ga_hits.append(r.request.url), r.abort()))

    # ⚠ `intro=none` is not decoration. A fresh save on level 1000 owes every
    # feature walkthrough at once, and a walkthrough PAUSES the board - the
    # clock does not run, the loss never arrives, and the test times out on a
    # build that is working. The flag marks every feature seen.
    pg.goto(URL + "?level=1000&intro=none")
    pg.wait_for_function(READY, timeout=20000)
    print("booted           :", pg.evaluate("PLATFORM.name"), "| level", pg.evaluate("CUR"))
    print("gtag requested   :", len(ga_hits) > 0, "(on reaching a level, never at boot)")
    print("run armed        :", pg.evaluate("teleLvl"), "sig", pg.evaluate("teleSig"))

    # ⚠ The clock is started by hand. It does not run until the first thing
    # really happens on the board - a walker stepping off, or the player's first
    # seat - so a board nobody touches sits at 5 seconds forever and this waited
    # out its whole timeout on a build that was working. Draining `S.left` is
    # the real out-of-time path, just reached without playing.
    pg.evaluate("RUNNING = true; S.left = 0.3;")
    pg.wait_for_function("document.getElementById('card').classList.contains('on')"
                         " || document.getElementById('revive').classList.contains('on')",
                         timeout=20000)
    pg.wait_for_timeout(400)      # the POST goes out just before the card

    print("rows posted      :", len(posted))
    if posted:
        row = posted[-1]
        print("row              :", json.dumps(row, sort_keys=True)[:300])
        need = ["lvl", "sig", "result", "ms", "build", "t", "dev", "host", "from", "ga"]
        missing = [k for k in need if k not in row]
        print("fields present   :", "all" if not missing else "MISSING " + ", ".join(missing))
        print("marked as a test :", row.get("dev") == 1, "(dev=1, so --all is needed to count it)")

    # the policy, reached the way a reviewer reaches it
    pg.evaluate("openSettings()")
    pg.wait_for_timeout(200)
    pg.evaluate("document.getElementById('set-privacy').click()")
    pg.wait_for_timeout(200)
    shown = pg.evaluate("document.getElementById('privacy').classList.contains('on')")
    words = pg.evaluate("document.querySelector('.pv-body').innerText.trim().length")
    links = pg.evaluate("document.querySelectorAll('#privacy a[href]').length")
    print("privacy opens    :", shown, "|", words, "characters |", links, "outbound links (must be 0)")
    pg.evaluate("document.getElementById('pv-close').click()")
    pg.wait_for_timeout(150)
    print("privacy closes   :", not pg.evaluate("document.getElementById('privacy').classList.contains('on')"))

    br.close()

if errs:
    print("")
    print("console errors   :")
    for e in errs[:10]:
        print("   ", e)

ok = bool(posted) and not errs
print("")
print("OK" if ok else "FAIL")
sys.exit(0 if ok else 1)
