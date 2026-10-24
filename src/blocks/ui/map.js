// The legend for colours ui.map chose: its stops as a gradient from lo to hi.
const scale = (g, label) => g && h("p", { class: "scale" }, h("span", {}, fmt(g.lo)),
  h("i", { style: `background: linear-gradient(to right, ${g.stops.join(", ")})` }), h("span", {}, fmt(g.hi)), label && h("span", { class: "muted" }, label));

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
