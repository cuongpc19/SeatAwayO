# -*- coding: utf-8 -*-
"""Shared bits for the game3d checks.

⚠ These live IN THE REPO. They used to live in a session scratchpad, which the
machine cleans, and every one of them vanished between two working days - the
night before a deploy. A check you cannot run again is a check you did once.

⚠ file://, not the dev server. three.js is inlined and the levels are inlined,
so the page needs nothing served; a check that needs `serve.py` running is a
check that fails for a reason that has nothing to do with the game.
"""
import pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = (ROOT / "index.html").as_uri()
OUT = []


def ok(name, cond, detail=""):
    OUT.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name + (("   " + detail) if detail else ""))
    return bool(cond)


def browser(pw):
    return pw.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])


def open_game(br, query, w=1280, h=720, init=None, block_sdk=True):
    """A booted board. ⚠ The host SDK is refused by default: its init() cannot
    finish outside the host, and a check that waits ~2.5s on every boot for a
    timeout is a check nobody runs."""
    pg = br.new_page(viewport={"width": w, "height": h})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console:" + m.text[:120])
          if m.type == "error" and "ERR_FAILED" not in m.text else None)
    if init:
        pg.add_init_script(init)
    if block_sdk:
        pg.route("**sdk.crazygames.com**", lambda r: r.abort())
    pg.goto(PAGE + query, wait_until="load")
    pg.wait_for_function("window.ready===true", timeout=45000)
    pg.wait_for_timeout(900)
    return pg, errs


def end_lesson(pg):
    pg.evaluate("if(typeof LESSON!=='undefined'&&LESSON) endLesson()")
    pg.wait_for_timeout(200)


# The screen spot of the first seat the front of a queue could be flown into.
JUMP_TARGET = """(want) => {
  const g = DBG.board;
  for (const b of g.seats) {
    const usable = jumpDoor(g, b) != null && freeSlot(b) >= 0;
    if (usable !== want) continue;
    const m = SEATMESH[b.id]; if (!m) continue;
    const v = new THREE.Vector3(); m.getWorldPosition(v); v.project(camera);
    const r = renderer.domElement.getBoundingClientRect();
    return { id: b.id, x: r.left + (v.x*.5+.5)*r.width, y: r.top + (-v.y*.5+.5)*r.height };
  }
  return null;
}"""


def summary():
    bad = OUT.count(False)
    print("\n%d checks, %d failed" % (len(OUT), bad))
    return bad


def run(main):
    with sync_playwright() as pw:
        br = browser(pw)
        try:
            main(br)
        finally:
            br.close()
    return summary()
