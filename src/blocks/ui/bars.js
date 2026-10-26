// One row per category, on round ticks: bars from the reference (or 0), or dots, with error
// bars where ui.bars has intervals and a dashed line at the reference.
RENDER.bars = (b) => {
  const S = b.series.length, row = Math.max(28, 10 * S + 14), W = 640, T = 6, B = b.label ? 38 : 24, R = 16;
  const L = Math.min(260, 6.2 * Math.max(...b.categories.map((c) => c.length)) + 16), H = T + b.categories.length * row + B;
  const base = b.reference ?? 0;
  const vals = b.series.flatMap((s) => [...s.values, ...(s.interval || []).flat()]).map(num).filter(Number.isFinite);
  if (!vals.length) return h("p", { class: "muted" }, "Nothing to draw.");
  const ends = [...vals, ...(b.kind === "bar" || b.reference != null ? [base] : [])];
  let [lo, hi] = [Math.min(...ends), Math.max(...ends)];
  if (lo === hi) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.04; lo -= b.kind === "bar" && lo === base ? 0 : pad; hi += pad;
  const X = (v) => L + ((v - lo) / (hi - lo)) * (W - L - R);
  const Y = (i, j) => T + i * row + row / 2 + (S > 1 ? (j - (S - 1) / 2) * 10 : 0);
  const fits = Math.floor((L - 16) / 6.2 + 1e-9), cut = (c) => (c.length > fits ? c.slice(0, fits - 1) + "…" : c);
  const f = (v) => fmt(v, b.percent);
  const marks = b.series.map((s, j) => h("svg:g", { fill: hue(j), stroke: hue(j) }, s.values.map((v, i) => {
    v = num(v);
    const iv = s.interval && [num(s.interval[0][i]), num(s.interval[1][i])], y = Y(i, j);
    const tip = h("svg:title", {}, `${b.categories[i]} · ${s.name}: ${f(v)}${iv ? ` (${f(iv[0])} to ${f(iv[1])})` : ""}`);
    return [
      iv && iv.every(Number.isFinite) && h("svg:path", { class: "error", d: `M${X(iv[0])},${y - 3}v6M${X(iv[0])},${y}H${X(iv[1])}M${X(iv[1])},${y - 3}v6` }),
      Number.isFinite(v) && (b.kind === "dot" ? h("svg:circle", { cx: X(v), cy: y, r: 3.5 }, tip)
        : h("svg:rect", { x: Math.min(X(base), X(v)), y: y - 4, width: Math.abs(X(v) - X(base)), height: 8, stroke: "none" }, tip)),
    ];
  })));
  return h("figure", { class: "bars" }, b.title && h("figcaption", {}, b.title),
    h("svg:svg", { viewBox: `0 0 ${W} ${H}` },
      ticks(lo, hi).map((t) => [h("svg:line", { x1: X(t), x2: X(t), y1: T, y2: H - B, class: "grid" }),
        h("svg:text", { x: X(t), y: H - B + 14, "text-anchor": "middle" }, f(t))]),
      b.categories.map((c, i) => h("svg:text", { x: L - 8, y: Y(i, (S - 1) / 2) + 4, "text-anchor": "end", class: "category" }, h("svg:title", {}, c), cut(c))),
      b.reference != null && h("svg:line", { x1: X(b.reference), x2: X(b.reference), y1: T, y2: H - B, class: "reference" }),
      marks,
      b.label && h("svg:text", { x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle", class: "label" }, b.label)),
    S > 1 && h("p", { class: "legend" }, b.series.map((s, j) => h("span", {}, h("i", { class: b.kind, style: `background:${hue(j)}` }), s.name))));
};
