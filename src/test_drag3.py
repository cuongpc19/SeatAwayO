"""Press a seat, drag it, release. Then press a different seat - the first one
   must be completely let go of."""
import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
TO_CLIENT = ("([c,r]) => { const [x,y] = P(cellW(c), 0, cellZ(r));"
             " const rect = cv.getBoundingClientRect();"
             " return [rect.left + x/cv.width*rect.width, rect.top + y/cv.height*rect.height]; }")
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=25000)
    pg.evaluate("load(45)")
    pg.wait_for_function("S && !S.boarding && S.anim.length === 0", timeout=20000)
    pg.wait_for_timeout(300)

    movable = pg.evaluate("S.seats.map((b,i)=>[i, placements(S,b).length]).filter(x=>x[1]>0).map(x=>x[0])")
    s1, s2 = movable[0], movable[1]
    print("movable seats:", len(movable), "| using", s1, "and", s2)

    def press(sid):
        pos = pg.evaluate(TO_CLIENT, pg.evaluate("s=>[S.seats[s].c,S.seats[s].r]", sid))
        pg.mouse.move(pos[0], pos[1]); pg.mouse.down()
        return pos

    # 1. the seat tracks the pointer
    pos = press(s1)
    pg.mouse.move(pos[0] - 60, pos[1] + 34, steps=4); pg.wait_for_timeout(80)
    st = pg.evaluate("HELD && {seat: HELD.seat.id, dx:+HELD.dx.toFixed(2), dz:+HELD.dz.toFixed(2), moved: HELD.moved}")
    print("while held:", st)
    pg.locator(".stage").screenshot(path="d3_hold.png")
    pg.mouse.up(); pg.wait_for_timeout(150)
    print("after release: HELD =", pg.evaluate("HELD"), "| sel =", pg.evaluate("S.sel && S.sel.id"))

    # 2. pressing a different seat must not leave the first one held
    press(s2)
    st2 = pg.evaluate("HELD && HELD.seat.id")
    print("pressed seat", s2, "-> HELD.seat =", st2, "| sel =", pg.evaluate("S.sel && S.sel.id"))
    pg.mouse.up(); pg.wait_for_timeout(100)
    print("released      -> HELD =", pg.evaluate("HELD"), "| sel =", pg.evaluate("S.sel && S.sel.id"))

    # 3. a plain click leaves nothing behind
    press(s1); pg.mouse.up(); pg.wait_for_timeout(100)
    print("plain click   -> HELD =", pg.evaluate("HELD"), "| sel =", pg.evaluate("S.sel && S.sel.id"))
    pg.locator(".stage").screenshot(path="d3_idle.png")
    print("errors:", errs[:3] or "none")
    br.close()
a = Image.open("d3_hold.png").convert("RGB"); b = Image.open("d3_idle.png").convert("RGB")
w = 420
ta = a.resize((w, int(a.height*w/a.width))); tb = b.resize((w, int(b.height*w/b.width)))
sh = Image.new("RGB", (w*2, ta.height), (232,236,240)); sh.paste(ta,(0,0)); sh.paste(tb,(w,0))
sh.save("drag3_sheet.png"); print(sh.size)
