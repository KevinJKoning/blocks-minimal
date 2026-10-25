// Bars of counts over the bins ui.histogram chose, on round ticks, with an optional marked
// value. Groups are outlines, each its share of its own group per bin, in the series colours.
RENDER.histogram = (b) => {
  if (!b.groups.some((g) => g.counts.some((c) => c > 0))) return h("p", { class: "muted" }, "Nothing to count.");
  const many = b.groups.length > 1;
  const sum = (cs) => cs.reduce((a, c) => a + c, 0);
  const heights = b.groups.map((g) => (many ? g.counts.map((c) => c / (sum(g.counts) || 1)) : g.counts));
  const W = 640, H = 260, R = 12, T = 12, B = 40, y1 = Math.max(...heights.flat()) * 1.05;
  const x0 = b.edges[0], x1 = b.edges[b.edges.length - 1], yTicks = ticks(0, y1).filter((t) => many || Number.isInteger(t));
  const L = Math.max(44, 6.5 * Math.max(...yTicks.map((t) => fmt(t, many).length)) + 38);
  const X = (v) => L + ((v - x0) / (x1 - x0)) * (W - L - R), Y = (v) => T + (1 - v / y1) * (H - T - B);
  const tip = (k, c, g) => h("svg:title", {}, `${g.name ? `${g.name}, ` : ""}${fmt(b.edges[k])} to ${fmt(b.edges[k + 1])}: ${c}`
    + (many ? ` (${fmt(c / (sum(g.counts) || 1), true)})` : ""));
  const marks = many
    ? b.groups.map((g, j) => {
      const d = `M${X(x0)},${Y(0)}` + heights[j].map((v, k) => `V${Y(v)}H${X(b.edges[k + 1])}`).join("") + `V${Y(0)}Z`;
      return h("svg:g", {}, h("svg:path", { d, class: "outline", stroke: hue(j), fill: hue(j) }),
        g.counts.map((c, k) => h("svg:rect", { x: X(b.edges[k]), width: X(b.edges[k + 1]) - X(b.edges[k]), y: Y(heights[j][k]), height: Y(0) - Y(heights[j][k]), class: "hit" }, tip(k, c, g))));
    })
    : b.groups[0].counts.map((c, k) => c > 0 && h("svg:rect", { x: X(b.edges[k]) + 0.5, width: Math.max(0.5, X(b.edges[k + 1]) - X(b.edges[k]) - 1), y: Y(c), height: Y(0) - Y(c), class: "bar" },
      tip(k, c, b.groups[0])));
  const told = b.groups.map((g) => (many ? `${g.name} ${fmt(sum(g.counts))}` : fmt(sum(g.counts)))).join(", ");
  return h("figure", { class: "histogram" }, b.title && h("figcaption", {}, b.title),
    h("svg:svg", { viewBox: `0 0 ${W} ${H}` },
      yTicks.map((t) => [h("svg:line", { x1: L, x2: W - R, y1: Y(t), y2: Y(t), class: "grid" }),
        h("svg:text", { x: L - 6, y: Y(t) + 4, "text-anchor": "end" }, fmt(t, many))]),
      marks,
      ticks(x0, x1).map((t) => h("svg:text", { x: X(t), y: H - B + 16, "text-anchor": "middle" }, fmt(t))),
      h("svg:line", { x1: L, x2: W - R, y1: Y(0), y2: Y(0), class: "axis" }),
      b.mark != null && h("svg:line", { x1: X(b.mark), x2: X(b.mark), y1: T, y2: Y(0), class: "mark" }),
      b.x_label && h("svg:text", { x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle", class: "label" }, b.x_label),
      h("svg:text", { x: 12, y: (T + H - B) / 2, "text-anchor": "middle", class: "label", transform: `rotate(-90 12 ${(T + H - B) / 2})` }, many ? "share of its group" : "count")),
    many && h("p", { class: "legend" }, b.groups.map((g, j) => h("span", {}, h("i", { style: `background:${hue(j)}` }), g.name))),
    h("p", { class: "muted small" }, `${told} values in ${b.edges.length - 1} bins of width ${fmt(b.edges[1] - b.edges[0])}` + (b.missing ? `; ${b.missing} unknown left out` : "")));
};
