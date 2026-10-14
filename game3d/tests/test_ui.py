# -*- coding: utf-8 -*-
"""The camera and the UI parts that ../../UI_UX_RULES.md governs.

The camera checks are measurements, not looks: which way up the room lies, how
high the camera sits, how much of the frame the room takes, and that no corner
of it is outside the frame or under the HUD - at every frame size that has
ever produced a complaint.
"""
import sys
from _base import ok, open_game, end_lesson, run

FRAME = """() => {
  const L = limits(), v = new THREE.Vector3();
  let x0=9,x1=-9,y0=9,y1=-9;
  for (let i=0;i<8;i++){
    v.set(i&1?BOX.max.x:BOX.min.x, i&2?BOX.max.y:BOX.min.y, i&4?BOX.max.z:BOX.min.z);
    v.project(camera);
    x0=Math.min(x0,v.x); x1=Math.max(x1,v.x); y0=Math.min(y0,v.y); y1=Math.max(y1,v.y);
  }
  const c = camera.position.clone().sub(
    new THREE.Vector3((BOX.max.x+BOX.min.x)/2, 0.2, (BOX.max.z+BOX.min.z)/2));
  return { land: LAND,
           elev: Math.atan2(c.y, Math.hypot(c.x, c.z)) * 180 / Math.PI,
           w: (x1-x0)/2, h: (y1-y0)/2,
           inside: Math.max(-x0,x1) <= L.x+1e-3 && y1 <= L.hi+1e-3 && y0 >= L.lo-1e-3 };
}"""

# (label, w, h, level, expect landscape, expected elevation)
FRAMES = [("iPhone upright", 393, 740, 19, False, 50),
          ("narrow upright", 360, 800, 26, False, 50),
          ("smallest board upright", 393, 740, 1, False, 50),
          ("iPhone sideways", 852, 393, 19, True, 32),
          ("desktop", 1280, 720, 19, True, 32)]


def main(br):
    # ---- the camera: option A, chosen off rendered images
    for label, w, h, lvl, land, elev in FRAMES:
        pg, errs = open_game(br, "?reset=1&level=%d&intro=grey" % lvl, w, h)
        end_lesson(pg)
        f = pg.evaluate(FRAME)
        ok("%s: room lies %s" % (label, "landscape" if land else "upright"), f["land"] is land)
        ok("%s: camera at ~%d deg" % (label, elev), abs(f["elev"] - elev) < 1.5,
           "%.1f deg" % f["elev"])
        ok("%s: whole room in frame, clear of the HUD" % label, f["inside"],
           "%d%% wide, %d%% tall" % (f["w"] * 100, f["h"] * 100))
        if not land:
            # ⚠ The complaint this answers: upright, the room sat small in a sea
            # of empty screen. At 50 deg it measured 88% wide; anything under 80
            # means the fit or the angle has slid back.
            ok("%s: room spans most of the width" % label, f["w"] >= 0.80, "%d%%" % (f["w"] * 100))
        ok("%s: no forced-rotation prompt" % label, not pg.evaluate("!!document.getElementById('turn')"))
        ok("%s: no page errors" % label, not errs, "; ".join(errs[:2]))
        pg.close()

    # ---- the UI rules, on the phone held sideways
    pg, errs = open_game(br, "?dbg=1&reset=1&level=14&intro=jump", 852, 393)
    ok("6.7 every lesson offers Skip", pg.evaluate("!!document.querySelector('#coach-bub .skip')"))
    ok("2.12 no caption under a booster icon",
       pg.evaluate("getComputedStyle(document.querySelector('.boost'),'::after').content") in ("none", "normal"))
    ok("6.2 a lesson's free go shows as FREE",
       pg.evaluate("document.getElementById('b-jump-cost').textContent") == "FREE")
    ratio = pg.evaluate("""(()=>{const b=document.querySelector('.boost'),i=b.querySelector('.ico');
      return i.getBoundingClientRect().width/b.getBoundingClientRect().width;})()""")
    ok("2.13 the icon is 2/3 of the button", abs(ratio - 2 / 3) < 0.04, "%.2f" % ratio)
    pg.evaluate("document.querySelector('#coach-bub .skip').click()"); pg.wait_for_timeout(300)
    ok("6.7 Skip ends the lesson and counts as taught",
       pg.evaluate("LESSON===null") and pg.evaluate("save.seen.indexOf('jump')>=0"))

    pg.evaluate("save.coins=9999; S.left=0.2")
    pg.wait_for_function("document.getElementById('revive').classList.contains('on')", timeout=12000)
    wh = pg.evaluate("""(()=>{const a=document.getElementById('rv-go').getBoundingClientRect(),
      b=document.getElementById('rv-no').getBoundingClientRect();
      return [Math.round(a.width),Math.round(b.width),Math.round(a.height),Math.round(b.height)];})()""")
    ok("3.8 the revive decline is the same size as the yes", wh[0] == wh[1] and wh[2] == wh[3], "%s" % wh)
    ok("3.8 no corner cross", pg.evaluate("getComputedStyle(document.getElementById('rv-x')).display") == "none")
    ok("UI: no page errors", not errs, "; ".join(errs[:3]))
    pg.close()


if __name__ == "__main__":
    sys.exit(1 if run(main) else 0)
