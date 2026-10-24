// The territories as tiles, in the order ui/tiles.py chose, each with its credibility badge.
RENDER.tiles = (b) => h("figure", { class: "tiles" }, b.title && h("figcaption", {}, b.title),
  h("div", { class: "grid" }, b.tiles.map((t) => h("div", { class: "tile" },
    h("span", { class: "muted small" }, t.name), h("strong", {}, fmt(t.rate)), h("span", { class: `badge ${t.band}` }, t.band)))));
