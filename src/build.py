"""Build every page from one engine.

  ../level_player.html   the editor / study tool: every board, door controls,
                         guides, the gesture recorder
  ../index.html          the real game: one board at a time, saved progress,
                         a full room around the grid, a proper win card. The
                         root page, so a deep link reads /?level=1 - see the
                         address bar block in game_shell.js
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

# ---- where this game differs from the one it was decoded from --------------
# lv/boards_campaign.json and remote_config.json are the APK, verbatim, and they
# stay that way - so what the original did is always one file away rather than
# something to be reconstructed. Deliberate departures live here instead of
# being typed into either, which keeps the whole distance between the two games
# readable in one place, and printed on every build.
# ---- which campaign ships --------------------------------------------------
# 1.63.1 stopped shipping the binary LevelCfModel assets the first dump read, so
# the campaign now comes from src/convert_163.py. lv/boards_campaign.json is the
# older dump and stays on disk: it is the only thing lv/overrides.json was
# authored against, and an override is keyed by id alone, so pointing the same
# file at a campaign where Level_00001 is a different board would silently
# replace it with a board from the other game.
CAMPAIGN = "lv/boards_163.json"
LEGACY = "lv/boards_campaign.json"

# 0 while the clock is flat. PLAIN_SECONDS / HARD_SECONDS are written after
# this is added, so on the campaign that ships it does nothing but print a line
# that is not true. It still applies to LEGACY, which carries real times.
EXTRA_SECONDS = 0
GOLD_WIN = 100        # paid for a win, whatever the difficulty
# ⚠ Ours, not the APK's. Where a booster is taught is where it unlocks, so this
# table is also the teaching order. The APK opens jump at 8 and time at 14; the
# two are swapped here because time is the one that explains itself in a
# sentence - seconds go back on the clock - and jump is the one worth saving for
# a player who has met a board they cannot walk into. Add-line opens at 18 in
# the APK.
UNLOCKS = {"booster_time": 8, "booster_jump": 14, "booster_area": 16}

# ⚠ Ours. The APK charges 300, 600 and 1000; halved here, and only the three
# boosters - keep-playing and a heart refill are not boosters and keep their
# own prices. It belongs up here with the other departures rather than being
# typed into remote_config.json, which stays as dumped.
BOOSTER_PRICE = 0.5

# ⚠ Ours. The APK's in-level time booster hands back 15 seconds; 30 here, which
# is what its own pre-game version already gives. 15 off a flat 300 is barely a
# reprieve, and a booster the player cannot feel is one they stop pressing.
BOOSTER_TIME_VALUE = 30


# ---- which levels are marked hard ------------------------------------------
# The APK carried an int per board called `difficultLevel`, 0 to 2, and the game
# still reads it: it raises the warning card, puts the HARD / SUPER chip on the
# topbar, pays the clock bonus, and picks the party room (see PARTY in
# engine.js). 1.63.1 stopped shipping the field - convert_163.py has to write a
# flat 0 for every board - so on the campaign that ships, none of that fires.
#
# So it is worked out here instead, and this is the older dump's own spacing
# rather than a scheme of ours: over the 600 levels of lv/boards_campaign.json
# the rule below reproduces 118 of the 118 marked boards and both their grades,
# and predicts exactly one more (level 415, which that dump leaves blank and we
# do not bother to leave blank too).
#
# ⚠ Worked out from the level's number, so the numbering has to be the campaign
# the player counts through - the boards AFTER the duplicate arrangements are
# dropped, which is what `variant == 0` picks out. Applied to the raw file it
# would land on a different set of boards.
FIRST_HARD = 15           # nothing before this is graded

# ⚠ Temporary, and flat on purpose. The campaign that ships carries no clock of
# its own - nothing in the bundle gives its boards a time, and the estimate that
# stood in for one was wrong in kind rather than in value: the real game authors
# a number per level, anywhere from 30s to 429s, with no relation to how many
# people board. Two boards of capacity 26 and 13 both read 2:00 on the HUD. So
# rather than keep a fitted curve that is wrong everywhere, every board gets one
# of two numbers until the real ones turn up.
PLAIN_SECONDS = 300       # 5:00
HARD_SECONDS = 240        # 4:00, for both grades

def grade(n):
    """The difficulty of campaign level `n`, 1-based: 0 plain, 1 hard, 2 super.

    Two marks every ten levels, on the 5 and the 9, and nothing else. Levels
    ending in 0 are not marked, which is why "every multiple of five" is the
    wrong way to say it: over the shipped table, boards ending in 5 and in 9 are
    a special vehicle 134 times out of 135 each, and boards ending in 0 are one
    0 times out of 135. Averaging those two together is what hides the rhythm.

    The 9s take the longer vehicles - Train, Cadillac, Limo - and the 5s spread
    evenly across all of them, so the 9 is the heavier of the two marks.
    """
    if n < FIRST_HARD:
        return 0
    if n % 10 == 5:
        return 1
    if n % 10 == 9:
        return 2
    return 0


def tuning(shipped_gold):
    """Say out loud, every build, how far this is from the shipped numbers."""
    if EXTRA_SECONDS:
        print("  tuning    every clock +%ds" % EXTRA_SECONDS)
    if GOLD_WIN != shipped_gold:
        print("  tuning    gold per win %d -> %d" % (shipped_gold, GOLD_WIN))
    print("  tuning    unlocks " + ", ".join("%s %d" % (k.replace("booster_", ""), v)
                                             for k, v in UNLOCKS.items()))



def levels_json():
    """The campaign boards, with any hand-edited ones laid over the top.

    lv/boards_campaign.json is what came out of the APK and stays that way; an
    edit exported from the level editor goes in lv/overrides.json instead, keyed
    by the board's id. So a board is reverted by deleting one entry, and the
    original is never a rebuild away from being lost."""
    boards = json.load(open(CAMPAIGN, encoding="utf-8"))
    src = pathlib.Path("lv/overrides.json")
    if src.exists() and CAMPAIGN == LEGACY:
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
    # ⚠ After the overrides, not before. An override carries the board's whole
    # KEEP set including `time`, so a board edited in the level editor would
    # otherwise be the one board in the campaign that did not get the extra.
    for b in boards:
        b["time"] += EXTRA_SECONDS
    # The grading, over the campaign the player counts through - see grade().
    # Only where the campaign brought none of its own: the older dump has the
    # real thing on it, and a rule of ours must never be laid over that.
    if not any(b.get("diff") for b in boards):
        n = 0
        for b in boards:
            if b.get("variant"):
                continue
            n += 1
            b["diff"] = grade(n)
            b["time"] = HARD_SECONDS if b["diff"] else PLAIN_SECONDS
        marked = sum(1 for b in boards if b.get("diff"))
        print("  tuning    %d of %d levels graded hard, from the level number" % (marked, n))
        print("  tuning    clock flat: %ds plain, %ds hard" % (PLAIN_SECONDS, HARD_SECONDS))
    print("  campaign  %s, %d boards" % (CAMPAIGN, len(boards)))
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
    price = lambda key: int(round(num("booster", key) * BOOSTER_PRICE))
    out = {
        # ⚠ Ours, not the APK's, for booster_area. The shipped gate is 18; 16 is
        # a deliberate departure and belongs with the others up top, not typed
        # into remote_config.json, which stays as dumped.
        "unlock": dict({k.replace("level_unlock_", ""): int(float(v["defaultValue"]["value"]))
                        for k, v in g["tutorial"]["parameters"].items()
                        if k.startswith("level_unlock")},
                       **UNLOCKS),
        # ⚠ Ours, not the APK's. The shipped game pays 10 for a win at every
        # difficulty - gold_win_normal, _hard and _hardest are all 10 - and the
        # read is kept so that a re-dump which changed it would be noticed.
        "goldWin": GOLD_WIN,
        "streakGold": [[int(num("gameplay", "win_streak_gold_%d_level" % i)),
                        int(num("gameplay", "win_streak_gold_%d_value" % i))] for i in (1, 2, 3, 4)],
        "heartMax": int(num("features", "heart_max_stack")),
        "heartSecs": int(num("features", "heart_recv_time")),
        "heartPrice": int(num("features", "heart_refill_price")),
        "boosterTime": {"price": price("booster_time_price"),
                        "value": BOOSTER_TIME_VALUE,
                        "uses": int(num("booster", "uses_limit_booster_time"))},
        "boosterJump": {"price": price("booster_jump_price"),
                        "uses": int(num("booster", "uses_limit_booster_jump"))},
        "boosterArea": {"price": price("booster_area_price"),
                        "uses": int(num("booster", "uses_limit_booster_area"))},
        "keepPlaying": {"price": int(num("gameplay", "keep_playing_price")),
                        "secs": int(num("gameplay", "keep_playing_time"))},
    }
    tuning(int(num("gameplay", "gold_win_normal")))
    shipped_t = int(num("booster", "booster_time_value"))
    if BOOSTER_TIME_VALUE != shipped_t:
        print("  tuning    time booster %ds -> %ds" % (shipped_t, BOOSTER_TIME_VALUE))
    if BOOSTER_PRICE != 1:
        keys = ("booster_time_price", "booster_jump_price", "booster_area_price")
        print("  tuning    booster prices x%g: %s -> %s"
              % (BOOSTER_PRICE, [int(num("booster", k)) for k in keys],
                 [price(k) for k in keys]))
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
    page = build("game_head.html", "game_shell.js", "../index.html")
    # ⚠ Proved, not assumed: the plain web build must carry no host SDK at all.
    if "sdk.crazygames.com" in page:
        sys.exit("index.html carries a host SDK - the platform split has leaked")
if "crazy" in targets:
    out = "../dist/index.html"
    check_crazy(build("game_head.html", "game_shell.js", out, host="crazy"), out)
