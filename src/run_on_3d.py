# -*- coding: utf-8 -*-
"""Run the 2D game's own checks against the 3D build.

    python run_on_3d.py              # every check that opens the game page
    python run_on_3d.py test_jump    # just one

Each check is run twice: once as written, against ../index.html, for the
baseline, and once with only the page path and the save key swapped for the 3D
build's. A check that passes on the first and fails on the second is a place
the 3D build does not behave like the shipped game - which is the one thing it
promises.

⚠ Nothing else is changed in the copy. A check edited to make it pass here is a
check that no longer says anything about the shipped game.
"""
import pathlib, re, subprocess, sys, tempfile, time
# ⚠ A Windows console is cp1252, and a check's output can carry characters it
# cannot print - which crashed this runner mid-report rather than the check.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent
GAME_TESTS = ["test_clock", "test_game", "test_home", "test_jump", "test_l21", "test_meta",
              "test_queue", "test_rules", "test_stats", "test_toast", "test_tutorial",
              "test_walklock"]
want = sys.argv[1:] or GAME_TESTS
# ⚠ Checks the 3D build fails ON PURPOSE, because something they drive was taken
# out of it on request. Reported as such rather than as breakage, each with the
# reason - an unexplained entry here would be a way to hide a real regression.
BY_DESIGN = {
    "test_game": "clicks #h-levels, the home screen's level picker - hidden on the 3D build",
}


def run(src_text, label, name):
    tmp = HERE / ("_tmp_%s_%s.py" % (name, label))
    tmp.write_text(src_text, encoding="utf-8")
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, tmp.name], cwd=HERE, capture_output=True,
                           text=True, timeout=420, encoding="utf-8", errors="replace")
        out, code = (r.stdout + r.stderr), r.returncode
    except subprocess.TimeoutExpired:
        out, code = "TIMEOUT", 99
    finally:
        tmp.unlink(missing_ok=True)
    return code, out, time.time() - t0


rows = []
for name in want:
    text = (HERE / (name + ".py")).read_text(encoding="utf-8")
    three = (text.replace("../index.html", "../game3d/index.html")
                 .replace("seatmatch.save.v3", "seatmatch3d.save.v3"))
    c2, o2, t2 = run(text, "2d", name)
    c3, o3, t3 = run(three, "3d", name)
    # ⚠ Once more on a disagreement, both sides. Some of these checks race the
    # clock, and the first run of this file reported test_game as broken by the
    # 3D build when a second run showed the 2D build failing it line for line too.
    if (c2 == 0) != (c3 == 0):
        c2, o2, t2 = run(text, "2d", name)
        c3, o3, t3 = run(three, "3d", name)
    verdict = ("same" if (c2 == 0) == (c3 == 0) else
               ("by design" if name in BY_DESIGN else "3D BROKE IT") if c2 == 0 else "3D only passes")
    if verdict == "by design":
        print("    (%s)" % BY_DESIGN[name])
    rows.append((name, c2, c3, verdict))
    print("%-16s 2d=%-3s 3d=%-3s %-14s (%.0fs / %.0fs)" % (name, c2, c3, verdict, t2, t3), flush=True)
    if verdict == "3D BROKE IT":
        tail = "\n".join(o3.strip().splitlines()[-12:])
        print("    --- 3d output, last lines ---\n    " + tail.replace("\n", "\n    "), flush=True)

bad = [r for r in rows if r[3] == "3D BROKE IT"]
print("\n%d checks, %d where the 3D build differs from the shipped game" % (len(rows), len(bad)))
sys.exit(1 if bad else 0)
