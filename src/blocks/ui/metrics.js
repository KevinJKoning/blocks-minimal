// The node's metrics, labelled, with the change since the last run and the baseline's value.
RENDER.metrics = (b, n) => {
  const { last, baseline } = records();
  const before = last?.nodes[n]?.metrics || {}, base = baseline?.nodes[n]?.metrics || {};
  const delta = (it, ref) => {
    const v = num(it.value), r = num(ref);
    if (typeof v !== "number" || typeof r !== "number" || Math.abs(v - r) <= 1e-12 * Math.max(1, Math.abs(r))) return null;
    const better = it.goal === "min" ? v < r : it.goal === "max" ? v > r : null;
    return h("span", { class: `delta ${better === null ? "" : better ? "better" : "worse"}` }, `${v > r ? "+" : "−"}${fmt(Math.abs(v - r))}`);
  };
  const row = (it) => h("tr", { class: it.extra ? "extra" : null },
    h("th", {}, it.label), h("td", {}, fmt(it.value)), h("td", {}, delta(it, before[it.key])),
    baseline && h("td", { class: "muted" }, fmt(base[it.key])));
  const main = b.items.filter((it) => !it.extra), extra = b.items.filter((it) => it.extra);
  return h("div", { class: "metrics" },
    h("table", {}, (last || baseline) && h("tr", { class: "head" }, h("th"), h("th"), h("th", {}, last && "Δ last run"), baseline && h("th", {}, "baseline")),
      main.map(row)),
    extra.length > 0 && h("details", {}, h("summary", {}, `${extra.length} more numbers`), h("table", {}, extra.map(row))));
};
