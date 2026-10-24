// The legend for the colours ui.map chose: its stops as a gradient from lo to hi, labelled on
// round values (powers of ten on a log scale), with the centre marked on a diverging one.
const place = (g, v) => (g.scale === "log"
  ? (Math.log10(v) - Math.log10(g.lo)) / (Math.log10(g.hi) - Math.log10(g.lo) || 1) : (v - g.lo) / (g.hi - g.lo || 1));
function marks(g) {
  if (g.scale === "log") {
    const out = [];
    for (let e = Math.ceil(Math.log10(g.lo) - 1e-9); 10 ** e <= g.hi * (1 + 1e-9); e++) out.push(10 ** e);
    return out.length >= 2 ? out : [g.lo, ...out, g.hi];
  }
  const t = ticks(g.lo, g.hi, 4);
  return g.center == null || t.includes(g.center) ? t : [...t, g.center];
}
const scale = (g, label) => g && h("div", { class: "scale" },
  h("div", { class: "bar" }, h("i", { style: `background: linear-gradient(to right, ${g.stops.join(", ")})` }),
    marks(g).map((v) => h("span", { style: `left: ${(100 * place(g, v)).toFixed(1)}%` }, fmt(v)))),
  label && h("span", {}, label),
  g.unshaded && h("span", {}, h("b", { class: "none" }), `${fmt(g.unshaded)} at 0 or less, unshaded`));

// Polygons in their own coordinates, filled with the colours ui.map chose.
RENDER.map = (b) => {
  const [x0, y0, x1, y1] = b.bounds, W = 640, s = Math.min(W / (x1 - x0 || 1), 480 / (y1 - y0 || 1)), H = (y1 - y0) * s;
  const P = ([x, y]) => `${((x - x0) * s).toFixed(1)},${((y1 - y) * s).toFixed(1)}`;
  const d = (rings, close) => rings.map((r) => `M${r.map(P).join("L")}${close ? "Z" : ""}`).join("");
  return h("figure", { class: "map" }, b.title && h("figcaption", {}, b.title),
    h("svg:svg", { viewBox: `0 0 ${(x1 - x0) * s} ${H}` },
      b.shapes.map((rings, i) => h("svg:path", { d: d(rings, true), class: "area", style: b.fills?.[i] && `fill: ${b.fills[i]}` },
        h("svg:title", {}, [b.names?.[i], b.values && fmt(b.values[i])].filter((x) => x != null).join(": ")))),
      b.lines.map((rings) => h("svg:path", { d: d(rings, false), class: "line" }))),
    scale(b.legend, b.label));
};
