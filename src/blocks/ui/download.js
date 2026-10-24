// A file to take away, as a card with a Download button (the overview gathers these).
RENDER.download = (b, n, label = "Output") => card(label, b.name, `${size(b.size)}${b.title ? ` · ${b.title}` : ""}`,
  h("button", { onclick: async () => save(b.name, new Blob([await bytes(b.data)], { type: b.media })) }, "Download"));
