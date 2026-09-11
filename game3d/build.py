# -*- coding: utf-8 -*-
"""Inline the campaign and the rules into one playable file.

⚠ One file, no fetch(). file:// refuses to fetch a sibling, and a build you have
to start a server for is one you cannot hand to somebody.

⚠ Duplicate top-level declarations are a parse error that kills the WHOLE script
and shows a blank page with no message. Inlining rules3d.js into a template that
happens to use one of its names has produced three of those already in this
project, so the check runs on every build.

⚠ three.js is inlined too, from a VENDORED copy rather than the cdnjs tag the
template carries. It is the one dependency that sits on the boot path: a font
that fails to load makes the game ugly, but a renderer that fails to load makes
it show "This device cannot run 3D graphics" and stop. 0.59 MB buys away every
way that request can fail - cdnjs down, cdnjs blocked, offline, a corporate
proxy, an upload host that forbids outbound requests.

⚠ This does NOT help a device with no working WebGL. Same error message, and a
completely different cause: there is no GPU context to be had, and no amount of
shipping the library changes that.
"""
import base64, io, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
tpl = io.open(HERE / "game_tpl.html", encoding="utf-8", newline="").read()
rules = io.open(HERE / "rules3d.js", encoding="utf-8", newline="").read()
levels = io.open(HERE / "levels.json", encoding="utf-8").read()

platform = io.open(HERE / "platform.js", encoding="utf-8", newline="").read()

for name, tok in (("levels", "/*__LEVELS__*/"), ("rules", "/*__RULES__*/"),
                  ("platform", "/*__PLATFORM__*/")):
    assert tpl.count(tok) == 1, "template is missing the %s placeholder" % name
page = (tpl.replace("/*__LEVELS__*/", levels)
           .replace("/*__RULES__*/", rules)
           .replace("/*__PLATFORM__*/", platform))

# ⚠ Proof the host door is actually in the bundle. The 2D build learned this the
# hard way: the submission form declares SDK muting and Data Module saves, and a
# build that quietly lost the platform layer makes both of those declarations
# false while looking perfectly healthy.
assert "sdk.crazygames.com" in page, "the host SDK URL is missing from the build"

# ⚠ The build stamp is what makes a telemetry row checkable. A dirty tree gets a
# "+" so a row can never claim to be a commit anybody could check out.
try:
    import subprocess
    # ⚠ shell=False. On Windows a list argv handed to a shell gets re-joined and
    # git never sees its arguments - which is how this first produced "nogit" on
    # a machine with a perfectly good repo under it.
    sh = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    stamp = (sh.stdout.strip() or "nogit") + ("+" if dirty.stdout.strip() else "")
except Exception:
    stamp = "nogit"
page = page.replace("/*__BUILD__*/", stamp)
print("build stamp:", stamp)
style = HERE / "redesign.css"
if style.exists():
    css = style.read_text(encoding="utf-8")
    assert css.count("HERO_DATA_URI") == 1, "hero must be embedded only once"
    hero = base64.b64encode((HERE / "home-hero-seat-fit.png").read_bytes()).decode("ascii")
    css = css.replace("HERO_DATA_URI", "data:image/png;base64," + hero)
    page = page.replace("</style>", css + "\n</style>", 1)

# ⚠ Before three.js goes in, not after. The duplicate check below is looking for
# collisions between rules3d.js and the template, and half a megabyte of
# minified library in the haystack only makes it slower and noisier.
DECL = re.compile(r"^(?:const|let|function)\s+([A-Za-z_$][\w$]*)", re.M)
seen, twice = set(), []
for m in DECL.finditer(page):
    n = m.group(1)
    if n in seen and n not in twice:
        twice.append(n)
    seen.add(n)
if twice:
    sys.exit("two top-level declarations of: " + ", ".join(twice))

# ⚠ Swap the CDN tag for the library itself. Asserted, not attempted: a silent
# miss here ships a game that boots only while cdnjs answers, and it would look
# perfectly fine on the machine that built it.
TAG = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/'
       '0.150.1/three.min.js"></script>')
assert page.count(TAG) == 1, "the three.js script tag moved or changed version"
three = io.open(HERE / "three.min.js", encoding="utf-8").read()
assert "</script" not in three.lower(), "the library would close its own tag"
page = page.replace(TAG, "<script>\n" + three + "\n</script>")
print("three.js inlined: %.2f MB" % (len(three.encode("utf-8")) / 1048576))

out = HERE / "index.html"
io.open(out, "w", encoding="utf-8", newline="").write(page)
levels_n = levels.count('"w":')
print("game3d/index.html  %.2f MB  %d levels" % (len(page.encode("utf-8")) / 1048576, levels_n))
