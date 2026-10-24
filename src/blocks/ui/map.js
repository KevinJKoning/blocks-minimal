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
// The pin marks the hovered region's value on the bar.
const scale = (g, label, pin) => h("div", { class: "scale" }, g && [
  h("div", { class: "bar" }, h("i", { style: `background: linear-gradient(to right, ${g.stops.join(", ")})` }),
    marks(g).map((v) => h("span", { style: `left: ${(100 * place(g, v)).toFixed(1)}%` }, fmt(v))), pin),
  label && h("span", {}, label),
  g.unshaded && h("span", {}, h("b", { class: "none" }), `${fmt(g.unshaded)} at 0 or less, unshaded`)]);

// Polygons in their own coordinates, filled with the colours ui.map chose for the layer shown.
// Hovering reads a region out beneath; pinch (or ctrl + scroll), double-click or + / − zoom,
// and dragging pans once zoomed. Plain scrolling stays the page's.
RENDER.map = (b) => {
  const [x0, y0, x1, y1] = b.bounds, s = Math.min(640 / (x1 - x0 || 1), 480 / (y1 - y0 || 1));
  const W = (x1 - x0) * s, H = (y1 - y0) * s;
  const P = ([x, y]) => `${((x - x0) * s).toFixed(1)},${((y1 - y) * s).toFixed(1)}`;
  const d = (rings, close) => rings.map((r) => `M${r.map(P).join("L")}${close ? "Z" : ""}`).join("");
  const areas = b.shapes.map((rings, i) => h("svg:path", { d: d(rings, true), class: "area", "data-i": i }));
  const svg = h("svg:svg", { viewBox: `0 0 ${W} ${H}` }, areas, b.lines.map((rings) => h("svg:path", { d: d(rings, false), class: "line" })));
  const readout = h("span", { class: "readout" }), pin = h("b", { class: "pin" }), legend = h("div");
  let layer = b.layers[0], hovered = null;

  const read = (i) => {
    hovered = i;
    const v = i == null || !layer ? null : num(layer.values[i]);
    readout.textContent = i == null ? "" : [b.names?.[i], v != null && [fmt(v), layer.label].filter(Boolean).join(" ")].filter(Boolean).join(" · ");
    const g = layer?.legend, at = g && Number.isFinite(v) && !(g.scale === "log" && v <= 0) && place(g, v);
    pin.style.display = at === false || at == null ? "none" : "";
    if (at !== false && at != null) pin.style.left = `${(100 * Math.min(1, Math.max(0, at))).toFixed(1)}%`;
  };
  const show = (l) => {
    layer = l;
    areas.forEach((a, i) => (a.style.fill = l?.fills?.[i] || ""));
    legend.replaceChildren(scale(l?.legend, l?.label, pin));
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
    } else read(e.target.dataset?.i == null ? null : +e.target.dataset.i);
  });
  svg.addEventListener("pointerup", () => (drag = null));
  svg.addEventListener("pointerleave", () => drag || read(null));

  show(layer); apply();
  return h("figure", { class: "map" }, b.title && h("figcaption", {}, b.title),
    tabs.length && h("p", { class: "layers" }, tabs), svg,
    h("p", { class: "under" }, readout, h("span", { class: "zoom" },
      h("button", { onclick: () => zoom(2), "aria-label": "zoom in" }, "+"), h("button", { onclick: () => zoom(0.5), "aria-label": "zoom out" }, "−"), reset)),
    legend);
};
