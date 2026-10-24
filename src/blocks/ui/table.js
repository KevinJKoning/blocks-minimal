// A table's first rows (ui.table keeps the total), numbers right-aligned.
RENDER.table = (b) => h("figure", { class: "table" }, b.title && h("figcaption", {}, b.title),
  h("div", { class: "scroll" }, h("table", {}, h("tr", {}, b.columns.map((c) => h("th", {}, c))),
    b.rows.map((r) => h("tr", {}, r.map((v) => h("td", { class: typeof num(v) === "number" ? "num" : null }, fmt(v))))))),
  h("p", { class: "muted small" }, b.total > b.rows.length ? `${b.rows.length} of ${fmt(b.total)} rows` : `${fmt(b.total)} rows × ${b.columns.length} columns`));
