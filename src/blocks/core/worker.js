// The Python worker. The page prepends Pyodide's two modules (as one classic script, so it
// also starts from a file:// page), which put `_createPyodideModule` and `__pyodide` in scope.
// Runtime files come from the page (inline builds) or the dev server (linked builds).

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
  for (const [path, buf] of Object.entries(files)) {
    const full = `${root}/${path}`;
    py.FS.mkdirTree(full.slice(0, full.lastIndexOf("/")));
    py.FS.writeFile(full, new Uint8Array(buf));
  }
};

const handlers = {
  async init({ base, runtime, packages, files, library, data, spec, baseline }) {
    for (const [name, buf] of Object.entries(runtime || {})) embedded.set(name, new Uint8Array(buf));
    base = base || EMBED;
    py = await __pyodide.loadPyodide({
      indexURL: base, packageBaseUrl: base, stdLibURL: base + "python_stdlib.zip", createPyodideModule: _createPyodideModule,
      lockFileContents: await (await fetch(base + "pyodide-lock.json")).json(),
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
    write("/app", data);
    py.runPython("import sys; sys.path.insert(0, '/lib')");
    graph = py.pyimport("blocks.core.graph");
    graph.start("/app", JSON.stringify(spec), JSON.stringify(baseline));
    return py.runPython("import sys; sys.version.split()[0]");
  },
  // A replacement, whole: a folder's old files go first.
  dataset({ path, files }) {
    const clear = (dir) => py.FS.readdir(dir).filter((n) => n !== "." && n !== "..").forEach((n) => {
      const p = `${dir}/${n}`;
      if (py.FS.isDir(py.FS.stat(p).mode)) { clear(p); py.FS.rmdir(p); } else py.FS.unlink(p);
    });
    if (path.endsWith("/") && py.FS.analyzePath(`/app/${path}`).exists) clear(`/app/${path.slice(0, -1)}`);
    write("/app", files);
  },
  run({ settings, data }) { return JSON.parse(graph.run_json(JSON.stringify(settings), JSON.stringify(data))); },
  output({ name }) { return JSON.parse(graph.output_json(name)); },
};

self.onmessage = async ({ data: { id, type, ...args } }) => {
  try { self.postMessage({ id, ok: true, result: await handlers[type](args) }); }
  catch (e) { self.postMessage({ id, ok: false, error: String((e && e.message) || e) }); }
};
