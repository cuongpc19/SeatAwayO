p = "template.html"
s = open(p, encoding="utf-8").read()

# 1 viewBox unit == 1 rendered px, so the CSS font sizes are honest at any panel width
s = s.replace("  const fs = 1000 / W;                       // keep on-screen text size constant across viewBoxes",
              "  const fs = 1;                              // viewBox units are rendered px, so no text rescaling")
s = s.replace("  const W = opt.W || 1000, fs = 1000 / (opt.W || 1000),",
              "  const W = opt.W || 1000, fs = 1,")

# half-width panels: viewBox sized to the column they actually occupy
s = s.replace('  W: 470, h: 240, m: { l: 42, r: 16, t: 12, b: 30 },',
              '  W: 392, h: 208, m: { l: 40, r: 14, t: 12, b: 30 },')
s = s.replace('  W: 470, l: 46, r: 42, rowH: 17,',
              '  W: 392, l: 44, r: 40, rowH: 18,')

open(p, "w", encoding="utf-8").write(s)
data = open("lv/curve.json", encoding="utf-8").read()
open("level_curve.html", "w", encoding="utf-8").write(s.replace("/*__DATA__*/", data))
print("rebuilt")
