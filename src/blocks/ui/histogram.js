// Bars of counts over the bins ui.histogram chose, on round ticks, with an optional marked value.
RENDER.histogram = (b) => {
  if (!b.counts.length) return h("p", { class: "muted" }, "Nothing to count.");
  const W = 640, H = 260, R = 12, T = 12, B = 40, y1 = Math.max(...b.counts) * 1.05;
  const x0 = b.edges[0], x1 = b.edges[b.edges.length - 1], yTicks = ticks(0, y1).filter(Number.isInteger);
  const L = Math.max(44, 6.5 * Math.max(...yTicks.map((t) => fmt(t).length)) + 38);
  const X = (v) => L + ((v - x0) / (x1 - x0)) * (W - L - R), Y = (v) => T + (1 - v / y1) * (H - T - B);
  const total = b.counts.reduce((a, c) => a + c, 0);
  return h("figure", { class: "histogram" }, b.title && h("figcaption", {}, b.title),
    h("svg:svg", { viewBox: `0 0 ${W} ${H}` },
      yTicks.map((t) => [h("svg:line", { x1: L, x2: W - R, y1: Y(t), y2: Y(t), class: "grid" }),
        h("svg:text", { x: L - 6, y: Y(t) + 4, "text-anchor": "end" }, fmt(t))]),
      b.counts.map((c, k) => c > 0 && h("svg:rect", { x: X(b.edges[k]) + 0.5, width: Math.max(0.5, X(b.edges[k + 1]) - X(b.edges[k]) - 1), y: Y(c), height: Y(0) - Y(c), class: "bar" },
        h("svg:title", {}, `${fmt(b.edges[k])} to ${fmt(b.edges[k + 1])}: ${c}`))),
      ticks(x0, x1).map((t) => h("svg:text", { x: X(t), y: H - B + 16, "text-anchor": "middle" }, fmt(t))),
      h("svg:line", { x1: L, x2: W - R, y1: Y(0), y2: Y(0), class: "axis" }),
      b.mark != null && h("svg:line", { x1: X(b.mark), x2: X(b.mark), y1: T, y2: Y(0), class: "mark" }),
      b.x_label && h("svg:text", { x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle", class: "label" }, b.x_label),
      h("svg:text", { x: 12, y: (T + H - B) / 2, "text-anchor": "middle", class: "label", transform: `rotate(-90 12 ${(T + H - B) / 2})` }, "count")),
    h("p", { class: "muted small" }, `${total} values in ${b.counts.length} bins of width ${fmt(b.edges[1] - b.edges[0])}` + (b.missing ? `; ${b.missing} unknown left out` : "")));
};
