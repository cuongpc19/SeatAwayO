"""Fetch the game's three faces once, so the CrazyGames bundle carries them.

    python fetch_fonts.py      writes fonts/*.woff2 and fonts/fonts.css

The web pages load Baloo 2, Lilita One and Nunito from Google Fonts. The
upload bundle carries its own copies in dist/fonts/, as Marble Sort's does: a
store build should not need a third party to draw its own title, and a player
behind a filter that blocks fonts.googleapis.com got the fallback faces - a
different game on the home screen.

Only the latin and latin-ext subsets: every word the game prints is English.
The files are what Google serves to a current Chrome (woff2, one variable file
where a family has one), so the faces are exactly the ones the web build gets.
All three are under the SIL Open Font License, which permits shipping them
inside a game; the licence travels in each file's own name table.

Run again only to change families or weights - the output is committed, and
build.py reads it rather than the network.
"""
import pathlib, re, urllib.request

CSS_URL = ("https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;700;800"
           "&family=Lilita+One&family=Nunito:wght@600;700;800&display=swap")
# ⚠ The user agent decides the format: an old or missing one is served TTF.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
KEEP = ("latin", "latin-ext")
OUT = pathlib.Path("fonts")


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read()


css = get(CSS_URL).decode()
OUT.mkdir(exist_ok=True)
blocks, saved = [], {}
for subset, body in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", css, re.S):
    if subset not in KEEP:
        continue
    url = re.search(r"url\((https://[^)]+\.woff2)\)", body).group(1)
    fam = re.search(r"font-family: '([^']+)'", body).group(1)
    if url not in saved:                 # a variable face serves one file for every weight
        name = "%s-%s-%d.woff2" % (fam.replace(" ", ""), subset, len(saved))
        (OUT / name).write_bytes(get(url))
        saved[url] = name
    blocks.append("/* %s */\n%s" % (subset, body.replace(url, "fonts/" + saved[url])))
(OUT / "fonts.css").write_text("\n".join(blocks) + "\n", encoding="utf-8")
total = sum((OUT / n).stat().st_size for n in saved.values())
print("%d faces, %d files, %.0f KB -> %s" % (len(blocks), len(saved), total / 1024, OUT))
