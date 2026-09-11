# -*- coding: utf-8 -*-
"""Inline the data and the shared rules into each prototype.

file:// refuses a fetch() of a sibling file, and a prototype you have to start a
server for is a prototype nobody opens - so everything is substituted in.

⚠ Two outputs per prototype, ONE template each. `<name>.html` opens off disk and
carries its own doctype and meta tags; the Artifact host supplies those itself
and rejects a file that brings its own, so `<name>_artifact.html` is the same
file with the HEAD block cut out.

⚠ rules.js is inlined into BOTH, never copied into either. Two copies of a rule
set means every fix has to be made twice, and the second one gets forgotten.
"""
import io, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
RULES = io.open(HERE / "rules.js", encoding="utf-8", newline="").read()
HEAD = re.compile(r"<!--HEAD:START-->.*?<!--HEAD:END-->\s*", re.S)

JOBS = [("honey_tpl.html", "boards.json", "honey"),
        ("seat3d_tpl.html", "boards_raw.json", "seat3d")]

DECL = re.compile(r"^(?:const|let)\s+([A-Za-z_$][\w$]*)", re.M)


def dup_decls(body):
    """Top-level names declared twice.

    Sharing rules.js between two templates has now produced three of these -
    CUR, the walker list, and TONE - and each one was a blank page with the whole
    script dead at parse time, which looks nothing like a naming problem. Only
    column-zero declarations count: anything indented is inside a function and
    has its own scope.
    """
    seen, twice = set(), []
    for m in DECL.finditer(body):
        name = m.group(1)
        if name in seen and name not in twice:
            twice.append(name)
        seen.add(name)
    return twice

for tpl_name, data_name, out in JOBS:
    tpl = io.open(HERE / tpl_name, encoding="utf-8", newline="").read()
    data = io.open(HERE / data_name, encoding="utf-8").read()
    assert tpl.count("/*__BOARDS__*/") == 1, tpl_name + ": board placeholder"
    assert tpl.count("/*__RULES__*/") == 1, tpl_name + ": rules placeholder"
    assert HEAD.search(tpl), tpl_name + ": HEAD markers"
    body = tpl.replace("/*__BOARDS__*/", data).replace("/*__RULES__*/", RULES)
    clash = dup_decls(body)
    assert not clash, ("%s: two top-level declarations of %s - inlining rules.js "
                       "into a template that already uses the name is a parse "
                       "error that kills the whole script"
                       % (tpl_name, ", ".join(clash)))
    for name, text in ((out + ".html", body), (out + "_artifact.html", HEAD.sub("", body))):
        io.open(HERE / name, "w", encoding="utf-8", newline="").write(text)
        print("%-26s %5.0f KB" % (name, len(text.encode("utf-8")) / 1024.0))
