// One step of the node (the spec's steps: name, doc, code), as a unit: its name and docstring, its
// blocks, each drawn as the page draws any block, and its code; the rule down the side is what binds them.
RENDER.step = (b, n) => {
  const s = S.nodes[n].steps.find((x) => x.name === b.name);
  if (!s) throw new Error(`${b.name} is not a step of ${n}: a function at the top of its file, with a docstring`);
  return h("section", { class: "step" },
    h("p", { class: "name" }, h("span", { class: "muted small" }, "Step"), h("code", {}, s.name)),
    markdown(s.doc), b.blocks.map((c) => paint(c, n)),
    h("details", {}, h("summary", {}, `Code of ${s.name}`), h("pre", {}, s.code)));
};
