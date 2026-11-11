// The page: the graph on the left (its table of contents), one page of blocks on the right: the
// overview, a node (its docstring, settings, results and code) or a dataset. Python runs in a
// worker (worker.js); Run computes what is stale, and the graph's cache keeps the rest.

const M = JSON.parse(document.getElementById("manifest").textContent);
const S = M.spec;
const bytes = async (b64) => new Uint8Array(await (await fetch(`data:application/octet-stream;base64,${b64}`)).arrayBuffer());
const text = (b64) => new TextDecoder().decode(Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));
// {path: base64} as {path: bytes}
const unpack = async (files) => Object.fromEntries(await Promise.all(Object.entries(files).map(async ([p, b]) => [p, await bytes(b)])));

const state = {
  page: null,      // a node's or a dataset's name, or null: the overview
  // name -> value. A setting is the app's, by its name: every node that declares it reads it.
  settings: Object.fromEntries(S.order.flatMap((n) => Object.entries(S.nodes[n].settings).map(([p, s]) => [p, s.default]))),
  data: {},        // dataset -> {key, files: {path: Blob}, chosen}, once Python has its files
  results: {},     // node -> its result in the last run
  record: null,    // the last run's record
  previous: null,  // the one before it
  differs: null,   // {node: [what differs]} from the baseline (graph.compare); null without one
  ranWith: null,   // the settings and data keys the last run had
  status: "Starting Python…",
  ready: false,    // Python has started
  running: false,
};
const busy = () => !state.ready || state.running;

// DOM:
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

// The worker:
let worker, seq = 0;
const pending = new Map();
const call = (type, args = {}, transfer = []) => new Promise((resolve, reject) => {
  pending.set(++seq, { resolve, reject });
  worker.postMessage({ id: seq, type, ...args }, transfer);
});
async function startWorker() {
  // The worker's script is Pyodide and worker.js, joined by the build (build.worker_script).
  worker = new Worker(URL.createObjectURL(new Blob([document.getElementById("worker").textContent], { type: "text/javascript" })));
  worker.onmessage = ({ data: { id, ok, result, error } }) => {
    const p = pending.get(id); pending.delete(id);
    ok ? p.resolve(result) : p.reject(new Error(error));
  };
  worker.onerror = (e) => { for (const p of pending.values()) p.reject(new Error(e.message || "the worker failed")); pending.clear(); };
  // An offline page holds the runtime; a served one leaves the worker to fetch it from M.runtime.
  const runtime = {};
  for (const el of document.querySelectorAll("script[data-runtime]")) runtime[el.dataset.runtime] = await bytes(el.textContent);
  state.status = `Loading Python and ${M.packages.length} packages…`; render();
  await call("init", {
    base: M.runtime && new URL(M.runtime, location.href).href, runtime, packages: M.packages,
    files: await unpack(M.files), library: await unpack(M.library), spec: S,
  }, Object.values(runtime).map((b) => b.buffer));
  for (const [d, { files }] of Object.entries(M.data)) {
    if (files) await putData(d, Object.fromEntries(Object.entries(await unpack(files)).map(([p, b]) => [p, new Blob([b])])), false);
  }
  state.ready = true; state.status = ""; render();
}

// Running:
const datasets = (n) => S.nodes[n].deps.filter((d) => d in S.datasets);
const missing = () => Object.keys(S.datasets).filter((d) => !state.data[d]);
// What Run would compute. The worker keys each output by its code, settings and inputs; in a
// page the code is fixed, so a node is stale when it did not run, its settings or data changed
// since the last run, or a node it reads is stale.
function stale() {
  const out = new Set(), last = state.ranWith;
  for (const n of S.order) {
    const r = state.results[n], node = S.nodes[n];
    if (!r || r.status !== "done"
      || Object.keys(node.settings).some((p) => JSON.stringify(state.settings[p]) !== JSON.stringify(last.settings[p]))
      || datasets(n).some((d) => state.data[d]?.key !== last.data[d])
      || node.deps.some((d) => out.has(d))) out.add(n);
  }
  return out;
}
function statusOf(n) {
  if (state.running) return stale().has(n) ? "running" : "done";
  const r = state.results[n];
  if (!r) return "pending";
  if (r.status !== "done") return r.status;
  return stale().has(n) ? "stale" : "done";
}
const GLYPH = { pending: "○", stale: "↻", running: "…", done: "●", error: "✕", blocked: "–" };

// Returns the run record, or throws when the run itself failed (a node's failure is in the record).
async function run() {
  if (busy()) throw new Error("Python is starting or running");
  if (missing().length) {
    state.status = `Choose ${missing().join(", ")} to run`; render();
    throw new Error(state.status);
  }
  const sent = { settings: { ...state.settings }, data: Object.fromEntries(Object.entries(state.data).map(([d, v]) => [d, v.key])) };
  state.running = true; state.status = "Running…"; render();
  const t0 = performance.now();
  try {
    const { nodes, record, differs } = await call("run", { ...sent, baseline: M.baseline });
    Object.assign(state, { previous: state.record, record, differs, results: nodes, ranWith: sent });
    const ran = Object.values(nodes).filter((r) => r.status === "done" && !r.cached).length;
    state.status = `Ran ${ran} of ${S.order.length} in ${((performance.now() - t0) / 1000).toFixed(1)} s`;
  } catch (e) {
    state.status = `Failed: ${e.message}`;
    throw e;
  } finally {
    state.running = false;
    render();
  }
  return state.record;
}

// Data in, files out:
const sha = async (buf) => [...new Uint8Array(await crypto.subtle.digest("SHA-256", buf))].map((b) => b.toString(16).padStart(2, "0")).join("");
// A dataset's key: its file's sha256, or a folder's over each file's name and sha256. The same
// bytes (and names) are the same data.
async function dataKey(path, bufs) {
  if (!path.endsWith("/")) return sha(bufs[path]);
  const sums = await Promise.all(Object.keys(bufs).sort().map(async (p) => `${p.slice(path.length)}\0${await sha(bufs[p])}\n`));
  return sha(new TextEncoder().encode(sums.join("")));
}
// Give Python a dataset's files ({path: Blob}), all of them, in place of what it had.
async function putData(d, files, chosen) {
  const path = S.datasets[d];
  const bufs = Object.fromEntries(await Promise.all(Object.entries(files).map(async ([p, f]) => [p, await f.arrayBuffer()])));
  await call("dataset", { path, files: bufs });
  state.data[d] = { key: await dataKey(path, bufs), files, chosen };
  render();
}
// The files a reader chose for a dataset: one file, or a folder's files, by their names.
function choose(d, chosen) {
  const path = S.datasets[d];
  return putData(d, Object.fromEntries(path.endsWith("/") ? chosen.map((f) => [path + f.name, f]) : [[path, chosen[0]]]), true);
}
const save = (name, blob) => h("a", { href: URL.createObjectURL(blob), download: name }).click();

// A card: what a file is, and buttons that act on it.
const card = (label, name, detail, ...buttons) => h("div", { class: "card" },
  h("div", {}, h("span", { class: "card-label" }, label), h("strong", {}, name), h("span", { class: "muted small" }, detail)), buttons);
function dataCard(d) {
  const v = state.data[d], path = S.datasets[d], folder = path.endsWith("/");
  let detail = M.data[d].files ? "" : `Not in this page: choose ${folder ? "its files" : "the file"} to run`;
  if (v) {
    const files = Object.values(v.files);
    detail = `${folder ? `${files.length} files · ` : ""}${size(files.reduce((n, f) => n + f.size, 0))}${v.chosen ? " · chosen here" : ""}`;
  }
  return card("Input", path.slice("data/".length), detail,
    h("label", { class: `button secondary ${busy() ? "disabled" : ""}` }, v ? "Replace…" : "Choose…",
      h("input", { type: "file", multiple: folder, "data-dataset": d, disabled: busy(), onchange: (e) => e.target.files.length && choose(d, [...e.target.files]) })),
    v && h("button", { class: "secondary", onclick: () => Object.entries(v.files).forEach(([p, f]) => save(p.split("/").pop(), f)) }, "Download"));
}

// Blocks:
// The kit a block's renderer may use, all of it here: h, fmt, num, size, markdown, card, save,
// bytes; paint(block, node), to draw a block's own blocks; S, the app's spec; records(), the
// page's run, last run and baseline; the classes muted, small, note and error; and ui/_kit.js.
// The build puts ui/_kit.js and then each block's script, in its own scope, at the marker.
const RENDER = {};
const records = () => ({ run: state.record, last: state.previous, baseline: M.baseline });
// @blocks

// The graph:
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

// Pages:
// Links are plain #name anchors; the hashchange listener below shows the page they name.
function show(page) {
  state.page = page;
  history.replaceState(null, "", page ? `#${encodeURIComponent(page)}` : location.pathname + location.search);
  render();
  window.scrollTo(0, 0);
}
const link = (x) => h("a", { href: `#${encodeURIComponent(x)}` }, x);
const sep = (xs) => xs.flatMap((x, i) => (i ? [", ", link(x)] : [link(x)]));
const crumb = (x) => h("p", { class: "crumb" }, h("a", { href: "#" }, M.title), " / ", x);

function control(n, p, s) {
  const v = state.settings[p];
  const set = (x) => { state.settings[p] = x; render(); };
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
      oninput: (e) => { state.settings[p] = from(+e.target.value); out.textContent = fmt(state.settings[p]); chrome(); },
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
const readersOf = (x) => S.order.filter((m) => S.nodes[m].deps.includes(x));

function dataPage(d) {
  return [crumb(d), h("h1", {}, d), M.data[d].doc && markdown(M.data[d].doc), h("div", { class: "cards" }, dataCard(d)),
    h("p", { class: "muted" }, `${S.datasets[d]} in the app${S.datasets[d].endsWith("/") ? ", whose files its readers get by name" : ""}. Read by `,
      sep(readersOf(d)), ". A replacement, all of it, is used from the next Run.")];
}

// The other nodes that read setting p: a setting is the app's, by its name.
const alsoReading = (n, p) => S.order.filter((m) => m !== n && p in S.nodes[m].settings);

function nodePage(n) {
  const node = S.nodes[n], readers = readersOf(n);
  return [
    crumb(n),
    h("h1", {}, n),
    node.doc ? markdown(node.doc) : null,
    datasets(n).length > 0 && h("p", { class: "muted" }, "Reads ", sep(datasets(n)), "."),
    Object.keys(node.settings).length > 0 && h("section", { class: "settings" }, h("h2", {}, "Settings"),
      Object.entries(node.settings).map(([p, s]) => control(n, p, s)),
      Object.keys(node.settings).filter((p) => alsoReading(n, p).length)
        .map((p) => h("p", { class: "muted small" }, `${p} is also read by `, sep(alsoReading(n, p)), "."))),
    h("section", {}, h("h2", {}, "Results"), results(n)),
    h("details", { class: "about" }, h("summary", {}, "Code"),
      h("p", { class: "muted" }, node.deps.length ? ["Reads ", sep(node.deps)] : "Reads nothing", readers.length ? [". Read by ", sep(readers), "."] : "."),
      code(node)),
  ];
}

// The node's file, top to bottom, with each step (spec.read_node's) under its name and what it says it is.
function code(node) {
  const lines = text(M.files[node.file]).replace(/\n$/, "").split("\n"), out = [];
  const pre = (a, b) => { const t = lines.slice(a, b).join("\n"); if (t.trim()) out.push(h("pre", {}, t.replace(/^\n+|\s+$/g, ""))); };
  let at = 0;
  for (const s of node.steps) {
    pre(at, s.lines[0] - 1);
    out.push(h("p", { class: "step" }, h("code", {}, s.name), " ", s.summary));
    pre(s.lines[0] - 1, at = s.lines[1]);
  }
  pre(at, lines.length);
  return out;
}

function overview() {
  const differs = state.differs;
  return [
    h("h1", {}, M.title),
    M.about && markdown(M.about),
    h("section", {}, h("h2", {}, "Nodes"), h("ol", { class: "nodes" }, S.order.map((n) => {
      const st = statusOf(n), m = state.results[n]?.metrics || {}, decl = S.nodes[n].metrics.slice(0, 3);
      return h("li", {}, link(n), h("span", { class: `status ${st}` }, ` ${GLYPH[st]} ${st}`),
        h("p", {}, S.nodes[n].summary),
        decl.length > 0 && h("p", { class: "small muted" }, decl.map((d) => `${d.label} ${fmt(m[d.key], d.percent)}`).join(" · ")));
    }))),
    // The app's front door: everything that goes in and everything that comes out.
    Object.keys(S.datasets).length > 0 && h("section", {}, h("h2", {}, "Inputs"), h("div", { class: "cards" }, Object.keys(S.datasets).map(dataCard))),
    S.order.some((n) => offered(n).length) && h("section", {}, h("h2", {}, "Outputs"),
      h("div", { class: "cards" }, S.order.map((n) => h("div", { class: `cards ${statusOf(n) === "stale" ? "dim" : ""}` },
        offered(n).map((b) => RENDER.download(b, n, `Output · ${n}`)))))),
    state.record && h("section", {}, h("h2", {}, "This run"),
      differs === null ? h("p", { class: "muted" }, "No baseline to compare with.")
        : Object.keys(differs).length === 0 ? h("p", { class: "ok" }, "Every node matches the baseline.")
          : h("ul", { class: "differs" }, Object.entries(differs).map(([n, why]) => h("li", {}, h("strong", {}, n), `: ${why.join("; ")}`))),
      h("p", {}, h("a", { href: URL.createObjectURL(new Blob([JSON.stringify(state.record, null, 1)])), download: "run.json" }, "↓ run.json"),
        h("span", { class: "muted" }, " the run's record: settings, data and every node's metrics and digest"))),
  ];
}

// Render:
function chrome() {
  document.querySelector("header").replaceChildren(
    h("a", { class: "title", href: "#" }, M.title),
    h("span", { class: "status-text" }, state.status),
    h("button", { onclick: () => run().catch(() => {}), disabled: busy() }, "Run"));
  document.querySelector("nav").replaceChildren(dag());
}
function render() {
  chrome();
  const page = S.nodes[state.page] ? nodePage(state.page) : S.datasets[state.page] ? dataPage(state.page) : overview();
  document.querySelector("main article").replaceChildren(...page.flat(Infinity).filter(Boolean));
}

// For agents (and the tooling): the page's state and what it can do.
window.blocks = {
  state: () => ({ status: state.status, busy: busy(), settings: state.settings, stale: [...stale()], missing: missing(), results: state.results, record: state.record }),
  set: (values) => {
    const unknown = Object.keys(values).filter((p) => !(p in state.settings));
    if (unknown.length) throw new Error(`no setting ${unknown.join(", ")} (the settings: ${Object.keys(state.settings).join(", ")})`);
    Object.assign(state.settings, values); render(); return [...stale()];
  },
  run,
  output: (node) => call("output", { name: node }),
  show,
  ready: null,
};
const hashPage = () => decodeURIComponent(location.hash.slice(1)) || null;
window.addEventListener("hashchange", () => show(hashPage()));
document.getElementById("app").append(h("header"), h("nav"), h("main", {}, h("article")));
show(hashPage());
window.blocks.ready = startWorker().catch((e) => { state.status = `Failed to start: ${e.message}`; render(); throw e; });
