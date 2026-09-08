# -*- coding: utf-8 -*-
"""Read the gameplay rows out of the Realtime Database and tally them.

    python scripts/pull_runs.py              tally only, writes nothing
    python scripts/pull_runs.py --write      merge new rows into playlog.jsonl
    python scripts/pull_runs.py --all        count test games too
    python scripts/pull_runs.py --level 15   everything about one level

⚠ No credentials to set up, and none to keep. This shells out to the Firebase
CLI, which is already logged in and reads as project OWNER - and an owner
bypasses database.rules.json completely. That is why the rules need no read
account for this path, and why public/stats.html, which is a browser and gets no
such privilege, needs the uid allowance instead.

⚠ The database URL is NOT repeated here. The CLI is pointed at the instance by
name, so the region - which is baked into the URL that src/telemetry.js ships -
lives in exactly one place that a browser ever sees. If the instance is ever
recreated in another region, telemetry.js is the file to change; this one only
needs the name below.

On which questions these rows answer and which belong to Firebase Analytics
instead, see ANALYTICS.md §0. The short version: winrate comes from here,
because every row carries `sig` and GA cannot tell one revision of a board from
another.
"""
import argparse, collections, json, os, pathlib, subprocess, sys

INSTANCE = "seatmatch-292b3-default-rtdb"
PROJECT = "seatmatch-292b3"
ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = ROOT / "playlog.jsonl"


def fetch(limit):
    """Every row, as {push key: row}. Via the CLI so no secret is needed."""
    cmd = ["npx", "--no-install", "firebase-tools", "database:get", "/runs",
           "--project", PROJECT, "--instance", INSTANCE,
           "--order-by-key", "--limit-to-last", str(limit)]
    r = subprocess.run(cmd, capture_output=True, text=True, shell=(os.name == "nt"))
    if r.returncode != 0:
        sys.exit("firebase database:get failed:\n" + (r.stderr or r.stdout))
    body = (r.stdout or "").strip()
    if not body or body == "null":
        return {}
    try:
        got = json.loads(body)
    except ValueError:
        sys.exit("could not parse the CLI's answer:\n" + body[:400])
    return got or {}


def load_log():
    """What has already been merged, keyed by push id, so a re-run is free."""
    if not LOG.exists():
        return {}
    out = {}
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("_k"):
            out[row["_k"]] = row
    return out


def tally(rows, args):
    if not rows:
        print("no rows yet.")
        return
    wins = sum(1 for r in rows if r.get("result") == "win")
    ga = sum(1 for r in rows if r.get("ga"))
    print("games   %d   wins %d   winrate %s"
          % (len(rows), wins, pct(wins, len(rows))))
    # ⚠ Step 1 of "something looks broken": all zeros here means gtag.js is
    # being blocked, not that the tracking code is wrong. No amount of GA work
    # fixes that - read the numbers from this database instead. ANALYTICS.md §6.
    print("gtag    %d of %d rows loaded it (%s)" % (ga, len(rows), pct(ga, len(rows))))
    builds = collections.Counter(r.get("build", "?") for r in rows)
    print("builds  " + ", ".join("%s x%d" % (b, n) for b, n in builds.most_common(6)))
    hosts = collections.Counter(r.get("host", "?") for r in rows)
    print("hosts   " + ", ".join("%s x%d" % (h, n) for h, n in hosts.most_common(6)))

    by = collections.defaultdict(lambda: {"n": 0, "w": 0, "ms": 0, "mv": 0,
                                          "sig": set(), "boost": 0})
    for r in rows:
        e = by[r.get("lvl", 0)]
        e["n"] += 1
        e["w"] += 1 if r.get("result") == "win" else 0
        e["ms"] += r.get("ms", 0)
        e["mv"] += r.get("moves", 0)
        e["sig"].add(r.get("sig"))
        if r.get("used"):
            e["boost"] += 1

    print("")
    print("%-7s %6s %6s %8s %8s %7s %7s %s"
          % ("level", "games", "wins", "winrate", "avg s", "moves", "boost", "boards"))
    for lvl in sorted(by):
        e = by[lvl]
        flag = "  <- RETUNED, do not average" if len(e["sig"]) > 1 else ""
        print("%-7d %6d %6d %8s %8.0f %7.1f %7d %6d%s"
              % (lvl, e["n"], e["w"], pct(e["w"], e["n"]), e["ms"] / e["n"] / 1000.0,
                 e["mv"] / float(e["n"]), e["boost"], len(e["sig"]), flag))

    # ⚠ The whole reason `sig` is on every row. A level with two fingerprints
    # has been retuned underneath its own number, and averaging the two together
    # produces a confident figure for a board that no longer exists. This is the
    # mistake that wrecked a calibration pass on the sibling project.
    mixed = [l for l in sorted(by) if len(by[l]["sig"]) > 1]
    if mixed:
        print("")
        print("⚠ %d level(s) carry more than one board fingerprint: %s"
              % (len(mixed), ", ".join(str(l) for l in mixed[:20])))
        print("  Their rows are not one population. Filter by build before reading them.")


def pct(a, b):
    return ("%.0f%%" % (100.0 * a / b)) if b else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="merge new rows into playlog.jsonl")
    ap.add_argument("--all", action="store_true", help="count test games too")
    ap.add_argument("--level", type=int, help="only this level")
    ap.add_argument("--build", help="only this build stamp")
    ap.add_argument("--limit", type=int, default=40000)
    args = ap.parse_args()

    got = fetch(args.limit)
    print("read    %d rows from %s" % (len(got), INSTANCE))

    rows = []
    for k, r in got.items():
        if not isinstance(r, dict):
            continue
        r = dict(r, _k=k)
        rows.append(r)
    rows.sort(key=lambda r: r.get("t", 0))

    if args.write:
        # ⚠ Merged by push id, never appended blind: the script is meant to be
        # safe to run twice in a row.
        have = load_log()
        fresh = [r for r in rows if r["_k"] not in have]
        with LOG.open("a", encoding="utf-8") as f:
            for r in fresh:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
        print("merged  %d new rows into %s (%d already there)"
              % (len(fresh), LOG.name, len(have)))

    # Filtering on READ rather than blocking on write is deliberate: a blocked
    # row is gone forever, a filtered one is still there when the question
    # changes. --all is what counts our own test games back in.
    kept = [r for r in rows if args.all or not r.get("dev")]
    if len(kept) != len(rows):
        print("skipped %d test games (--all counts them)" % (len(rows) - len(kept)))
    if args.level:
        kept = [r for r in kept if r.get("lvl") == args.level]
    if args.build:
        kept = [r for r in kept if r.get("build") == args.build]
    print("")
    tally(kept, args)


if __name__ == "__main__":
    main()
