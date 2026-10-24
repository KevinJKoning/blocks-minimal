// Lines or dots over a shared x, on nice ticks, in the theme's series colours.
const COLORS = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)"];
RENDER.chart = (b) => {
  const W = 640, H = 300, R = 12, T = 12, B = 40;
  const xs = b.x.map(num), ys = b.series.flatMap((s) => s.y.map(num)).filter(Number.isFinite);
  const fx = xs.filter(Number.isFinite);
  if (!fx.length || !ys.length) return h("p", { class: "muted" }, "Nothing to plot.");
  let [x0, x1, y0, y1] = [Math.min(...fx), Math.max(...fx), Math.min(...ys), Math.max(...ys)];
  if (x0 === x1) { x0 -= 1; x1 += 1; }
  if (y0 === y1) { y0 -= 1; y1 += 1; }
  const pad = (y1 - y0) * 0.05; y0 -= pad; y1 += pad;
  const yTicks = ticks(y0, y1);
  // Room for the widest y tick (~6.5px a character at 11px) and the axis title beside it.
  const L = Math.max(52, 6.5 * Math.max(...yTicks.map((t) => fmt(t).length)) + (b.y_label ? 38 : 14));
  const X = (v) => L + ((v - x0) / (x1 - x0)) * (W - L - R), Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const grid = [
    ...yTicks.map((t) => [h("svg:line", { x1: L, x2: W - R, y1: Y(t), y2: Y(t), class: "grid" }),
      h("svg:text", { x: L - 6, y: Y(t) + 4, "text-anchor": "end" }, fmt(t))]),
    ...ticks(x0, x1).map((t) => h("svg:text", { x: X(t), y: H - B + 16, "text-anchor": "middle" }, fmt(t))),
    h("svg:line", { x1: L, x2: W - R, y1: H - B, y2: H - B, class: "axis" }),
    b.x_label && h("svg:text", { x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle", class: "label" }, b.x_label),
    b.y_label && h("svg:text", { x: 12, y: (T + H - B) / 2, "text-anchor": "middle", class: "label", transform: `rotate(-90 12 ${(T + H - B) / 2})` }, b.y_label),
  ];
  const marks = b.series.map((s, i) => {
    const pts = s.y.map((y, k) => [xs[k], num(y)]).filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y));
    const c = COLORS[i % COLORS.length];
    if (s.kind === "scatter") return h("svg:g", { fill: c }, pts.map(([x, y]) => h("svg:circle", { cx: X(x), cy: Y(y), r: 2.2 })));
    return h("svg:path", { d: pts.map(([x, y], k) => `${k ? "L" : "M"}${X(x).toFixed(1)},${Y(y).toFixed(1)}`).join(""), stroke: c, fill: "none", "stroke-width": 1.5 });
  });
  return h("figure", { class: "chart" }, b.title && h("figcaption", {}, b.title),
    h("svg:svg", { viewBox: `0 0 ${W} ${H}` }, grid, marks),
    b.series.length > 1 && h("p", { class: "legend" }, b.series.map((s, i) => h("span", {}, h("i", { style: `background:${COLORS[i % COLORS.length]}` }), s.name))));
};
