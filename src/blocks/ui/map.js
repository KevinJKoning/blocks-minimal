// Polygons and points in their own coordinates, filled with the colours ui.map chose for the
// layer shown, over its grid if it has one, under its lines. Hovering reads a region or a cell
// out beneath; pinch (or ctrl + scroll), double-click or + / − zoom, and dragging pans once
// zoomed. Plain scrolling stays the page's.
const dot = (rings) => rings.every((r) => r.length === 1);
RENDER.map = (b) => {
  // Dots get a margin, so one on the extent's edge is drawn whole.
  const m = b.shapes.some(dot) || b.lines.some((g) => g.shapes.some(dot)) ? 8 : 0;
  const [x0, y0, x1, y1] = b.bounds, s = Math.min((640 - 2 * m) / (x1 - x0 || 1), (480 - 2 * m) / (y1 - y0 || 1));
  const W = (x1 - x0) * s + 2 * m || 640, H = (y1 - y0) * s + 2 * m || 480;
  const P = ([x, y]) => `${((x - x0) * s + m).toFixed(1)},${((y1 - y) * s + m).toFixed(1)}`;
  // A ring of one point is a dot: a stroke of no length, with round caps.
  const d = (rings, close) => rings.map((r) => (r.length === 1 ? `M${P(r[0])}h0` : `M${r.map(P).join("L")}${close ? "Z" : ""}`)).join("");
  const areas = b.shapes.map((rings, i) => h("svg:path", { d: d(rings, true), class: dot(rings) ? "dot" : "area", "data-i": i }));
  const named = b.lines.some((g) => g.name != null), color = (k) => (named ? `var(--s${(k % 6) + 1})` : null);
  const lines = b.lines.map((g, k) => g.shapes.map((rings) =>
    h("svg:path", { d: d(rings, false), class: dot(rings) ? "dot mark" : "line", style: color(k) && `stroke: ${color(k)}` })));
  const under = h("svg:g", { class: "grid" });
  const svg = h("svg:svg", { viewBox: `0 0 ${W} ${H}` }, under, areas, lines);
  const readout = h("span", { class: "readout" }), pin = h("b", { class: "pin" }), key = h("div");
  let layer = b.layers[0], hovered = null;

  const read = (i, cell) => {
    hovered = i;
    const v = i != null ? (layer ? num(layer.values[i]) : null) : cell;
    readout.textContent = i == null && cell == null ? "" : [i != null && b.names?.[i], v != null && [fmt(v), layer?.label].filter(Boolean).join(" ")].filter(Boolean).join(" · ");
    const g = layer?.legend, at = g && !g.names && Number.isFinite(v) && !(g.scale === "log" && v <= 0) && place(g, v);
    pin.style.display = at === false || at == null ? "none" : "";
    if (at !== false && at != null) pin.style.left = `${(100 * Math.min(1, Math.max(0, at))).toFixed(1)}%`;
  };
  // The grid's cells, a rect for each run of one colour along a row.
  const surface = (g) => {
    if (!g) return under.replaceChildren();
    const [gx0, , , gy1] = g.bounds, rows = g.values.length / g.cols;
    const cw = (g.bounds[2] - gx0) / g.cols * s, ch = (gy1 - g.bounds[1]) / rows * s, ox = (gx0 - x0) * s + m, oy = (y1 - gy1) * s + m;
    const out = [];
    for (let r = 0; r < rows; r++) for (let c = 0; c < g.cols;) {
      const f = g.cells[r * g.cols + c];
      let e = c + 1;
      while (e < g.cols && g.cells[r * g.cols + e] === f) e++;
      // A hair wider and taller than the cells, so no seam of paper shows between them.
      if (f >= 0) out.push(h("svg:rect", { x: ox + c * cw, y: oy + r * ch, width: (e - c) * cw + 0.4, height: ch + 0.4, fill: g.fills[f] }));
      c = e;
    }
    under.replaceChildren(...out);
  };
  const cellAt = ([ux, uy]) => {
    const g = layer?.grid;
    if (!g) return null;
    const rows = g.values.length / g.cols, x = x0 + (ux - m) / s, y = y1 - (uy - m) / s;
    const c = Math.floor((x - g.bounds[0]) / (g.bounds[2] - g.bounds[0]) * g.cols), r = Math.floor((g.bounds[3] - y) / (g.bounds[3] - g.bounds[1]) * rows);
    return c >= 0 && c < g.cols && r >= 0 && r < rows ? num(g.values[r * g.cols + c]) : null;
  };
  const show = (l) => {
    layer = l;
    areas.forEach((a, i) => {
      const f = l?.fills?.[i];
      if (a.classList.contains("dot")) a.style.stroke = f || "";
      else a.style.fill = f || (l?.grid ? "none" : "");
    });
    surface(l?.grid);
    key.replaceChildren(legend(l?.legend, l?.label, pin));
    tabs.forEach((t) => t.setAttribute("aria-pressed", t.layer === l));
    read(hovered);
  };
  const tabs = b.layers.length > 1 ? b.layers.map((l) => Object.assign(h("button", { onclick: () => show(l) }, l.name), { layer: l })) : [];

  // The view box: its top-left and its width (its height keeps the map's shape).
  let vx = 0, vy = 0, vw = W;
  const reset = h("button", { onclick: () => { vw = W; apply(); } }, "reset");
  const apply = () => {
    vw = Math.min(W, Math.max(W / 32, vw));
    const vh = vw * H / W;
    vx = Math.min(W - vw, Math.max(0, vx)); vy = Math.min(H - vh, Math.max(0, vy));
    svg.setAttribute("viewBox", `${vx} ${vy} ${vw} ${vh}`);
    svg.classList.toggle("zoomed", vw < W);
    reset.hidden = vw >= W;
  };
  // Zoom by f about a point in the map's units (its centre if none).
  const zoom = (f, px = vx + vw / 2, py = vy + vw * H / W / 2) => {
    const n = Math.min(W, Math.max(W / 32, vw / f)), k = n / vw;
    vx = px - (px - vx) * k; vy = py - (py - vy) * k; vw = n; apply();
  };
  const at = (e) => { const r = svg.getBoundingClientRect(); return [vx + (e.clientX - r.left) / r.width * vw, vy + (e.clientY - r.top) / r.height * vw * H / W]; };
  svg.addEventListener("wheel", (e) => { if (!e.ctrlKey && !e.metaKey) return; e.preventDefault(); zoom(Math.exp(-e.deltaY / 100), ...at(e)); }, { passive: false });
  svg.addEventListener("dblclick", (e) => { e.preventDefault(); zoom(e.shiftKey ? 0.5 : 2, ...at(e)); });
  let drag = null;
  svg.addEventListener("pointerdown", (e) => { if (vw < W && e.button === 0) { drag = [e.clientX, e.clientY, vx, vy]; svg.setPointerCapture(e.pointerId); } });
  svg.addEventListener("pointermove", (e) => {
    if (drag) {
      const r = svg.getBoundingClientRect(), u = vw / r.width;
      vx = drag[2] - (e.clientX - drag[0]) * u; vy = drag[3] - (e.clientY - drag[1]) * u; apply();
    } else if (e.target.dataset?.i != null) read(+e.target.dataset.i);
    else read(null, cellAt(at(e)));
  });
  svg.addEventListener("pointerup", () => (drag = null));
  svg.addEventListener("pointerleave", () => drag || read(null));

  show(layer); apply();
  const every = layer?.grid?.every;
  return h("figure", { class: "map" }, b.title && h("figcaption", {}, b.title),
    tabs.length > 0 && h("p", { class: "layers" }, tabs), svg,
    h("p", { class: "under" }, readout, h("span", { class: "zoom" },
      h("button", { onclick: () => zoom(2), "aria-label": "zoom in" }, "+"), h("button", { onclick: () => zoom(0.5), "aria-label": "zoom out" }, "−"), reset)),
    key,
    named && h("p", { class: "key" }, b.lines.map((g, k) => g.name != null && h("span", {},
      h("i", { class: g.shapes.every(dot) ? "dot" : "line", style: `background: ${color(k)}` }), g.name))),
    every && h("p", { class: "muted small" }, `The grid keeps one row and column in ${fmt(every)}.`));
};
