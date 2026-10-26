// Cells in rows and columns, filled with the colours ui.heatmap chose, labelled at the left
// and the top (slanted when the columns are many or long), with each value written in its
// cell when the cells are big enough to hold it. A cell's title reads it out.
RENDER.heatmap = (b) => {
  const nr = b.rows.length, nc = b.columns.length;
  if (!nr || !nc) return h("p", { class: "muted" }, "Nothing to draw.");
  const W = 640, ch = (c) => 6.2 * c.length;
  const L = Math.min(200, Math.max(...b.rows.map(ch)) + 10);
  const cw = Math.min(64, (W - L) / nc), rh = Math.max(12, Math.min(30, cw));
  // Every k-th column is labelled, so labels sit at least 12px apart.
  const k = Math.ceil(12 / cw);
  const slant = Math.max(...b.columns.map(ch)) > cw - 4;
  const T = slant ? Math.min(120, Math.max(...b.columns.map(ch)) * 0.71 + 12) : 20, H = T + nr * rh + 4;
  const f = (v) => fmt(v, b.percent), writes = cw >= 30 && rh >= 16;
  const cells = b.values.map((r, i) => r.map((v, j) => {
    const x = L + j * cw, y = T + i * rh, fill = b.fills[i][j];
    return [h("svg:rect", { x, y, width: cw - 1, height: rh - 1, class: fill ? "cell" : "cell none", style: fill && `fill: ${fill}` },
      h("svg:title", {}, `${b.rows[i]} · ${b.columns[j]}: ${f(v)}`)),
    writes && v != null && h("svg:text", { x: x + cw / 2, y: y + rh / 2 + 4, "text-anchor": "middle", class: b.dark[i][j] ? "on-dark" : "on-light" }, f(v))];
  }));
  const fits = Math.floor((L - 10) / 6.2 + 1e-9), cut = (c) => (c.length > fits ? c.slice(0, fits - 1) + "…" : c);
  return h("figure", { class: "heatmap" }, b.title && h("figcaption", {}, b.title),
    h("svg:svg", { viewBox: `0 0 ${Math.max(W, L + nc * cw)} ${H}` },
      b.rows.map((r, i) => h("svg:text", { x: L - 6, y: T + i * rh + rh / 2 + 4, "text-anchor": "end" }, h("svg:title", {}, r), cut(r))),
      b.columns.map((c, j) => j % k === 0 && (slant
        ? h("svg:text", { x: L + j * cw + cw / 2, y: T - 6, transform: `rotate(-45 ${L + j * cw + cw / 2} ${T - 6})` }, c)
        : h("svg:text", { x: L + j * cw + cw / 2, y: T - 6, "text-anchor": "middle" }, c))),
      cells),
    legend(b.legend, b.label, null, b.percent));
};
