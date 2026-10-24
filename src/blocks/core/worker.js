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
    await py.loadPackage(packages, { messageCallback: () => {} });
    embedded.clear();
    write("/app", files);
    write("/lib", library);
    write("/app", data);
    py.runPython("import sys; sys.path.insert(0, '/lib')");
    graph = py.pyimport("blocks.core.graph");
    graph.start("/app", JSON.stringify(spec), JSON.stringify(baseline));
    return py.runPython("import sys; sys.version.split()[0]");
  },
  dataset({ path, buf }) { write("/app", { [path]: buf }); },
  run({ settings, data }) { return JSON.parse(graph.run_json(JSON.stringify(settings), JSON.stringify(data))); },
  output({ name }) { return JSON.parse(graph.output_json(name)); },
};

self.onmessage = async ({ data: { id, type, ...args } }) => {
  try { self.postMessage({ id, ok: true, result: await handlers[type](args) }); }
  catch (e) { self.postMessage({ id, ok: false, error: String((e && e.message) || e) }); }
};
