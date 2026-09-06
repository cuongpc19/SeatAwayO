import json, pathlib

ART = pathlib.Path("../art")
tpl = open("game_tpl.html", encoding="utf-8").read()
tpl = tpl.replace('cyan: "#2ace d6".replace(" ", "")', 'cyan: "#2aced6"')

pacing = open("lv/pacing.json", encoding="utf-8").read()
meta = open(ART / "atlas.json", encoding="utf-8").read()
b64 = open(ART / "atlas_b64.txt", encoding="utf-8").read().strip()

out = (tpl.replace("/*__PACING__*/", pacing)
          .replace("/*__META__*/", meta)
          .replace("/*__ATLAS__*/", b64))
open("bench_rush.html", "w", encoding="utf-8").write(out)
print("bench_rush.html %.0f KB" % (len(out) / 1024))
