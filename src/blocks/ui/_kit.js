// What the blocks' renderers share, on top of the page's kit; the build puts it before them,
// unscoped. A helper moves here from a block once a second block needs it.

// About n round ticks (1, 2 or 5 times a power of ten) from lo to hi.
function ticks(lo, hi, n = 5) {
  const step = 10 ** Math.floor(Math.log10((hi - lo) / n || 1)), err = (hi - lo) / n / step;
  const s = step * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1);
  const out = [];
  // Each tick from its index, not a running sum, so zero is exactly 0 (a sum leaves -5.6e-17).
  for (let k = Math.ceil(lo / s - 1e-9); k * s <= hi + s * 1e-9; k++) out.push(+(k * s).toPrecision(12));
  return out;
}
