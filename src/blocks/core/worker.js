// The Python worker. The build puts Pyodide before it (build.worker_script), which brings
// `_createPyodideModule` and `__pyodide` into scope. Runtime files come from the page (an
// offline build) or the dev server (a served one).

const EMBED = "https://embedded.invalid/";
const embedded = new Map();
const realFetch = fetch;
globalThis.fetch = async (url, init) => {
  url = String(url.url || url);
  if (!url.startsWith(EMBED)) return realFetch(url, init);
  const data = embedded.get(url.slice(EMBED.length));
  if (!data) throw new Error(`not embedded: ${url}`);
  return new Response(data, { headers: { "Content-Type": url.endsWith(".wasm") ? "application/wasm" : "application/octet-stream" } });
};

let py, graph;
const write = (root, files) => {
  for (const [path, data] of Object.entries(files)) {
    const full = `${root}/${path}`;
    py.FS.mkdirTree(full.slice(0, full.lastIndexOf("/")));
    py.FS.writeFile(full, new Uint8Array(data));
  }
};

const handlers = {
  async init({ base, runtime, packages, files, library, spec }) {
    for (const [name, data] of Object.entries(runtime)) embedded.set(name, data);
    base = base || EMBED;
    py = await __pyodide.loadPyodide({
      indexURL: base, packageBaseUrl: base, createPyodideModule: _createPyodideModule,
      env: { HOME: "/home/pyodide", PYTHONHASHSEED: "0", MPLBACKEND: "Agg" },
    });
    // Pyodide reports a package that failed to load and carries on; here it fails the start,
    // after one retry (a fetch can fail under load), rather than as a ModuleNotFoundError later.
    for (let tries = 2; tries--;) {
      const failed = [];
      await py.loadPackage(packages, { messageCallback: () => {}, errorCallback: (m) => failed.push(m) });
      if (!failed.length) break;
      if (!tries) throw new Error(`packages failed to load: ${failed.join(" ")}`);
    }
    embedded.clear();
    write("/app", files);
    write("/lib", library);
    py.runPython("import sys; sys.path.insert(0, '/lib')");
    graph = py.pyimport("blocks.core.graph");
    graph.start("/app", JSON.stringify(spec));
    return py.runPython("import sys; sys.version.split()[0]");
  },
  // A dataset, whole: a folder's old files go first (a folder dataset holds only files).
  dataset({ path, files }) {
    const folder = `/app/${path}`;
    if (path.endsWith("/") && py.FS.analyzePath(folder).exists) {
      for (const name of py.FS.readdir(folder)) if (name !== "." && name !== "..") py.FS.unlink(folder + name);
    }
    write("/app", files);
  },
  run: (args) => JSON.parse(graph.run_json(JSON.stringify(args))),
  explore: (args) => JSON.parse(graph.explore_json(JSON.stringify(args))),
  output({ name }) { return JSON.parse(graph.output_json(name)); },
};

self.onmessage = async ({ data: { id, type, ...args } }) => {
  try { self.postMessage({ id, ok: true, result: await handlers[type](args) }); }
  catch (e) { self.postMessage({ id, ok: false, error: String((e && e.message) || e) }); }
};
