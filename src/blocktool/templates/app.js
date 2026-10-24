// The page: the graph on the left (the table of contents), one page of blocks on the right
// (the overview, or a node: its docstring, settings, results and code). Python runs in a
// worker; Run computes what is stale and the graph's cache keeps the rest.

const M = JSON.parse(document.getElementById("manifest").textContent);
const S = M.spec;
const bytes = async (b64) => new Uint8Array(await (await fetch(`data:application/octet-stream;base64,${b64}`)).arrayBuffer());
const text = (b64) => new TextDecoder().decode(Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));

const state = {
  page: decodeURIComponent(location.hash.slice(1)) || null,   // a node's name, or null: the overview
  settings: Object.fromEntries(S.order.flatMap((n) => Object.entries(S.nodes[n].settings).map(([p, s]) => [`${n}.${p}`, s.default]))),
  data: Object.fromEntries(Object.entries(M.data).map(([d, v]) => [d, { key: v.key, size: v.size, file: null }])),
  results: {},   // node -> its result in the last run
  record: null,  // the last run's record
  differs: null, // {node: [what differs]} from the baseline (blocks.graph.compare); null without one
  previous: null,
  ran: {},       // node -> {settings, data} it last ran with
  status: "Starting Python…",
  busy: true,
};

// ------------------------------------------------------------------ DOM
function h(tag, attrs = {}, ...kids) {
  const svg = tag.startsWith("svg:");
  const el = svg ? document.createElementNS("http://www.w3.org/2000/svg", tag.slice(4)) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  el.append(...kids.flat(Infinity).filter((k) => k != null && k !== false));
  return el;
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const num = (v) => (v === "NaN" ? NaN : v === "Infinity" ? Infinity : v === "-Infinity" ? -Infinity : v);
function fmt(v) {
  v = num(v);
  if (typeof v !== "number") return v == null ? "—" : String(v);
  if (!Number.isFinite(v)) return String(v);
  if (Number.isInteger(v)) return v.toLocaleString("en-US");
  const a = Math.abs(v);
  return a !== 0 && (a < 1e-3 || a >= 1e9) ? v.toExponential(3) : (+v.toPrecision(4)).toLocaleString("en-US", { maximumFractionDigits: 12 });
}
const size = (n) => (n < 1024 ? `${n} B` : n < 1 << 20 ? `${(n / 1024).toFixed(1)} KB` : `${(n / (1 << 20)).toFixed(1)} MB`);

function markdown(src) {
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  const out = [], lines = String(src).split("\n");
  for (let i = 0; i < lines.length;) {
    const l = lines[i];
    if (/^```/.test(l)) {
      const code = [];
      while (++i < lines.length && !/^```/.test(lines[i])) code.push(lines[i]);
      out.push(`<pre><code>${esc(code.join("\n"))}</code></pre>`); i++;
    } else if (/^ {4}\S/.test(l)) {
      const code = [];
      while (i < lines.length && /^ {4}/.test(lines[i])) code.push(lines[i++].slice(4));
      out.push(`<pre><code>${esc(code.join("\n"))}</code></pre>`);
    } else if (/^#{1,4} /.test(l)) {
      const n = l.indexOf(" ");
      out.push(`<h${n + 1}>${inline(l.slice(n + 1))}</h${n + 1}>`); i++;
    } else if (/^\s*([-*]|\d+\.) /.test(l)) {
      const start = parseInt(l.trim(), 10), items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.) /.test(lines[i])) {
        let item = lines[i++].replace(/^\s*([-*]|\d+\.) /, "");
        while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*]|\d+\.) /.test(lines[i])) item += " " + lines[i++].trim();
        items.push(`<li>${inline(item)}</li>`);
      }
      out.push(start >= 0 ? `<ol start="${start}">${items.join("")}</ol>` : `<ul>${items.join("")}</ul>`);
    } else if (/^\|/.test(l)) {
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++].replace(/^\||\|$/g, "").split("|").map((c) => inline(c.trim())));
      const body = rows.filter((_, k) => k !== 1).map((r, k) => `<tr>${r.map((c) => (k ? `<td>${c}</td>` : `<th>${c}</th>`)).join("")}</tr>`);
      out.push(`<table>${body.join("")}</table>`);
    } else if (l.trim()) {
      const para = [];
      while (i < lines.length && lines[i].trim() && !/^(#{1,4} |```|\s*([-*]|\d+\.) |\|)/.test(lines[i])) para.push(lines[i++]);
      out.push(`<p>${inline(para.join(" "))}</p>`);
    } else i++;
  }
  return h("div", { class: "prose", html: out.join("\n") });
}

// ------------------------------------------------------------------ the worker
let worker, seq = 0;
const pending = new Map();
const call = (type, args = {}, transfer = []) => new Promise((resolve, reject) => {
  pending.set(++seq, { resolve, reject });
  worker.postMessage({ id: seq, type, ...args }, transfer);
});
const runtimeEl = (name) => document.querySelector(`script[data-runtime="${name}"]`);
async function runtimeText(name) {
  return M.runtime ? (await fetch(M.runtime + name)).text() : new TextDecoder().decode(await bytes(runtimeEl(name).textContent));
}
async function startWorker() {
  // Pyodide's ES modules, joined into one classic worker script: browsers refuse module
  // workers from blob: URLs on file:// pages. Pyodide refuses classic workers, which it
  // detects by importScripts working, so that is disabled first.
  const dropMap = (s) => s.replace(/\n\/\/# sourceMappingURL=\S+\s*$/, "\n");
  const asm = dropMap(await runtimeText("pyodide.asm.mjs"))
    .replace(/export\s+default\s+_createPyodideModule;?\s*$/, "\n").replace(/import\.meta\.url/g, "self.location.href");
  const mjs = dropMap(await runtimeText("pyodide.mjs"));
  const m = mjs.match(/export\s*\{([^}]*)\};?/);
  const ret = m[1].split(",").map((s) => { const [a, b] = s.trim().split(/\s+as\s+/); return `${b || a}: ${a}`; }).join(", ");
  const src = `globalThis.importScripts = () => { throw new Error("importScripts is disabled"); };\n${asm}\nconst __pyodide = (() => {\n${mjs.replace(m[0], `return { ${ret} };`)}\n})();\n${document.getElementById("worker").textContent}`;
  worker = new Worker(URL.createObjectURL(new Blob([src], { type: "text/javascript" })));
  worker.onmessage = ({ data: { id, ok, result, error } }) => {
    const p = pending.get(id); pending.delete(id);
    ok ? p.resolve(result) : p.reject(new Error(error));
  };
  worker.onerror = (e) => { for (const p of pending.values()) p.reject(new Error(e.message || "the worker failed")); pending.clear(); };
  const runtime = {}, transfer = [];
  if (!M.runtime) for (const el of document.querySelectorAll("script[data-runtime]")) {
    runtime[el.dataset.runtime] = (await bytes(el.textContent)).buffer;
    transfer.push(runtime[el.dataset.runtime]);
  }
  const decode = async (o) => Object.fromEntries(await Promise.all(Object.entries(o).map(async ([p, b]) => [p, (await bytes(b)).buffer])));
  const data = Object.fromEntries(await Promise.all(Object.values(M.data).map(async (d) => [d.path, (await bytes(d.bytes)).buffer])));
  state.status = `Loading Python and ${M.packages.length} packages…`; render();
  await call("init", {
    base: M.runtime && new URL(M.runtime, location.href).href, runtime, packages: M.packages,
    files: await decode(M.files), library: await decode(M.library), data, spec: S, baseline: M.baseline,
  }, transfer);
  state.status = "";
  state.busy = false;
  render();
}

// ------------------------------------------------------------------ running
const datasets = (n) => S.nodes[n].deps.filter((d) => d in S.datasets);
function stale() {
  const out = new Set();
  for (const n of S.order) {
    const r = state.results[n], ran = state.ran[n], node = S.nodes[n];
    if (!r || r.status !== "done" || !ran
      || Object.keys(node.settings).some((p) => JSON.stringify(state.settings[`${n}.${p}`]) !== JSON.stringify(ran.settings[p]))
      || datasets(n).some((d) => state.data[d].key !== ran.data[d])
      || node.deps.some((d) => out.has(d))) out.add(n);
  }
  return out;
}
function statusOf(n) {
  if (state.busy && state.running) return stale().has(n) ? "running" : "done";
  const r = state.results[n];
  if (!r) return "pending";
  if (r.status !== "done") return r.status;
  return stale().has(n) ? "stale" : "done";
}
const GLYPH = { pending: "○", stale: "↻", running: "…", done: "●", error: "✕", blocked: "–" };

async function run() {
  if (state.busy) return;
  state.busy = state.running = true; state.status = "Running…"; render();
  const data = Object.fromEntries(Object.entries(state.data).map(([d, v]) => [d, v.key]));
  try {
    const t0 = performance.now();
    const { nodes, record, differs } = await call("run", { settings: state.settings, data });
    state.previous = state.record;
    state.record = record;
    state.differs = differs;
    state.results = nodes;
    for (const [n, r] of Object.entries(nodes)) if (r.status === "done") state.ran[n] = { settings: r.settings, data };
    const ran = Object.values(nodes).filter((r) => r.status === "done" && !r.cached).length;
    state.status = `Ran ${ran} of ${S.order.length} in ${((performance.now() - t0) / 1000).toFixed(1)} s`;
  } catch (e) {
    state.status = `Failed: ${e.message}`;
  }
  state.busy = state.running = false;
  render();
  return state.record;
}

async function replaceData(d, file) {
  const buf = await file.arrayBuffer();
  await call("dataset", { path: M.data[d].path, buf });
  state.data[d] = { key: `${file.name}:${file.size}:${file.lastModified}`, size: file.size, file: file.name, blob: file };
  render();
}
const save = async (name, blob) => h("a", { href: URL.createObjectURL(await blob), download: name }).click();
const dataBlob = async (d) => state.data[d].blob || new Blob([await bytes(M.data[d].bytes)]);

// Data in and files out: a card with what the file is and a button that acts on it.
const card = (label, name, detail, ...buttons) => h("div", { class: "card" },
  h("div", {}, h("span", { class: "card-label" }, label), h("strong", {}, name), h("span", { class: "muted small" }, detail)), buttons);
const dataCard = (d) => card("Input", state.data[d].file || M.data[d].path.split("/").pop(),
  `${size(state.data[d].size)}${state.data[d].file ? " · replaced" : ""}`,
  h("label", { class: "button secondary" }, "Replace…", h("input", { type: "file", onchange: (e) => e.target.files[0] && replaceData(d, e.target.files[0]) })),
  h("button", { class: "secondary", onclick: () => save(state.data[d].file || M.data[d].path.split("/").pop(), dataBlob(d)) }, "Download"));

// ------------------------------------------------------------------ blocks
const COLORS = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)"];
const RENDER = {
  markdown: (b) => markdown(b.text),
  metrics: (b, n) => {
    const before = state.previous?.nodes[n]?.metrics || {}, base = M.baseline?.nodes[n]?.metrics || {};
    const delta = (it, ref) => {
      const v = num(it.value), r = num(ref);
      if (typeof v !== "number" || typeof r !== "number" || Math.abs(v - r) <= 1e-12 * Math.max(1, Math.abs(r))) return null;
      const better = it.goal === "min" ? v < r : it.goal === "max" ? v > r : null;
      return h("span", { class: `delta ${better === null ? "" : better ? "better" : "worse"}` }, `${v > r ? "+" : "−"}${fmt(Math.abs(v - r))}`);
    };
    const row = (it) => h("tr", { class: it.extra ? "extra" : null },
      h("th", {}, it.label), h("td", {}, fmt(it.value)), h("td", {}, delta(it, before[it.key])),
      M.baseline && h("td", { class: "muted" }, fmt(base[it.key])));
    const main = b.items.filter((it) => !it.extra), extra = b.items.filter((it) => it.extra);
    return h("div", { class: "metrics" }, b.title && h("h3", {}, b.title),
      h("table", {}, (state.previous || M.baseline) && h("tr", {}, h("th"), h("th"), h("th", {}, state.previous && "Δ last run"), M.baseline && h("th", {}, "baseline")),
        main.map(row)),
      extra.length > 0 && h("details", {}, h("summary", {}, `${extra.length} more numbers`), h("table", {}, extra.map(row))));
  },
  table: (b) => h("figure", { class: "table" }, b.title && h("figcaption", {}, b.title),
    h("div", { class: "scroll" }, h("table", {}, h("tr", {}, b.columns.map((c) => h("th", {}, c))),
      b.rows.map((r) => h("tr", {}, r.map((v) => h("td", { class: typeof num(v) === "number" ? "num" : null }, fmt(v))))))),
    h("p", { class: "muted small" }, b.total > b.rows.length ? `${b.rows.length} of ${fmt(b.total)} rows` : `${fmt(b.total)} rows × ${b.columns.length} columns`)),
  chart,
  figure: (b) => h("figure", {}, h("img", { src: b.media === "image/png" ? `data:image/png;base64,${b.data}` : `data:image/svg+xml,${encodeURIComponent(b.data)}`, alt: b.caption || "" }),
    b.caption && h("figcaption", {}, b.caption)),
  download: (b, label = "Output") => card(label, b.name, `${size(b.size)}${b.title ? ` · ${b.title}` : ""}`,
    h("button", { onclick: async () => save(b.name, new Blob([await bytes(b.data)], { type: b.media })) }, "Download")),
};

function ticks(lo, hi, n = 5) {
  const step = 10 ** Math.floor(Math.log10((hi - lo) / n || 1)), err = (hi - lo) / n / step;
  const s = step * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1);
  const out = [];
  for (let t = Math.ceil(lo / s) * s; t <= hi + s * 1e-9; t += s) out.push(+t.toPrecision(12));
  return out;
}
function chart(b) {
  const W = 640, H = 300, L = 52, R = 12, T = 12, B = 40;
  const xs = b.x.map(num), ys = b.series.flatMap((s) => s.y.map(num)).filter(Number.isFinite);
  const fx = xs.filter(Number.isFinite);
  if (!fx.length || !ys.length) return h("p", { class: "muted" }, "Nothing to plot.");
  let [x0, x1, y0, y1] = [Math.min(...fx), Math.max(...fx), Math.min(...ys), Math.max(...ys)];
  if (x0 === x1) { x0 -= 1; x1 += 1; }
  if (y0 === y1) { y0 -= 1; y1 += 1; }
  const pad = (y1 - y0) * 0.05; y0 -= pad; y1 += pad;
  const X = (v) => L + ((v - x0) / (x1 - x0)) * (W - L - R), Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const grid = [
    ...ticks(y0, y1).map((t) => [h("svg:line", { x1: L, x2: W - R, y1: Y(t), y2: Y(t), class: "grid" }),
      h("svg:text", { x: L - 6, y: Y(t) + 4, "text-anchor": "end" }, fmt(t))]),
    ...ticks(x0, x1).map((t) => h("svg:text", { x: X(t), y: H - B + 16, "text-anchor": "middle" }, fmt(t))),
    h("svg:line", { x1: L, x2: W - R, y1: H - B, y2: H - B, class: "axis" }),
    b.x_label && h("svg:text", { x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle", class: "label" }, b.x_label),
    b.y_label && h("svg:text", { x: 12, y: (T + H - B) / 2, "text-anchor": "middle", class: "label", transform: `rotate(-90 12 ${(T + H - B) / 2})` }, b.y_label),
  ];
  const marks = b.series.map((s, i) => {
    const pts = s.y.map((y, k) => [xs[k], num(y)]).filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y));
    const c = COLORS[i % COLORS.length];
    if (s.kind === "scatter") return h("svg:g", { fill: c }, pts.map(([x, y]) => h("svg:circle", { cx: X(x), cy: Y(y), r: 2.2 })));
    return h("svg:path", { d: pts.map(([x, y], k) => `${k ? "L" : "M"}${X(x).toFixed(1)},${Y(y).toFixed(1)}`).join(""), stroke: c, fill: "none", "stroke-width": 1.5 });
  });
  return h("figure", { class: "chart" }, b.title && h("figcaption", {}, b.title),
    h("svg:svg", { viewBox: `0 0 ${W} ${H}` }, grid, marks),
    b.series.length > 1 && h("p", { class: "legend" }, b.series.map((s, i) => h("span", {}, h("i", { style: `background:${COLORS[i % COLORS.length]}` }), s.name))));
}

// ------------------------------------------------------------------ the graph
function dag() {
  const nodeIds = [...Object.keys(S.datasets), ...S.order];
  const deps = (id) => (S.nodes[id] ? S.nodes[id].deps : []);
  const layer = {};
  for (const id of nodeIds) layer[id] = deps(id).length ? Math.max(...deps(id).map((d) => layer[d])) + 1 : 0;
  const rows = [];
  for (const id of nodeIds) (rows[layer[id]] ||= []).push(id);
  const W = 260, BH = 30, GAP = 34, M0 = 14, pos = {};
  rows.forEach((row, r) => row.forEach((id, i) => {
    const w = Math.min(180, (W - 2 * M0 - 8 * (row.length - 1)) / row.length);
    pos[id] = { x: (W - row.length * w - 8 * (row.length - 1)) / 2 + i * (w + 8), y: 10 + r * (BH + GAP), w };
  }));
  const H = 10 + rows.length * (BH + GAP) - GAP + 10;
  const edges = nodeIds.flatMap((id) => deps(id).map((d) => {
    const a = pos[d], b = pos[id], ax = a.x + a.w / 2, ay = a.y + BH, bx = b.x + b.w / 2, by = b.y, m = (ay + by) / 2;
    return h("svg:path", { d: `M${ax},${ay} C${ax},${m} ${bx},${m} ${bx},${by}`, class: `edge ${state.page === id || state.page === d ? "on" : ""}` });
  }));
  const boxes = nodeIds.map((id) => {
    const p = pos[id], isData = !S.nodes[id], st = isData ? "data" : statusOf(id);
    const label = id, fits = Math.floor((p.w - 8) / 6.4);
    return h("svg:g", { class: `box ${st} ${state.page === id ? "sel" : ""}`, onclick: () => show(id) },
      h("svg:title", {}, isData ? `${M.data[id].path}` : `${id}: ${st}`),
      h("svg:rect", { x: p.x, y: p.y, width: p.w, height: BH, rx: isData ? 15 : 3 }),
      h("svg:text", { x: p.x + p.w / 2, y: p.y + BH / 2 + 4, "text-anchor": "middle" }, label.length > fits ? label.slice(0, fits - 1) + "…" : label));
  });
  return h("svg:svg", { viewBox: `0 0 ${W} ${H}`, width: W, class: "dag" }, edges, boxes);
}

// ------------------------------------------------------------------ pages
function show(page) {
  state.page = page;
  history.replaceState(null, "", page ? `#${encodeURIComponent(page)}` : location.pathname + location.search);
  render();
  window.scrollTo(0, 0);
}

function control(n, p, s) {
  const key = `${n}.${p}`, v = state.settings[key];
  const set = (x) => { state.settings[key] = x; render(); };
  let input;
  if (s.choices) input = h("select", { onchange: (e) => set(s.choices[e.target.selectedIndex]) },
    s.choices.map((c) => h("option", { selected: c === v }, String(c))));
  else if (typeof s.default === "boolean") input = h("input", { type: "checkbox", checked: v, onchange: (e) => set(e.target.checked) });
  else if (typeof s.default === "number" && s.min != null && s.max != null) {
    const cast = (x) => (s.type === "int" ? Math.round(x) : +x.toPrecision(6));
    const [to, from] = s.log
      ? [(x) => (Math.log(x / s.min) / Math.log(s.max / s.min)) * 1000, (t) => cast(s.min * (s.max / s.min) ** (t / 1000))]
      : [(x) => x, cast];
    const out = h("output", {}, fmt(v));
    // While dragging, only the value and the graph's state change; the page re-renders on release.
    input = [h("input", { type: "range", min: to(s.min), max: to(s.max), step: s.log ? 1 : s.step || (s.type === "int" ? 1 : "any"), value: to(v),
      oninput: (e) => { state.settings[key] = from(+e.target.value); out.textContent = fmt(state.settings[key]); chrome(); },
      onchange: () => render() }), out];
  } else if (typeof s.default === "number") input = h("input", { type: "number", value: v, step: s.type === "int" ? 1 : "any", onchange: (e) => set(s.type === "int" ? parseInt(e.target.value, 10) : +e.target.value) });
  else input = h("input", { type: "text", value: v, onchange: (e) => set(e.target.value) });
  return h("label", { class: `setting ${v !== s.default ? "changed" : ""}` }, h("span", {}, p), input);
}

function results(n) {
  const r = state.results[n], st = statusOf(n);
  if (!r) return h("p", { class: "muted" }, "Not run yet.");
  const note = { stale: "Stale: settings or data changed since this ran. Run to update.", running: "Running…" }[st];
  if (r.status === "error") return h("pre", { class: "error" }, r.error);
  if (r.status === "blocked") return h("p", { class: "muted" }, `Blocked: ${r.error}.`);
  return h("div", { class: st === "stale" ? "dim" : null }, note && h("p", { class: "note" }, note),
    r.blocks.filter((b) => b.type !== "download").map((b) => (RENDER[b.type] ? RENDER[b.type](b, n) : h("pre", {}, JSON.stringify(b)))),
    h("p", { class: "muted small" }, `${r.cached ? "From the cache" : `Ran in ${r.seconds} s`} · ${r.key.slice(0, 10)}`),
    r.log && h("details", {}, h("summary", {}, "Log"), h("pre", {}, r.log)));
}

const offered = (n) => (state.results[n]?.status === "done" ? state.results[n].blocks.filter((b) => b.type === "download") : []);
const link = (x) => h("a", { href: `#${x}`, onclick: (e) => { e.preventDefault(); show(x); } }, x);
const sep = (xs) => xs.flatMap((x, i) => (i ? [", ", link(x)] : [link(x)]));
const crumb = (x) => h("p", { class: "crumb" }, h("a", { href: "#", onclick: (e) => { e.preventDefault(); show(null); } }, M.title), " / ", x);

function dataPage(d) {
  const readers = S.order.filter((m) => S.nodes[m].deps.includes(d));
  return [crumb(d), h("h1", {}, d), h("div", { class: "cards" }, dataCard(d)),
    h("p", { class: "muted" }, `${M.data[d].path} in the app. Read by `, sep(readers), ". A replacement is used from the next Run.")];
}

function nodePage(n) {
  const node = S.nodes[n], readers = S.order.filter((m) => S.nodes[m].deps.includes(n));
  const files = offered(n);
  return [
    crumb(n),
    h("h1", {}, n),
    node.doc ? markdown(node.doc) : null,
    datasets(n).length > 0 && h("p", { class: "muted" }, "Reads ", sep(datasets(n)), "."),
    h("div", { class: `cards ${statusOf(n) === "stale" ? "dim" : ""}` }, files.map((b) => RENDER.download(b))),
    Object.keys(node.settings).length > 0 && h("section", { class: "settings" }, h("h2", {}, "Settings"),
      Object.entries(node.settings).map(([p, s]) => control(n, p, s))),
    h("section", {}, h("h2", {}, "Results"), results(n)),
    h("details", { class: "about" }, h("summary", {}, "Code"),
      h("p", { class: "muted" }, node.deps.length ? ["Reads ", sep(node.deps)] : "Reads nothing", readers.length ? [". Read by ", sep(readers), "."] : "."),
      h("pre", {}, text(M.files[node.file]))),
  ];
}

function overview() {
  const failing = state.differs;
  return [
    h("h1", {}, M.title),
    M.about && markdown(M.about),
    h("section", {}, h("h2", {}, "Nodes"), h("ol", { class: "nodes" }, S.order.map((n) => {
      const st = statusOf(n), m = state.results[n]?.metrics || {}, decl = S.nodes[n].metrics.slice(0, 3);
      return h("li", {}, h("a", { href: `#${n}`, onclick: (e) => { e.preventDefault(); show(n); } }, n),
        h("span", { class: `status ${st}` }, ` ${GLYPH[st]} ${st}`),
        h("p", {}, (S.nodes[n].doc.split("\n")[0] || "")),
        decl.length > 0 && h("p", { class: "small muted" }, decl.map((d) => `${d.label} ${fmt(m[d.key])}`).join(" · ")));
    }))),
    // The app's front door: everything that goes in and everything that comes out.
    Object.keys(M.data).length > 0 && h("section", {}, h("h2", {}, "Inputs"), h("div", { class: "cards" }, Object.keys(M.data).map(dataCard))),
    S.order.some((n) => S.nodes[n].downloads) && h("section", {}, h("h2", {}, "Outputs"),
      S.order.some((n) => offered(n).length) ? h("div", { class: "cards" }, S.order.map((n) => h("div", { class: `cards ${statusOf(n) === "stale" ? "dim" : ""}` },
        offered(n).map((b) => RENDER.download(b, `Output · ${n}`)))))
        : h("p", { class: "muted" }, "Run to make the files.")),
    state.record && h("section", {}, h("h2", {}, "This run"),
      failing === null ? h("p", { class: "muted" }, "No baseline to compare with.")
        : Object.keys(failing).length === 0 ? h("p", { class: "ok" }, "Every node matches the baseline.")
          : h("ul", { class: "differs" }, Object.entries(failing).map(([n, why]) => h("li", {}, h("strong", {}, n), `: ${why.join("; ")}`))),
      h("p", {}, h("a", { href: "#", onclick: (e) => { e.preventDefault(); h("a", { href: URL.createObjectURL(new Blob([JSON.stringify(state.record, null, 1)], { type: "application/json" })), download: "run.json" }).click(); } }, "↓ run.json"),
        h("span", { class: "muted" }, " the run's record: settings, data and every node's metrics and digest"))),
  ];
}

// ------------------------------------------------------------------ render
function chrome() {
  document.querySelector("header").replaceChildren(
    h("a", { class: "title", href: "#", onclick: (e) => { e.preventDefault(); show(null); } }, M.title),
    h("span", { class: "status-text" }, state.status),
    h("button", { onclick: run, disabled: state.busy }, "Run"));
  document.querySelector("nav").replaceChildren(dag());
}
function render() {
  chrome();
  document.querySelector("main article").replaceChildren(...[S.nodes[state.page] ? nodePage(state.page) : M.data[state.page] ? dataPage(state.page) : overview()].flat(Infinity).filter(Boolean));
}

window.addEventListener("hashchange", () => { state.page = decodeURIComponent(location.hash.slice(1)) || null; render(); });

// For agents (and the tooling): the page's state and its two actions.
window.blocks = {
  state: () => ({ status: state.status, busy: state.busy, settings: state.settings, stale: [...stale()], results: state.results, record: state.record }),
  set: (values) => { Object.assign(state.settings, values); render(); return [...stale()]; },
  run,
  output: (node) => call("output", { name: node }),
  show,
  ready: null,
};
document.getElementById("app").append(h("header"), h("nav"), h("main", {}, h("article")));
render();
window.blocks.ready = startWorker().catch((e) => { state.status = `Failed to start: ${e.message}`; render(); throw e; });
