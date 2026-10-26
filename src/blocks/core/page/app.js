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
  // dataset -> {key, size, files}: files are the ones chosen here ({path: File}), else the page's.
  // A page built without its data has no key until they are chosen.
  data: Object.fromEntries(Object.entries(M.data).map(([d, v]) => [d, { key: v.key, size: v.size, files: null }])),
  results: {},   // node -> its result in the last run
  record: null,  // the last run's record
  differs: null, // {node: [what differs]} from the baseline (core/graph.py compare); null without one
  previous: null,
  ran: {},       // node -> {settings, data} it last ran with
  status: "Starting Python…",
  busy: true,     // the worker is starting or running
  running: false, // a run is going
};

// ------------------------------------------------------------------ DOM
function h(tag, attrs = {}, ...kids) {
  const svg = tag.startsWith("svg:");
  const el = svg ? document.createElementNS("http://www.w3.org/2000/svg", tag.slice(4)) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  el.append(...kids.flat(Infinity).filter((k) => k != null && k !== false));
  return el;
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const num = (v) => (v === "NaN" ? NaN : v === "Infinity" ? Infinity : v === "-Infinity" ? -Infinity : v);
// Every number is a quantity here. One that names something (a year, a code) reaches the page as
// text, and a share has percent set (0.706 reads 70.6%), because its block's Python was told so.
function fmt(v, percent) {
  v = num(v);
  if (percent && Number.isFinite(v)) return `${fmt(100 * v)}%`;
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
      out.push(`<h${n}>${inline(l.slice(n + 1))}</h${n}>`); i++;
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
  const data = await decode(Object.assign({}, ...Object.values(M.data).map((v) => v.files || {})));
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
// What Run would compute. The worker keys each output by its code, settings and inputs; in a
// built page the code is fixed, so a node is stale exactly when its settings or data changed
// since it ran, or a node it reads is stale.
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

// Returns the run record, or throws when the run itself failed (a node's failure is in the record).
async function run() {
  if (state.busy) throw new Error("a run is already going");
  if (missing().length) {
    state.status = `Choose ${missing().join(", ")} to run`; render();
    throw new Error(state.status);
  }
  let failed = null;
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
    failed = e;
  }
  state.busy = state.running = false;
  render();
  if (failed) throw failed;
  return state.record;
}

const missing = () => Object.keys(state.data).filter((d) => state.data[d].key == null);
const sha = async (buf) => [...new Uint8Array(await crypto.subtle.digest("SHA-256", buf))].map((b) => b.toString(16).padStart(2, "0")).join("");
// A dataset's key, as spec.data_key computes it: the same bytes (and names) are the same data.
async function dataKey(path, bufs) {
  if (!path.endsWith("/")) return sha(bufs[path]);
  const sums = await Promise.all(Object.keys(bufs).sort().map(async (p) => `${p.slice(path.length)}\0${await sha(bufs[p])}\n`));
  return sha(new TextEncoder().encode(sums.join("")));
}
// Replace a dataset whole: a file, or every file of a folder (its old files go).
async function replaceData(d, chosen) {
  const path = S.datasets[d], folder = path.endsWith("/");
  const files = Object.fromEntries((folder ? chosen : chosen.slice(0, 1)).map((f) => [folder ? path + f.name : path, f]));
  const bufs = Object.fromEntries(await Promise.all(Object.entries(files).map(async ([p, f]) => [p, await f.arrayBuffer()])));
  const key = await dataKey(path, bufs);
  await call("dataset", { path, files: bufs });
  state.data[d] = { key, size: Object.values(files).reduce((n, f) => n + f.size, 0), files };
  render();
}
const save = async (name, blob) => h("a", { href: URL.createObjectURL(await blob), download: name }).click();
// [path, Blob] for each of a dataset's files: those chosen here, or the page's own.
const dataFiles = (d) => (state.data[d].files ? Object.entries(state.data[d].files)
  : Object.entries(M.data[d].files || {}).map(([p, b]) => [p, bytes(b).then((u) => new Blob([u]))]));

// Data in and files out: a card with what the file is and a button that acts on it.
const card = (label, name, detail, ...buttons) => h("div", { class: "card" },
  h("div", {}, h("span", { class: "card-label" }, label), h("strong", {}, name), h("span", { class: "muted small" }, detail)), buttons);
function dataCard(d) {
  const v = state.data[d], path = S.datasets[d], folder = path.endsWith("/"), count = Object.keys(v.files || M.data[d].files || {}).length;
  const name = folder ? path.slice("data/".length) : (v.files ? Object.values(v.files)[0].name : path.split("/").pop());
  const detail = v.key == null ? `Not in this page: choose ${folder ? "its files" : "the file"} to run`
    : `${folder ? `${count} files · ` : ""}${size(v.size)}${v.files ? " · chosen here" : ""}`;
  return card("Input", name, detail,
    h("label", { class: `button secondary ${state.busy ? "disabled" : ""}` }, v.key == null ? "Choose…" : "Replace…",
      h("input", { type: "file", multiple: folder, "data-dataset": d, disabled: state.busy, onchange: (e) => e.target.files.length && replaceData(d, [...e.target.files]) })),
    v.key != null && h("button", { class: "secondary", onclick: () => dataFiles(d).forEach(([p, b]) => save(v.files ? b.name : p.split("/").pop(), b)) }, "Download"));
}

// ------------------------------------------------------------------ blocks
// The kit a block's renderer may use, all of it here: h, fmt, num, size, markdown, card, save,
// bytes; paint(block, node), to draw a block's own blocks; S, the app's spec; records(), the
// page's run, last run and baseline; the classes muted, small, note and error; and ui/_kit.js.
// The build puts ui/_kit.js and then each block's script, in its own scope, at the marker.
const RENDER = {};
const records = () => ({ run: state.record, last: state.previous, baseline: M.baseline });
// @blocks

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
    const fits = Math.floor((p.w - 8) / 6.4);
    return h("svg:g", { class: `box ${st} ${state.page === id ? "sel" : ""}`, onclick: () => show(id) },
      h("svg:title", {}, isData ? `${S.datasets[id]}` : `${id}: ${st}`),
      h("svg:rect", { x: p.x, y: p.y, width: p.w, height: BH, rx: isData ? 15 : 3 }),
      h("svg:text", { x: p.x + p.w / 2, y: p.y + BH / 2 + 4, "text-anchor": "middle" }, id.length > fits ? id.slice(0, fits - 1) + "…" : id));
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

// A block, or why it could not be drawn (marked, so that verify finds it).
function paint(b, n) {
  try {
    if (!RENDER[b.type]) throw new Error(`no renderer for "${b.type}"`);
    return RENDER[b.type](b, n);
  } catch (e) {
    return h("pre", { class: "error", "data-failed": b.type }, `The ${b.type} block failed: ${e.message}`);
  }
}

function results(n) {
  const r = state.results[n], st = statusOf(n);
  if (!r) return h("p", { class: "muted" }, "Not run yet.");
  const note = { stale: "Stale: settings or data changed since this ran. Run to update.", running: "Running…" }[st];
  if (r.status === "error") return h("pre", { class: "error" }, r.error);
  if (r.status === "blocked") return h("p", { class: "muted" }, `Blocked: ${r.error}.`);
  return h("div", { class: st === "stale" ? "dim" : null }, note && h("p", { class: "note" }, note),
    r.view_error && [h("p", {}, "The node ran; its view failed:"), h("pre", { class: "error" }, r.view_error)],
    r.blocks.map((b) => paint(b, n)),
    h("p", { class: "muted small" }, `${r.cached ? "From the cache" : `Ran in ${r.seconds} s`} · ${r.key.slice(0, 10)}`),
    r.log && h("details", {}, h("summary", {}, "Log"), h("pre", {}, r.log)));
}

// A block's own blocks are in its "blocks" field (ui.row's); downloads inside them count too.
const within = (b) => [b, ...(b.blocks || []).flatMap(within)];
const offered = (n) => (state.results[n]?.status === "done" ? state.results[n].blocks.flatMap(within).filter((b) => b.type === "download") : []);
const link = (x) => h("a", { href: `#${x}`, onclick: (e) => { e.preventDefault(); show(x); } }, x);
const sep = (xs) => xs.flatMap((x, i) => (i ? [", ", link(x)] : [link(x)]));
const crumb = (x) => h("p", { class: "crumb" }, h("a", { href: "#", onclick: (e) => { e.preventDefault(); show(null); } }, M.title), " / ", x);

function dataPage(d) {
  const readers = S.order.filter((m) => S.nodes[m].deps.includes(d));
  return [crumb(d), h("h1", {}, d), h("div", { class: "cards" }, dataCard(d)),
    h("p", { class: "muted" }, `${S.datasets[d]} in the app${S.datasets[d].endsWith("/") ? ", whose files its readers get by name" : ""}. Read by `,
      sep(readers), ". A replacement, all of it, is used from the next Run.")];
}

function nodePage(n) {
  const node = S.nodes[n], readers = S.order.filter((m) => S.nodes[m].deps.includes(n));
  return [
    crumb(n),
    h("h1", {}, n),
    node.doc ? markdown(node.doc) : null,
    datasets(n).length > 0 && h("p", { class: "muted" }, "Reads ", sep(datasets(n)), "."),
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
        decl.length > 0 && h("p", { class: "small muted" }, decl.map((d) => `${d.label} ${fmt(m[d.key], d.percent)}`).join(" · ")));
    }))),
    // The app's front door: everything that goes in and everything that comes out.
    Object.keys(M.data).length > 0 && h("section", {}, h("h2", {}, "Inputs"), h("div", { class: "cards" }, Object.keys(M.data).map(dataCard))),
    S.order.some((n) => offered(n).length) && h("section", {}, h("h2", {}, "Outputs"),
      h("div", { class: "cards" }, S.order.map((n) => h("div", { class: `cards ${statusOf(n) === "stale" ? "dim" : ""}` },
        offered(n).map((b) => RENDER.download(b, n, `Output · ${n}`)))))),
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
    h("button", { onclick: () => run().catch(() => {}), disabled: state.busy }, "Run"));
  document.querySelector("nav").replaceChildren(dag());
}
function render() {
  chrome();
  document.querySelector("main article").replaceChildren(...[S.nodes[state.page] ? nodePage(state.page) : M.data[state.page] ? dataPage(state.page) : overview()].flat(Infinity).filter(Boolean));
}

window.addEventListener("hashchange", () => { state.page = decodeURIComponent(location.hash.slice(1)) || null; render(); });

// For agents (and the tooling): the page's state and its two actions.
window.blocks = {
  state: () => ({ status: state.status, busy: state.busy, settings: state.settings, stale: [...stale()], missing: missing(), results: state.results, record: state.record }),
  set: (values) => { Object.assign(state.settings, values); render(); return [...stale()]; },
  run,
  output: (node) => call("output", { name: node }),
  show,
  ready: null,
};
document.getElementById("app").append(h("header"), h("nav"), h("main", {}, h("article")));
render();
window.blocks.ready = startWorker().catch((e) => { state.status = `Failed to start: ${e.message}`; render(); throw e; });
