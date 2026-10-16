# -*- coding: utf-8 -*-
"""Superseded. The 3D game is now built from the shipped game's own sources:

    cd src && python build.py 3d

That target takes engine.js and game_shell.js unchanged and appends
src/render3d.js, which replaces only the drawing and the picking. Everything
else - rules, walkthroughs, the result card, boosters, sound, the host door -
is the code the 2D game runs.

⚠ This file used to write game3d/index.html too. Left working, one run of it
would overwrite the real 3D game with the old rewrite, which had drifted from
the shipped game in more than twenty places. So it refuses instead.
"""
import sys

sys.exit(__doc__)
