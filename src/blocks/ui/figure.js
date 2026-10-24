// An SVG or PNG image, with its caption.
RENDER.figure = (b) => h("figure", {}, h("img", { src: b.media === "image/png" ? `data:image/png;base64,${b.data}` : `data:image/svg+xml,${encodeURIComponent(b.data)}`, alt: b.caption || "" }),
  b.caption && h("figcaption", {}, b.caption));
