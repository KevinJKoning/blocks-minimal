// A table's first rows (ui.table keeps the total), numbers right-aligned. A table that holds
// all its rows sorts by a header on click (again to reverse); a cut one does not, since it
// would sort only what it shows.
const cell = (v) => h("td", { class: typeof num(v) === "number" ? "num" : null }, fmt(v));
const order = (a, b) => (a == null ? 1 : b == null ? -1 : typeof num(a) === "number" && typeof num(b) === "number"
  ? num(a) - num(b) : String(a).localeCompare(String(b), "en", { numeric: true }));
RENDER.table = (b) => {
  const whole = b.total === b.rows.length, body = h("tbody");
  let by = null, up = true;
  const fill = () => {
    const rows = by == null ? b.rows : [...b.rows].sort((r, s) => (up ? 1 : -1) * order(r[by], s[by]) || 0);
    body.replaceChildren(...rows.map((r) => h("tr", {}, r.map(cell))));
  };
  const head = h("tr", {}, b.columns.map((c, i) => h("th", whole ? {
    class: "sortable", title: "Sort by this column",
    onclick: (e) => {
      up = by === i ? !up : true; by = i; fill();
      for (const th of head.children) th.removeAttribute("data-sort");
      e.currentTarget.setAttribute("data-sort", up ? "up" : "down");
    },
  } : {}, c)));
  fill();
  return h("figure", { class: "table" }, b.title && h("figcaption", {}, b.title),
    h("div", { class: "scroll" }, h("table", {}, h("thead", {}, head), body)),
    h("p", { class: "muted small" }, whole ? `${fmt(b.total)} rows × ${b.columns.length} columns` : `${b.rows.length} of ${fmt(b.total)} rows`));
};
