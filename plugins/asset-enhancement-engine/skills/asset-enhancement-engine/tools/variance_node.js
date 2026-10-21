// The Translator's variance view run outside a page (build L5, 2026-10-21): the SAME code the pages run - the text
// between /*VARIANCE-BEGIN*/ and /*VARIANCE-END*/ in engine/tools/part_frame_view.html - on a mesh given as raw files,
// so its proofs (engine/tools/test_surface_variance.py) and case checks test what a person sees.
//   node engine/tools/variance_node.js JOB.json
//   JOB: {"V": "v.f32" (float32 x,y,z, cm), "F": "f.u32" (uint32 triangles), "sizes": [cm, ...], "out": "prefix",
//         "params": optional engine parameters (calibration only), "template": optional path (default: this folder's part_frame_view.html), "report": "report.json",
//         "info": optional, the page's info block (its frame and handedness: which side is out of the body; build L5b),
//         "page": optional, a Translator page (.html) in place of V / F / info: its own mesh and info, as the page reads them}
//   writes <out>_<i>.f32 (the variance at sizes[i], cm, NaN where none) and the report (edge, noise, auto, outward side, seconds)
"use strict";
const fs = require("fs"), path = require("path");
const job = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const html = fs.readFileSync(job.template || path.join(__dirname, "part_frame_view.html"), "utf8");
const a = html.indexOf("/*VARIANCE-BEGIN*/"), b = html.indexOf("/*VARIANCE-END*/");
if (a < 0 || b < a) throw new Error("no variance block in the template");
const varianceEngine = new Function(html.slice(a, b) + "\nreturn varianceEngine;")();
const rd = (p, T) => { const u = new Uint8Array(fs.readFileSync(p)); return new T(u.buffer, 0, u.byteLength / T.BYTES_PER_ELEMENT); };
const b64 = (s, T) => { const u = Buffer.from(s, "base64"); const c = new Uint8Array(u.byteLength); c.set(u); return new T(c.buffer); };
let V, F, info = job.info || null;
if (job.page){                                                     // the page's own data block (translator_pages.data_block)
  const t = fs.readFileSync(job.page, "utf8"), o = '<script id="data" type="application/json">', i = t.indexOf(o), j = t.indexOf("</script>", i);
  const D = JSON.parse(t.slice(i + o.length, j)); V = b64(D.V, Float32Array); F = b64(D.F, Uint32Array); info = D.info;
} else { V = rd(job.V, Float32Array); F = rd(job.F, Uint32Array); }
const prm = Object.assign({}, job.params || {}); if (info) prm.info = info;
let t0 = Date.now(); const E = varianceEngine(V, F, prm); const rep = {n: E.n, edge_cm: E.edge, outward: E.outward || null, setup_s: (Date.now() - t0) / 1000, sizes: []};
job.sizes.forEach((s, i) => {
  t0 = Date.now(); const f = E.run(s); const sec = (Date.now() - t0) / 1000;
  fs.writeFileSync(`${job.out}_${i}.f32`, Buffer.from(f.buffer, f.byteOffset, f.byteLength));
  const nz = E.noise(f); rep.sizes.push({size_cm: s, seconds: sec, noise_cm: nz, auto_cm: E.AUTO_K * nz});
});
fs.writeFileSync(job.report || `${job.out}_report.json`, JSON.stringify(rep, null, 1));
console.log(JSON.stringify(rep));
