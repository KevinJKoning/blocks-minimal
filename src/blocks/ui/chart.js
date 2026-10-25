// Lines, steps or dots over a shared x (or each series' own), on nice ticks, in the theme's
// series colours, with dashed reference lines. A series' band (lows, highs) is shaded beneath
// a line, and drawn as an error bar on each of its dots. A missing point breaks a line and its
// band. A log axis places log10 of its values, on ticks at powers of ten.
// The unbroken runs of rows [x, ...values]: a row with a value missing ends one.
function runs(rows) {
  const out = [];
  let open = false;
  for (const r of rows) {
    if (r.every(Number.isFinite)) { if (!open) out.push([]); out.at(-1).push(r); open = true; }
    else open = false;
  }
  return out;
}
RENDER.chart = (b) => {
  const W = 640, H = 300, R = 12, T = 12, B = 40;
  // Values as placed on each axis: log10 on a log one.
  const ax = b.x_scale === "log" ? (v) => Math.log10(num(v)) : num, ay = b.y_scale === "log" ? (v) => Math.log10(num(v)) : num;
  const sx = b.series.map((s) => (s.x || b.x).map(ax));
  const ref = (ls, at) => (ls || []).map((l) => ({ ...l, at: at(l.value) })).filter((l) => Number.isFinite(l.at));
  const xl = ref(b.x_lines, ax), yl = ref(b.y_lines, ay);
  const ys = [...b.series.flatMap((s) => [s.y, ...(s.band || [])].flat().map(ay)), ...yl.map((l) => l.at)].filter(Number.isFinite);
  const fx = [...sx.flat(), ...xl.map((l) => l.at)].filter(Number.isFinite);
  if (!fx.length || !ys.length) return h("p", { class: "muted" }, "Nothing to plot.");
  let [x0, x1, y0, y1] = [Math.min(...fx), Math.max(...fx), Math.min(...ys), Math.max(...ys)];
  if (x0 === x1) { x0 -= 1; x1 += 1; }
  if (y0 === y1) { y0 -= 1; y1 += 1; }
  const pad = (y1 - y0) * 0.05; y0 -= pad; y1 += pad;
  // Ticks as [placed, label].
  const axis = (lo, hi, log, text, percent) => (log ? logTicks(10 ** lo, 10 ** hi).map((t) => [Math.log10(t), fmt(t)])
    : ticks(lo, hi).map((t) => [t, text ? String(t) : fmt(t, percent)]));
  const yTicks = axis(y0, y1, b.y_scale === "log", false, b.y_percent);
  // Room for the widest y tick (~6.5px a character at 11px) and the axis title beside it.
  const L = Math.max(52, 6.5 * Math.max(...yTicks.map(([, t]) => t.length)) + (b.y_label ? 38 : 14));
  const X = (v) => L + ((v - x0) / (x1 - x0)) * (W - L - R), Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const grid = [
    ...yTicks.map(([t, s]) => [h("svg:line", { x1: L, x2: W - R, y1: Y(t), y2: Y(t), class: "grid" }),
      h("svg:text", { x: L - 6, y: Y(t) + 4, "text-anchor": "end" }, s)]),
    ...axis(x0, x1, b.x_scale === "log", b.x_text, b.x_percent).map(([t, s]) => h("svg:text", { x: X(t), y: H - B + 16, "text-anchor": "middle" }, s)),
    h("svg:line", { x1: L, x2: W - R, y1: H - B, y2: H - B, class: "axis" }),
    b.x_label && h("svg:text", { x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle", class: "label" }, b.x_label),
    b.y_label && h("svg:text", { x: 12, y: (T + H - B) / 2, "text-anchor": "middle", class: "label", transform: `rotate(-90 12 ${(T + H - B) / 2})` }, b.y_label),
  ];
  const refs = [
    ...yl.map((l) => [h("svg:line", { x1: L, x2: W - R, y1: Y(l.at), y2: Y(l.at), class: "ref" }),
      h("svg:text", { x: W - R, y: Y(l.at) - 4, "text-anchor": "end", class: "ref-name" }, `${l.name} ${fmt(l.value, b.y_percent)}`)]),
    ...xl.map((l) => [h("svg:line", { x1: X(l.at), x2: X(l.at), y1: T, y2: H - B, class: "ref" }),
      h("svg:text", { x: X(l.at) + 4, y: T + 10, class: "ref-name" }, `${l.name} ${fmt(l.value, b.x_percent)}`)]),
  ];
  // A step holds each value until the next x; walked backwards (a band's top), it drops first.
  const path = (pts, step, back) => pts.map(([x, y], k) => {
    const px = X(x).toFixed(1), py = Y(y).toFixed(1);
    return k === 0 ? `M${px},${py}` : !step ? `L${px},${py}` : back ? `V${py}H${px}` : `H${px}V${py}`;
  }).join("");
  const bands = b.series.map((s, i) => {
    if (!s.band) return null;
    const parts = runs(s.band[0].map((lo, k) => [sx[i][k], ay(lo), ay(s.band[1][k])]));
    if (s.kind === "scatter") return h("svg:g", { stroke: hue(i), class: "errors" },
      parts.flat().map(([x, lo, hi]) => h("svg:path", { d: `M${X(x) - 3},${Y(lo)}h6M${X(x)},${Y(lo)}V${Y(hi)}M${X(x) - 3},${Y(hi)}h6` })));
    const step = s.kind === "step";
    const d = parts.map((p) => path(p.map(([x, lo]) => [x, lo]), step) + path([...p].reverse().map(([x, , hi]) => [x, hi]), step, true).replace(/^M/, "L") + "Z").join("");
    return h("svg:path", { d, fill: hue(i), class: "band" });
  });
  const marks = b.series.map((s, i) => {
    const parts = runs(s.y.map((y, k) => [sx[i][k], ay(y)]));
    const c = hue(i);
    if (s.kind === "scatter") return h("svg:g", { fill: c }, parts.flat().map(([x, y]) => h("svg:circle", { cx: X(x), cy: Y(y), r: 2.2 })));
    return h("svg:path", { d: parts.map((p) => path(p, s.kind === "step")).join(""), stroke: c, fill: "none", "stroke-width": 1.5 });
  });
  return h("figure", { class: "chart" }, b.title && h("figcaption", {}, b.title),
    h("svg:svg", { viewBox: `0 0 ${W} ${H}` }, grid, bands, refs, marks),
    b.every && h("p", { class: "muted small" }, `One point in ${fmt(b.every)} of ${fmt(b.points)} is drawn.`),
    b.dropped && h("p", { class: "muted small" }, `${fmt(b.dropped)} ${b.dropped === 1 ? "value" : "values"} at 0 or less ${b.dropped === 1 ? "has" : "have"} no place on the log axis, so left out.`),
    b.series.length > 1 && h("p", { class: "legend" }, b.series.map((s, i) => h("span", {}, h("i", { class: s.kind, style: `background:${hue(i)}` }), s.name))));
};
