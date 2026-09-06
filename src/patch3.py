p = "template.html"
s = open(p, encoding="utf-8").read()

# axis title was sitting on top of the first x tick - centre it and give it its own row
s = s.replace('  txt(m.l, H - 3, "axis-title", "start", "Campaign level", 10);',
              '  txt(m.l + iw / 2, H - 2, "axis-title", "middle", "Campaign level", 10);')
s = s.replace('  const m = opt.m || { l: 46, r: 58, t: 14, b: 34 };',
              '  const m = opt.m || { l: 46, r: 58, t: 14, b: 42 };')
s = s.replace('  W: 392, h: 208, m: { l: 40, r: 14, t: 12, b: 30 },',
              '  W: 392, h: 214, m: { l: 40, r: 14, t: 12, b: 38 },')

open(p, "w", encoding="utf-8").write(s)
data = open("lv/curve.json", encoding="utf-8").read()
open("level_curve.html", "w", encoding="utf-8").write(s.replace("/*__DATA__*/", data))
print("rebuilt")
