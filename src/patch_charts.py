import io

p = "template.html"
s = open(p, encoding="utf-8").read()

NEW_LINE = r'''/* ---------- line chart ---------- */
function lineChart(host, opt) {
  const W = opt.W || 1000, H = opt.h || 300;
  const m = opt.m || { l: 46, r: 58, t: 14, b: 34 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const fs = 1000 / W;                       // keep on-screen text size constant across viewBoxes
  const svg = el("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": opt.aria });
  const xs = D.n, xmin = xs[0], xmax = xs[xs.length - 1];
  const ymax = opt.ymax, ymin = opt.ymin || 0;
  const X = v => m.l + (v - xmin) / (xmax - xmin) * iw;
  const Y = v => m.t + ih - (v - ymin) / (ymax - ymin) * ih;
  const px = v => (v / fs) + "px";
  const txt = (x, y, cls, anchor, str, size) => {
    const t = el("text", { x: x, y: y, class: cls, "text-anchor": anchor, style: "font-size:" + px(size) });
    t.textContent = str; svg.appendChild(t); return t;
  };

  (opt.yticks || []).forEach(t => {
    svg.appendChild(el("line", { x1: m.l, x2: m.l + iw, y1: Y(t), y2: Y(t), class: "gridline" }));
    txt(m.l - 8, Y(t) + 3.5 / fs, "axis-text", "end", opt.yfmt ? opt.yfmt(t) : t, 10.5);
  });
  (opt.xticks || []).forEach(t => txt(X(t), m.t + ih + 18 / fs, "axis-text", "middle", t, 10.5));
  txt(m.l, H - 3, "axis-title", "start", "Campaign level", 10);

  opt.series.forEach(s => {
    if (s.dots) {
      const g = el("g", { fill: s.color, opacity: s.op == null ? .3 : s.op });
      s.v.forEach((v, i) => g.appendChild(el("circle", { cx: X(xs[i]), cy: Y(v), r: (s.r || 1.4) / fs })));
      svg.appendChild(g); return;
    }
    if (s.area) {
      let d = "M " + X(xs[0]) + " " + Y(ymin);
      s.v.forEach((v, i) => d += " L " + X(xs[i]) + " " + Y(v));
      d += " L " + X(xs[xs.length - 1]) + " " + Y(ymin) + " Z";
      svg.appendChild(el("path", { d: d, fill: s.area, stroke: "none" }));
    }
    let d = "";
    s.v.forEach((v, i) => d += (i ? " L " : "M ") + X(xs[i]) + " " + Y(v));
    svg.appendChild(el("path", { d: d, fill: "none", stroke: s.color, "stroke-width": (s.w || 2) / fs,
      "stroke-linejoin": "round", "stroke-linecap": "round" }));
  });

  // direct labels, nudged apart when they collide
  const labs = opt.series.filter(s => s.label)
    .map(s => ({ s: s, y: Y(s.v[s.v.length - 1]) })).sort((a, b) => a.y - b.y);
  labs.forEach((L, i) => { if (i && L.y - labs[i - 1].y < 13 / fs) L.y = labs[i - 1].y + 13 / fs; });
  labs.forEach(L => {
    const t = el("text", { x: m.l + iw + 8, y: L.y + 4 / fs, class: "dlabel", fill: L.s.color,
      style: "font-size:" + px(11) });
    t.textContent = L.s.label; svg.appendChild(t);
  });

  const cross = el("line", { x1: 0, x2: 0, y1: m.t, y2: m.t + ih, stroke: "var(--ink-3)",
    "stroke-width": 1 / fs, "stroke-dasharray": (3 / fs) + " " + (3 / fs), opacity: 0 });
  svg.appendChild(cross);
  const marks = opt.series.filter(s => !s.dots);
  const dots = marks.map(s => {
    const c = el("circle", { r: 4.5 / fs, fill: s.color, stroke: "var(--panel)", "stroke-width": 2 / fs, opacity: 0 });
    svg.appendChild(c); return c;
  });
  host.appendChild(svg);
  const tip = document.createElement("div"); tip.className = "tip"; host.appendChild(tip);

  svg.addEventListener("pointermove", ev => {
    const r = svg.getBoundingClientRect();
    const mx = (ev.clientX - r.left) / r.width * W;
    let i = Math.round((mx - m.l) / iw * (xmax - xmin));
    i = Math.max(0, Math.min(xs.length - 1, i));
    cross.setAttribute("x1", X(xs[i])); cross.setAttribute("x2", X(xs[i])); cross.setAttribute("opacity", 1);
    marks.forEach((s, k) => {
      dots[k].setAttribute("cx", X(xs[i])); dots[k].setAttribute("cy", Y(s.v[i])); dots[k].setAttribute("opacity", 1);
    });
    tip.className = "tip on";
    tip.innerHTML = "<i>Level</i> <b>" + xs[i] + "</b><br>" + opt.tiplines.map(t =>
      "<i>" + t.name + "</i> <b>" + t.fmt(D[t.key][i]) + "</b>").join("<br>");
    tip.style.left = (X(xs[i]) / W * r.width) + "px";
    tip.style.top = (Y(marks[0].v[i]) / H * r.height - 12) + "px";
  });
  svg.addEventListener("pointerleave", () => {
    cross.setAttribute("opacity", 0); dots.forEach(d => d.setAttribute("opacity", 0)); tip.className = "tip";
  });
}

'''

NEW_CALLS = r'''const XT = [1, 100, 200, 300, 400, 500, 600];
const XT_S = [1, 200, 400, 600];

lineChart(document.getElementById("c-colours"), {
  h: 300, ymax: 8, ymin: 0, yticks: [0, 2, 4, 6, 8], xticks: XT,
  aria: "Colour count per campaign level with a 15-level rolling average",
  series: [
    { name: "colours", v: D.colours, color: "var(--s1)", dots: true, r: 1.6, op: .30 },
    { name: "15-level avg", v: roll(D.colours, 15), color: "var(--s1)", w: 2.5, label: "colours" }
  ],
  tiplines: [{ name: "colours", key: "colours", fmt: v => v }]
});

lineChart(document.getElementById("c-size"), {
  h: 320, ymax: 80, ymin: 0, yticks: [0, 20, 40, 60, 80], xticks: XT,
  aria: "Grid cells and occupied seats per campaign level",
  series: [
    { name: "grid cells", v: D.cells, color: "var(--s2)", dots: true, r: 1.6, op: .32 },
    { name: "grid cells", v: roll(D.cells, 15), color: "var(--s2)", w: 2.2, label: "cells" },
    { name: "seats", v: roll(D.slots, 15), color: "var(--s1)", w: 2.5, area: "var(--s1-fill)", label: "seats" }
  ],
  tiplines: [{ name: "cells", key: "cells", fmt: v => v }, { name: "seats", key: "slots", fmt: v => v }]
});

lineChart(document.getElementById("c-time"), {
  W: 470, h: 240, m: { l: 42, r: 16, t: 12, b: 30 },
  ymax: 360, ymin: 0, yticks: [0, 90, 180, 270, 360], xticks: XT_S,
  yfmt: v => v + "s",
  aria: "Time limit per campaign level with a 15-level rolling average",
  series: [
    { name: "time limit", v: D.time, color: "var(--s1)", dots: true, r: 1.5, op: .30 },
    { name: "avg", v: roll(D.time, 15), color: "var(--s1)", w: 2.2 }
  ],
  tiplines: [{ name: "time limit", key: "time", fmt: v => v + " s" }]
});

'''

a = s.index("/* ---------- line chart ---------- */")
b = s.index("const XT = [1, 100, 200, 300, 400, 500, 600];")
c = s.index("/* ---------- horizontal bars ---------- */")
s = s[:a] + NEW_LINE + NEW_CALLS + s[c:]

PAIRS = [
 ('function barChart(host, rows, opt) {\n  const W = 1000, rowH = opt.rowH || 26, m = { l: opt.l || 92, r: 60, t: 8, b: 26 };',
  'function barChart(host, rows, opt) {\n  const W = opt.W || 1000, fs = 1000 / (opt.W || 1000),\n        rowH = opt.rowH || 26, m = { l: opt.l || 92, r: opt.r || 60, t: 8, b: 26 };'),
 ('const tx = el("text", { x: X(t), y: H - 8, class: "axis-text", "text-anchor": "middle" });',
  'const tx = el("text", { x: X(t), y: H - 8, class: "axis-text", "text-anchor": "middle", style: "font-size:" + (10.5 / fs) + "px" });'),
 ('const lab = el("text", { x: m.l - 12, y: y + h / 2 + 4, class: "axis-text", "text-anchor": "end" });',
  'const lab = el("text", { x: m.l - 10, y: y + h / 2 + 4 / fs, class: "axis-text", "text-anchor": "end", style: "font-size:" + (10.5 / fs) + "px" });'),
 ('const val = el("text", { x: X(r.v) + 12, y: y + h / 2 + 4, class: "dlabel", fill: "var(--ink-2)" });',
  'const val = el("text", { x: X(r.v) + 10, y: y + h / 2 + 4 / fs, class: "dlabel", fill: "var(--ink-2)", style: "font-size:" + (11 / fs) + "px" });'),
 ('stroke: "var(--grid)", "stroke-width": 2, "stroke-linecap": "round" }));',
  'stroke: "var(--grid)", "stroke-width": 2 / fs, "stroke-linecap": "round" }));'),
 ('svg.appendChild(el("circle", { cx: X(r.v), cy: y + h / 2, r: 5, fill: "var(--s1)",\n        stroke: "var(--panel)", "stroke-width": 2 }));',
  'svg.appendChild(el("circle", { cx: X(r.v), cy: y + h / 2, r: 5 / fs, fill: "var(--s1)",\n        stroke: "var(--panel)", "stroke-width": 2 / fs }));'),
 ('barChart(document.getElementById("c-grid"), gridRows, {\n  l: 60, rowH: 30, xticks: [0, 100, 200, 300], aria: "Campaign levels by grid shape",',
  'barChart(document.getElementById("c-grid"), gridRows, {\n  W: 470, l: 46, r: 42, rowH: 17, xticks: [0, 100, 200, 300], aria: "Campaign levels by grid shape",'),
 ('<div class="legend"><span><i class="swatch" style="background:var(--s1)"></i>15-level average</span></div>',
  '<div class="legend"><span><i class="swatch" style="background:var(--s1)"></i>dots = each level &middot; line = 15-level average</span></div>'),
]
for x, y in PAIRS:
    if x not in s:
        raise SystemExit("MISS: " + x[:70])
    s = s.replace(x, y)

open(p, "w", encoding="utf-8").write(s)
data = open("lv/curve.json", encoding="utf-8").read()
open("level_curve.html", "w", encoding="utf-8").write(s.replace("/*__DATA__*/", data))
print("rebuilt level_curve.html")
