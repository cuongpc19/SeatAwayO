"""Build every page from one engine.

  ../level_player.html   the editor / study tool: every board, door controls,
                         guides, the gesture recorder
  ../game.html           the real game: one board at a time, saved progress,
                         a full room around the grid, a proper win card
  ../dist/index.html     the same game with the CrazyGames host door built in,
                         ready to drag into their upload box

    python build.py            editor + game
    python build.py crazy      the upload bundle, and the checks that go with it
"""
import json, pathlib, re, sys, time

ART = pathlib.Path("../art")
DATA = open("data_slots.js", encoding="utf-8").read()
ENGINE = open("engine.js", encoding="utf-8").read()

KEEP = ("w", "h", "time", "holes", "seats", "queue")   # what a board cannot do without


def levels_json():
    """The campaign boards, with any hand-edited ones laid over the top.

    lv/boards_campaign.json is what came out of the APK and stays that way; an
    edit exported from the level editor goes in lv/overrides.json instead, keyed
    by the board's id. So a board is reverted by deleting one entry, and the
    original is never a rebuild away from being lost."""
    boards = json.load(open("lv/boards_campaign.json", encoding="utf-8"))
    src = pathlib.Path("lv/overrides.json")
    if src.exists():
        at = {b["id"]: i for i, b in enumerate(boards)}
        for bid, b in json.loads(src.read_text(encoding="utf-8")).items():
            if bid not in at:
                sys.exit("overrides.json: no campaign board with id %r" % bid)
            missing = [k for k in KEEP if k not in b]
            if missing:
                sys.exit("overrides.json: %s is missing %s" % (bid, ", ".join(missing)))
            b["id"] = bid                       # the key is what decides which board
            boards[at[bid]] = b
            print("  override %-16s %d seats, %d passengers" % (bid, len(b["seats"]), len(b["queue"])))
    return json.dumps(boards, separators=(",", ":"))


LEVELS = levels_json()


def fill(html):
    return (html.replace("/*__LEVELS__*/", LEVELS)
                .replace("/*__META__*/", open(ART / "seat_atlas.json", encoding="utf-8").read())
                .replace("/*__ATLAS__*/", open(ART / "seat_atlas_b64.txt", encoding="utf-8").read().strip())
                .replace("/*__WMETA__*/", open(ART / "walk_atlas.json", encoding="utf-8").read())
                .replace("/*__WALK__*/", open(ART / "walk_atlas_b64.txt", encoding="utf-8").read().strip()))

def inline(path, mime):
    """A picture the published single-file build has to carry with it."""
    f = pathlib.Path(path)
    if not f.exists():
        return ""
    import base64
    return "data:%s;base64,%s" % (mime, base64.b64encode(f.read_bytes()).decode())


def movie_uri():
    """The cinema still."""
    return inline("../bg/movie1.jpg", "image/jpeg")


def cover_uri():
    """The home screen's cover art. Rendered by `art/home_cover.py`, which is
    slow enough not to belong in a build - the PNG it leaves behind is what is
    inlined here."""
    return inline("../art/home_cover.png", "image/png")


def live_config():
    """The numbers the shipped game runs on, read out of its own RemoteConfig so
    they cannot drift from the source by being retyped."""
    cfg = json.load(open("remote_config.json", encoding="utf-8"))
    g = cfg["parameterGroups"]
    num = lambda grp, key: float(g[grp]["parameters"][key]["defaultValue"]["value"])
    out = {
        "unlock": {k.replace("level_unlock_", ""): int(float(v["defaultValue"]["value"]))
                   for k, v in g["tutorial"]["parameters"].items()
                   if k.startswith("level_unlock")},
        "goldWin": int(num("gameplay", "gold_win_normal")),
        "streakGold": [[int(num("gameplay", "win_streak_gold_%d_level" % i)),
                        int(num("gameplay", "win_streak_gold_%d_value" % i))] for i in (1, 2, 3, 4)],
        "heartMax": int(num("features", "heart_max_stack")),
        "heartSecs": int(num("features", "heart_recv_time")),
        "heartPrice": int(num("features", "heart_refill_price")),
        "boosterTime": {"price": int(num("booster", "booster_time_price")),
                        "value": int(num("booster", "booster_time_value")),
                        "uses": int(num("booster", "uses_limit_booster_time"))},
        "boosterJump": {"price": int(num("booster", "booster_jump_price")),
                        "uses": int(num("booster", "uses_limit_booster_jump"))},
        "keepPlaying": {"price": int(num("gameplay", "keep_playing_price")),
                        "secs": int(num("gameplay", "keep_playing_time"))},
    }
    return json.dumps(out, separators=(",", ":"))


def build(head_file, shell_file, out, host="none"):
    """One page.

    `host` picks which platform door is compiled in, and it is a build-time
    choice rather than a runtime branch: CrazyGames bans third-party ad SDKs
    outright, so a build for one store must not be able to carry another's. See
    platform_base.js. The editor has no shell that talks to a host at all."""
    head = open(head_file, encoding="utf-8").read()
    shell = open(shell_file, encoding="utf-8").read()
    plat = ""
    if shell_file == "game_shell.js":
        plat = (open("platform_base.js", encoding="utf-8").read() + "\n"
                + open("platform_%s.js" % host, encoding="utf-8").read() + "\n")
    page = head + "\n<script>\n" + DATA + "\n" + ENGINE + "\n" + plat + shell + "\n</script>\n"
    page = (fill(page).replace("/*__MOVIE__*/", movie_uri())
                      .replace("/*__COVER__*/", cover_uri())
                      .replace("/*__BUILT__*/", time.strftime("%Y-%m-%d"))
                      .replace("/*__CONFIG__*/", live_config()))
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    open(out, "w", encoding="utf-8").write(page)
    print("%-24s %6.0f KB" % (out, len(page) / 1024))
    return page


# What a reviewer must never be handed, and what the bundle must never lack.
DEV_TOOLS = {"the JSON export panel": 'id="exp-json"',
             "the editor title": "Level Player",
             "the gesture trace panel": 'id="trace"'}


def check_crazy(page, out):
    """The limits a checklist would otherwise be trusted to remember. All cheap
    here and all expensive at the upload screen - and the dev-tool one is not a
    retry, it is a failed review."""
    size = len(page.encode("utf-8"))
    # Absolute paths break inside the host's iframe. Everything is inlined into
    # this one file, so any of these is a slip rather than a dependency.
    absolute = re.findall(r'(?:src|href)="/[^"]*"', page)
    strays = [n for n, needle in DEV_TOOLS.items() if needle in page]
    # Their SDK is fetched by URL at runtime and must not be bundled, so what is
    # checked is that the code which fetches it made it in.
    sdk = "sdk.crazygames.com" in page

    rows = [(size <= 20 * 1024 * 1024, "under 20 MB - keeps the mobile front page",
             "%.2f MB, over the 20 MB limit" % (size / 1048576)),
            (not absolute, "relative paths only",
             "absolute paths: " + " ".join(absolute[:4])),
            (sdk, "CrazyGames SDK wired", "no CrazyGames SDK in the bundle"),
            (not strays, "no dev tools", "dev tools rode in: " + ", ".join(strays))]

    print("")
    print('Bundle "crazy": %s - %.2f MB' % (out, size / 1048576))
    for ok, good, bad in rows:
        print("  %s %s" % ("OK  " if ok else "FAIL", good if ok else bad))
    if not all(ok for ok, _, _ in rows):
        sys.exit(1)
    print("")
    print("  Upload: Developer Portal -> your game -> Builds / Files")
    print("  Drag the CONTENTS of ../dist/ in. Do not zip it - archives are rejected.")


targets = sys.argv[1:] or ["editor", "game"]
if "editor" in targets:
    build("editor_head.html", "editor_shell.js", "../level_player.html")
if "game" in targets:
    page = build("game_head.html", "game_shell.js", "../game.html")
    # ⚠ Proved, not assumed: the plain web build must carry no host SDK at all.
    if "sdk.crazygames.com" in page:
        sys.exit("game.html carries a host SDK - the platform split has leaked")
if "crazy" in targets:
    out = "../dist/index.html"
    check_crazy(build("game_head.html", "game_shell.js", out, host="crazy"), out)
