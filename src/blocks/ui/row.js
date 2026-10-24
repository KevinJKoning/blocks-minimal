// Blocks side by side, each drawn as the page draws any block (paint, from the kit).
RENDER.row = (b, n) => h("figure", { class: "row" }, b.title && h("figcaption", {}, b.title),
  h("div", { class: "cells" }, b.blocks.map((c) => h("div", { class: "cell" }, paint(c, n)))));
