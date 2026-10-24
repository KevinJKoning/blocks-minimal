// The node's numbers from the run, labelled by its METRICS (the spec's metrics), with the change
// since the last run and the baseline's value.
RENDER.metrics = (b, n) => {
  const { run, last, baseline } = records(), declared = S.nodes[n].metrics, found = run?.nodes[n]?.metrics || {};
  const before = last?.nodes[n]?.metrics || {}, base = baseline?.nodes[n]?.metrics || {};
  const items = [...declared.map((m) => ({ ...m, value: found[m.key] })),
    ...Object.entries(found).filter(([k]) => !declared.some((m) => m.key === k)).map(([k, v]) => ({ key: k, label: k, value: v, extra: true }))];
  const delta = (it, ref) => {
    const v = num(it.value), r = num(ref);
    if (typeof v !== "number" || typeof r !== "number" || Math.abs(v - r) <= 1e-12 * Math.max(1, Math.abs(r))) return null;
    const better = it.goal === "min" ? v < r : it.goal === "max" ? v > r : null;
    return h("span", { class: `delta ${better === null ? "" : better ? "better" : "worse"}` }, `${v > r ? "+" : "−"}${fmt(Math.abs(v - r))}`);
  };
  const row = (it) => h("tr", { class: it.extra ? "extra" : null },
    h("th", {}, it.label), h("td", {}, fmt(it.value)), h("td", {}, delta(it, before[it.key])),
    baseline && h("td", { class: "muted" }, fmt(base[it.key])));
  const main = items.filter((it) => !it.extra), extra = items.filter((it) => it.extra);
  return h("div", { class: "metrics" },
    h("table", {}, (last || baseline) && h("tr", { class: "head" }, h("th"), h("th"), h("th", {}, last && "Δ last run"), baseline && h("th", {}, "baseline")),
      main.map(row)),
    extra.length > 0 && h("details", {}, h("summary", {}, `${extra.length} more numbers`), h("table", {}, extra.map(row))));
};
