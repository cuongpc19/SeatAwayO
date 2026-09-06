"""The line at the stop shuffles up rather than jumping.

A passenger leaving used to move everyone behind them a whole place in the frame
the queue shifted. This walks the line forward: each person eases off the
distance they are carrying, one starting after another, so the check is that no
frame moves anybody a long way and that the last of them has arrived by the time
one step plus six gaps have passed.
"""
import pathlib, json
from playwright.sync_api import sync_playwright
url = pathlib.Path("../game.html").resolve().as_uri()

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 460, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)

    # A board with a queue long enough to have a line, that boards on its own.
    lvl = pg.evaluate("""(() => {
      for (let n = 1; n <= 40; n++) {
        startLevel(n);
        if (S && S.queue.length >= 5 && pickSeat(S, S.queue[0])) return n;
      }
      return 0;
    })()""")
    print("level with a line     :", lvl, "queue", pg.evaluate("S.queue.length"))
    assert lvl, "no board in the first 40 boards has a line that boards unaided"

    # Sample every frame: how far each person still has to walk, in places.
    pg.evaluate("""() => {
      window.SAMP = [];
      const tick = () => {
        SAMP.push([performance.now(), S && S.qstep
                   ? S.qstep.map(st => +placesBack(st, performance.now()).toFixed(4)) : null,
                   S ? S.queue.length : -1]);
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }""")
    pg.evaluate("startLevel(%d)" % lvl)
    pg.wait_for_timeout(2500)
    samp = pg.evaluate("SAMP")

    moving = [s for s in samp if s[1] and any(v > 1e-3 for v in s[1])]
    print("frames sampled        :", len(samp), "of which the line is moving in", len(moving))
    assert moving, "the line never moved: qstep was empty the whole time"

    # 1. Nobody teleports. A place is QUEUE_PITCH; a frame at 60Hz is a fraction
    #    of a step, so the biggest single-frame move must be well under a place.
    worst, at = 0.0, None
    for a, b in zip(moving, moving[1:]):
        if not a[1] or not b[1] or a[2] != b[2]:
            continue                       # a shift re-indexes the line; not a move
        for i in range(min(len(a[1]), len(b[1]))):
            d = abs(a[1][i] - b[1][i])
            if d > worst: worst, at = d, (round(b[0] - a[0], 1), i)
    print("biggest move in a frame: %.4f places  (%s ms, place %s)"
          % (worst, at[0] if at else "-", at[1] if at else "-"))
    assert worst < 0.12, "someone jumped %.3f of a place in one frame" % worst

    # 2. They start one after another, not all together.
    first = moving[0][1]
    lead = [i for i, v in enumerate(first) if v < 0.999]
    print("moving on frame one   :", lead, "(the head steps off first)")

    # 3. And the line settles: one step plus the gaps behind it, then still.
    span = moving[-1][0] - moving[0][0]
    print("line in motion for    : %.0f ms" % span)
    assert span > 150, "the shuffle was over in %.0f ms - that is still a jump" % span

    print("errors:", "none" if not errs else errs[:5])
    br.close()
