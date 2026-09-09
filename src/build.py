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
import json, pathlib, re, subprocess, sys, time

ART = pathlib.Path("../art")
DATA = open("data_slots.js", encoding="utf-8").read()
ENGINE = open("engine.js", encoding="utf-8").read()
# The two telemetry files. Compiled into the game only - see build(). They sit
# between the platform door and the shell, sharing one scope with both, so a
# name either of them already uses would be silently overridden; analytics.js
# and telemetry.js both carry that warning at the top.
ANALYTICS = open("analytics.js", encoding="utf-8").read()
TELEMETRY = open("telemetry.js", encoding="utf-8").read()
PRIVACY = open("privacy.html", encoding="utf-8").read()

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
PLAIN_SECONDS = 240       # 4:00
HARD_SECONDS = 180        # 3:00, for both grades

# ⚠ Ours. Lives are switched off. The APK gates every board on a heart, refills
# one every fifteen minutes and sells refills - a meter that decides when the
# player is allowed to play, which is a thing to tune against a live audience
# rather than something to carry while the levels themselves are still moving.
# Off means: a loss costs nothing, no board is ever refused, and the counter
# leaves the home screen rather than standing there showing a number that never
# changes. Every heart value below is still built, so this is one flag to flip.
LIVES = False

# ⚠ Ours. The APK sells its keep-playing at 900 gold for 30 seconds, which on a
# 300s board buys back a tenth of the level for six wins' worth of gold. Ours is
# a minute for 500: enough time to be worth the press, and priced so that two
# clean levels pay for one. The button it feeds is the only thing standing
# between running out of time and starting the board over.
KEEP_PLAYING_PRICE = 500
KEEP_PLAYING_SECS = 60

# ⚠ Ours, and only for testing: a level number -> its clock, overriding the two
# numbers above. Level 1000 is here so the run-out-of-time screen can be reached
# in five seconds instead of four minutes.
#
# ⚠ Never in a store bundle. A build for a host ships the campaign without this,
# so a five-second level cannot ride out to players on the strength of nobody
# having remembered to empty the dict - see levels_json(test=...) and the SHIP
# line in build(). It is in the web build, where the test links live.
TEST_CLOCK = {1000: 5}

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



def levels_json(test=True):
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
            if test and n in TEST_CLOCK: b["time"] = TEST_CLOCK[n]
        marked = sum(1 for b in boards if b.get("diff"))
        print("  tuning    %d of %d levels graded hard, from the level number" % (marked, n))
        print("  tuning    clock flat: %ds plain, %ds hard" % (PLAIN_SECONDS, HARD_SECONDS))
    # ⚠ Outside the block above. A campaign that arrives with its own difficulty
    # skips all of that, and the test clock used to go with it - so the one lever
    # for reaching the Time Out screen without playing four minutes disappeared
    # the moment the real data was wired in.
    if test and TEST_CLOCK:
        n = 0
        for b in boards:
            if b.get("variant"):
                continue
            n += 1
            if n in TEST_CLOCK:
                b["time"] = TEST_CLOCK[n]
                print("  TEST      level %d clock forced to %ds" % (n, TEST_CLOCK[n]))
    print("  campaign  %s, %d boards" % (CAMPAIGN, len(boards)))
    return json.dumps(boards, separators=(",", ":"))


LEVELS = levels_json()
# Built only when a host bundle is actually being made - it is the same 1497
# boards a second time, and the web build has no use for it.
SHIP_LEVELS = None


def fill(html, levels=None):
    return (html.replace("/*__LEVELS__*/", levels or LEVELS)
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


def build_stamp():
    """The commit every telemetry row is stamped with.

    ⚠ A dirty tree is stamped `<hash>+`, and says so on the build line. Marble
    Sort's note says to commit before building; the plus is there because that
    instruction gets forgotten and a row claiming to be a commit it was not
    played on is worse than one that admits it. `build` is the column reached
    for when two versions of a level disagree - see ANALYTICS.md."""
    def git(*a):
        try:
            r = subprocess.run(("git",) + a, capture_output=True, text=True, cwd="..")
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""
    h = git("rev-parse", "--short", "HEAD") or "nogit"
    # ⚠ `-uno`: modified TRACKED files make a build unreproducible, untracked
    # ones do not - nothing untracked is read by this script. Without it, a
    # scratch file left in the tree by another session marks every build dirty
    # for days, and a warning that is always on is a warning nobody reads.
    return h + ("+" if git("status", "--porcelain", "-uno") else "")


BUILD = build_stamp()


def privacy_page():
    """The hosted copy of the policy, for the CrazyGames submission form.

    ⚠ Written on every build from the same fragment the game inlines, so the two
    cannot drift. The form's copy is the one a reviewer reads; the in-game copy
    is the one a player reaches from Settings. Both have to be right, which is
    why neither is edited by hand - src/privacy.html is."""
    page = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Seat Match - Privacy Policy</title>
<style>
  :root { color-scheme: light; }
  body { margin: 0; padding: 40px 22px 80px; background: #f6f7fb; color: #22283a;
         font: 16px/1.65 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 44rem; margin: 0 auto; }
  h1 { font-size: 1.9rem; margin: 0 0 .2em; }
  h2 { font-size: 1.15rem; margin: 2em 0 .5em; color: #39415c; }
  .upd { color: #6b7288; margin: 0 0 2em; font-size: .92rem; }
  code { background: #e7eaf3; border-radius: 5px; padding: .1em .38em; font-size: .92em; }
  ul { padding-left: 1.3em; }
  li { margin: .3em 0; }
</style>
</head><body><main>
%s
</main></body></html>
""" % PRIVACY
    out = pathlib.Path("../public/privacy.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page.replace("/*__BUILT__*/", time.strftime("%Y-%m-%d")), encoding="utf-8")
    print("%-24s %6.0f KB" % (out.as_posix(), len(page) / 1024))


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
        "lives": LIVES,
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
        "keepPlaying": {"price": KEEP_PLAYING_PRICE, "secs": KEEP_PLAYING_SECS},
    }
    tuning(int(num("gameplay", "gold_win_normal")))
    if not LIVES:
        print("  tuning    lives off: a loss costs nothing and nothing is gated")
    shipped_k = (int(num("gameplay", "keep_playing_price")),
                 int(num("gameplay", "keep_playing_time")))
    if shipped_k != (KEEP_PLAYING_PRICE, KEEP_PLAYING_SECS):
        print("  tuning    revive %dg/%ds -> %dg/%ds"
              % (shipped_k + (KEEP_PLAYING_PRICE, KEEP_PLAYING_SECS)))
    shipped_t = int(num("booster", "booster_time_value"))
    if BOOSTER_TIME_VALUE != shipped_t:
        print("  tuning    time booster %ds -> %ds" % (shipped_t, BOOSTER_TIME_VALUE))
    if BOOSTER_PRICE != 1:
        keys = ("booster_time_price", "booster_jump_price", "booster_area_price")
        print("  tuning    booster prices x%g: %s -> %s"
              % (BOOSTER_PRICE, [int(num("booster", k)) for k in keys],
                 [price(k) for k in keys]))
    return json.dumps(out, separators=(",", ":"))


def build(head_file, shell_file, out, host="none", levels=None):
    """One page.

    `host` picks which platform door is compiled in, and it is a build-time
    choice rather than a runtime branch: CrazyGames bans third-party ad SDKs
    outright, so a build for one store must not be able to carry another's. See
    platform_base.js. The editor has no shell that talks to a host at all."""
    head = open(head_file, encoding="utf-8").read()
    shell = open(shell_file, encoding="utf-8").read()
    plat = tele = ""
    if shell_file == "game_shell.js":
        plat = (open("platform_base.js", encoding="utf-8").read() + "\n"
                + open("platform_%s.js" % host, encoding="utf-8").read() + "\n")
        # ⚠ The game only. The editor opens hundreds of boards a session and
        # never finishes one honestly, so telemetry from it would be noise at
        # best - and it has no PLATFORM to name as the source either.
        tele = ANALYTICS + "\n" + TELEMETRY + "\n"
    page = head + "\n<script>\n" + DATA + "\n" + ENGINE + "\n" + plat + tele + shell + "\n</script>\n"
    # ⚠ A bundle for a host carries the campaign without the test clocks. Built
    # here rather than filtered out afterwards, because "afterwards" is the step
    # that gets skipped - see TEST_CLOCK.
    global SHIP_LEVELS
    ship = levels                        # an explicit campaign wins over both
    if ship is None and host != "none":
        if SHIP_LEVELS is None: SHIP_LEVELS = levels_json(test=False)
        ship = SHIP_LEVELS
    page = (fill(page, ship).replace("/*__MOVIE__*/", movie_uri())
                      .replace("/*__COVER__*/", cover_uri())
                      .replace("/*__PRIVACY__*/", PRIVACY if tele else "")
                      .replace("/*__BUILD__*/", BUILD)
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
    # ⚠ Both of these have gone missing before by being switched off "just for a
    # test" and shipped that way. A build with no telemetry looks perfect and
    # reports nothing, and the first sign of it is an empty dashboard a week
    # later - which reads as a bug in the reading, not in the build.
    ga = "googletagmanager.com/gtag/js" in page
    runs = "firebasedatabase.app/runs.json" in page
    # The submission form demands a privacy policy and the reviewer follows the
    # in-game route to it. Shipping without it is a failed review, not a retry.
    priv = "Privacy Policy" in page
    # A placeholder that reached the bundle is a policy that names no one.
    holes = [s for s in ("PASTE_A_CONTACT_EMAIL", "PASTE_YOUR_UID") if s in page]
    # ⚠ A test clock that reached a store is a level nobody can finish, found by
    # a player rather than by a build.
    #
    # ⚠ Not a floor any more. This used to fail anything under the flat
    # HARD_SECONDS, which was right while every level ran on 240 or 180 and
    # wrong the moment the campaign started carrying the APK's own clocks -
    # those go down to 30s, and thirty real levels tripped it. A floor cannot
    # tell a fast level from a broken one. What it can tell is whether a
    # TEST_CLOCK entry is sitting at its own level, which is the thing that
    # must never ship.
    clocks = [int(n) for n in re.findall(r'"time":(\d+)', page)]
    quick = sorted(lv for lv, secs in TEST_CLOCK.items()
                   if lv <= len(clocks) and clocks[lv - 1] == secs)

    rows = [(size <= 20 * 1024 * 1024, "under 20 MB - keeps the mobile front page",
             "%.2f MB, over the 20 MB limit" % (size / 1048576)),
            (not absolute, "relative paths only",
             "absolute paths: " + " ".join(absolute[:4])),
            (sdk, "CrazyGames SDK wired", "no CrazyGames SDK in the bundle"),
            (ga, "Google Analytics wired", "no gtag.js loader in the bundle"),
            (runs, "telemetry endpoint wired", "no Realtime Database URL in the bundle"),
            (priv, "privacy policy carried", "no privacy policy in the bundle"),
            (not holes, "no unfilled placeholders",
             "placeholders shipped: " + ", ".join(holes)),
            (clocks and not quick, "no test clocks - none of %s shipped" % sorted(TEST_CLOCK),
             "test clocks shipped at levels: %s" % quick),
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
# ⚠ Printed, not silent. `+` means the tree was dirty and every telemetry row
# from this build will name the PREVIOUS commit as the one it was played on.
print("  build     %s%s" % (BUILD, "   <- dirty tree; commit before a build you will read numbers from"
                                    if BUILD.endswith("+") else ""))
if "editor" in targets:
    build("editor_head.html", "editor_shell.js", "../level_player.html")
if "game" in targets:
    privacy_page()          # the hosted copy, from the same fragment the game inlines
    page = build("game_head.html", "game_shell.js", "../index.html")
    # ⚠ Proved, not assumed: the plain web build must carry no host SDK at all.
    if "sdk.crazygames.com" in page:
        sys.exit("index.html carries a host SDK - the platform split has leaked")
if "plana" in targets:
    """The APK's own ladder, side by side with ours so the two can be played
    against each other rather than argued about.

    lv/boards_163a.json is built by `LADDER=timedata python convert_163.py`:
    2085 levels in the order TimeData gives, each carrying the seconds TimeData
    gives, and marked Hard / VeryHard by the APK's own level number. Every board
    already arrives with `diff` set, so the flat 240/180 below is skipped by the
    guard that exists for exactly this - a rule of ours must never be laid over
    the real thing.

    ⚠ Its own save key. Both pages are served from one origin, and localStorage
    is keyed by origin: sharing a key would have the two ladders overwriting
    each other's progress, and `unlocked` means a different board in each.
    """
    keep = CAMPAIGN
    globals()["CAMPAIGN"] = "lv/boards_163a.json"
    apk_levels = levels_json(test=False)          # ⚠ after CAMPAIGN moves, not before
    globals()["CAMPAIGN"] = keep
    page = build("game_head.html", "game_shell.js", "../a.html", levels=apk_levels)
    # ⚠ Every occurrence, not just the declaration. The privacy page names the
    # storage key in prose, and a policy that names the wrong key is wrong in
    # the one place a reader would check it.
    swapped = page.replace("seatmatch.save.v3", "seatmatch.apkladder.save.v1")
    if "seatmatch.save.v3" in swapped or swapped == page:
        sys.exit("a.html: the save key survived the swap - it would share progress with the main build")
    open("../a.html", "w", encoding="utf-8").write(swapped)
    print("  plana     ../a.html - APK ladder, own save key")

if "crazy" in targets:
    out = "../dist/index.html"
    check_crazy(build("game_head.html", "game_shell.js", out, host="crazy"), out)
