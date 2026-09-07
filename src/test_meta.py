"""The progression layer: gold, streak, lives, boosters, and the level gates."""
import pathlib, json
from playwright.sync_api import sync_playwright
url = pathlib.Path("../index.html").resolve().as_uri()

bad = []


def check(ok, msg):
    if not ok:
        bad.append(msg)
    print("  %s %s" % ("ok  " if ok else "FAIL", msg))

with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof BOOTED !== 'undefined' && BOOTED", timeout=20000)

    print("the numbers the build runs on:", pg.evaluate("({gold: CF.goldWin, hearts: CF.heartMax, "
          "heartMins: CF.heartSecs/60, jump: CF.boosterJump.price, time: CF.boosterTime.price})"))

    # --- gates ---
    print("\nlevel gates:")
    for f in ("winstreak", "gray_seat", "booster_jump", "booster_time", "challenge"):
        r = pg.evaluate("f => ({at: unlockedAt(f), openAt1: (save.unlocked = 1, has(f)), "
                        "openAtGate: (save.unlocked = unlockedAt(f), has(f))})", f)
        print("   %-14s unlocks at %-4s  open at level 1: %-5s  at the gate: %s"
              % (f, r["at"], r["openAt1"], r["openAtGate"]))

    # --- boosters appear only when unlocked ---
    pg.evaluate("save.unlocked = 1; save.coins = 5000; startLevel(1)"); pg.wait_for_timeout(300)
    print("\nat level 1  : time button %s, jump button %s"
          % (pg.locator("#b-time").is_visible(), pg.locator("#b-jump").is_visible()))
    # ⚠ Every walkthrough marked seen first. Level 14 introduces the time
    # booster, and its card's dim layer swallows the click below - and the card
    # also hands out a free go, which would make the booster look free. How the
    # booster is introduced is test_tutorial's business; this is what it does.
    pg.evaluate("save.seenBoosters = ['grey','jump','twin','time']; persist(); "
                "save.unlocked = 14; startLevel(14)"); pg.wait_for_timeout(400)
    print("at level 14 : time button %s, jump button %s"
          % (pg.locator("#b-time").is_visible(), pg.locator("#b-jump").is_visible()))

    # --- the time booster ---
    before = pg.evaluate("({t: Math.round(S.left), g: save.coins})")
    pg.click("#b-time"); pg.wait_for_timeout(200)
    after = pg.evaluate("({t: Math.round(S.left), g: save.coins})")
    print("\ntime booster: clock %d -> %d (+%d)   gold %d -> %d (-%d)"
          % (before["t"], after["t"], after["t"] - before["t"],
             before["g"], after["g"], before["g"] - after["g"]))

    # --- the jump booster ---
    r = pg.evaluate("""(() => {
      const b = S.seats.find(x => !FIXED(x));
      const slide = placements(S, b).length;
      JUMP = true; const jump = placements(S, b).length; JUMP = false;
      return { slide, jump, id: b.id };
    })()""")
    print("jump booster: seat %d can slide to %d cells, can jump to %d"
          % (r["id"], r["slide"], r["jump"]))
    pg.click("#b-jump"); pg.wait_for_timeout(150)
    print("   armed: %s   charges: %d   gold: %d"
          % (pg.evaluate("JUMP"), pg.evaluate("save.jumps"), pg.evaluate("save.coins")))

    # --- a win pays, a loss costs a life ---
    pg.evaluate("save.unlocked = 20; save.streak = 4; startLevel(20); S.left = S.time*0.9; "
                "S.seated = S.total; S.queue.length = 0;")
    g0 = pg.evaluate("save.coins")
    pg.evaluate("finish(true)"); pg.wait_for_timeout(400)
    paid = pg.evaluate("save.coins") - g0
    print("\nwin with a 5-streak: gold +%d, streak now %d"
          % (paid, pg.evaluate("save.streak")))
    want = pg.evaluate("CF.goldWin") + 15      # + the streak bonus at five in a row
    check(paid == want, "a win on a 5-streak pays %d (expected %d)" % (paid, want))
    pg.evaluate("save.hearts = 3; startLevel(20); S.left = 0.01"); pg.wait_for_timeout(900)
    print("loss: lives %d, streak %d" % (pg.evaluate("save.hearts"), pg.evaluate("save.streak")))
    pg.evaluate("save.hearts = 0; save.heartAt = Date.now() + 900000; startLevel(21)")
    pg.wait_for_timeout(300)
    print("with no lives: home shown %s, message %r"
          % (pg.locator("#home").is_visible(), pg.locator("#hint").inner_text()))
    # What a win pays and how long a level lasts are this game's own numbers.
    # build.py lays them over the APK dumps rather than editing them, so both
    # are checked against the dumps: the tuning going missing and the dump
    # changing under it look different, and neither should pass unnoticed.
    print("\nthe tuning laid over the APK:")
    g = json.load(open("remote_config.json", encoding="utf-8"))
    g = g["parameterGroups"]["gameplay"]["parameters"]
    print("   gold per win   shipped %d, built %d"
          % (int(float(g["gold_win_normal"]["defaultValue"]["value"])), pg.evaluate("CF.goldWin")))

    boards = json.load(open("lv/boards_campaign.json", encoding="utf-8"))
    was = [b["time"] for b in boards if b.get("variant") == 0]
    now = pg.evaluate("LEVELS.filter(b => b.variant === 0).map(b => b.time)")
    check(len(was) == len(now), "600 campaign boards, %d in the file and %d in the build"
          % (len(was), len(now)))
    moved = sorted({b - a for a, b in zip(was, now)})
    # One value, or a board somewhere missed the extra - an override carries its
    # own `time`, which is exactly how one board could come out short.
    check(len(moved) == 1, "every clock moved by the same amount: %s" % moved)
    print("   every clock    +%ds  (shortest board %ds -> %ds)"
          % (moved[0], min(was), min(now)))

    print("\npage errors:", errs[:3] or "none")
    br.close()

print("\nerrors:", "; ".join(bad) if bad else "none")
assert not bad, bad
