// What the blocks' renderers share, on top of the page's kit; the build puts it before them,
// unscoped. A helper moves here from a block once a second block needs it.

// The i-th series colour, from the theme's six (--s1 to --s6), round again past them.
const hue = (i) => `var(--s${(i % 6) + 1})`;

// About n round ticks (1, 2 or 5 times a power of ten) from lo to hi.
function ticks(lo, hi, n = 5) {
  const step = 10 ** Math.floor(Math.log10((hi - lo) / n || 1)), err = (hi - lo) / n / step;
  const s = step * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1);
  const out = [];
  // Each tick from its index, not a running sum, so zero is exactly 0 (a sum leaves -5.6e-17).
  for (let k = Math.ceil(lo / s - 1e-9); k * s <= hi + s * 1e-9; k++) out.push(+(k * s).toPrecision(12));
  return out;
}

// Powers of ten from lo to hi (both > 0), with 2 and 5 times them when the range spans under
// two; round linear ticks if even that leaves fewer than two.
function logTicks(lo, hi) {
  const out = [];
  for (const m of [[1], [1, 5], [1, 2, 5]]) {
    out.length = 0;
    for (let e = Math.floor(Math.log10(lo)); 10 ** e <= hi * (1 + 1e-9); e++)
      for (const k of m) { const t = +(k * 10 ** e).toPrecision(12); if (t >= lo * (1 - 1e-9) && t <= hi * (1 + 1e-9)) out.push(t); }
    if (out.length >= 3) return out;
  }
  return out.length >= 2 ? out : ticks(lo, hi, 4);
}

// Where v falls on a ramp's legend (ui/_kit.py shade), from 0 to 1.
const place = (g, v) => (g.scale === "log"
  ? (Math.log10(v) - Math.log10(g.lo)) / (Math.log10(g.hi) - Math.log10(g.lo) || 1) : (v - g.lo) / (g.hi - g.lo || 1));

// A legend: the ramp's stops as a gradient from lo to hi, labelled on round values (powers of
// ten on a log scale), with the centre marked on a diverging one; or a swatch per name. pin, an
// element, marks a hovered value on the bar.
function legend(g, label, pin, percent) {
  if (!g) return h("div", { class: "scale" });
  if (g.names) return h("div", { class: "scale" }, label && h("span", {}, label),
    g.names.map((n) => h("span", {}, h("b", { class: "swatch", style: `background: ${n.fill}` }), n.name)));
  const t = g.scale === "log" ? logTicks(g.lo, g.hi) : ticks(g.lo, g.hi, 4);
  const marks = g.center == null || t.includes(g.center) ? t : [...t, g.center];
  return h("div", { class: "scale" },
    h("div", { class: "bar" }, h("i", { style: `background: linear-gradient(to right, ${g.stops.join(", ")})` }),
      marks.map((v) => h("span", { style: `left: ${(100 * place(g, v)).toFixed(1)}%` }, fmt(v, percent))), pin),
    label && h("span", {}, label),
    g.unshaded && h("span", {}, h("b", { class: "swatch none" }), `${fmt(g.unshaded)} at 0 or less, unshaded`));
}
