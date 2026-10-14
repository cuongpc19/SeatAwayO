# -*- coding: utf-8 -*-
"""Every game3d check, in one command. Run from anywhere:

    python game3d/tests/run_all.py

Exits non-zero if any check failed, so it can sit in front of a deploy.

⚠ Builds first. A check run against a stale index.html passes or fails for the
previous change, not this one - and it looks exactly like a real result.
"""
import pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
build = subprocess.run([sys.executable, str(HERE.parent / "build.py")])
if build.returncode:
    sys.exit("build failed - nothing checked")

failed = []
for name in ("test_jump.py", "test_platform.py", "test_ui.py"):
    print("\n==================== " + name)
    r = subprocess.run([sys.executable, name], cwd=HERE)
    if r.returncode:
        failed.append(name)

print("\n" + ("ALL PASSED" if not failed else "FAILED: " + ", ".join(failed)))
sys.exit(1 if failed else 0)
