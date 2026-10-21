"""PACK I/O for jobs (2026-10-20): the plumbing every stage used to write for itself. A Pack reads a pack folder's files on
demand, lets ops replace them, and saves the result as a new folder (a copy of the input with the changed files
written), exactly as the hand-written stages did (copytree, then np.savez_compressed / json.dump(indent=1)).

    pk = Pack(in_dir)
    S = pk.npz("skin.npz")            # dict of arrays (a fresh dict; set_npz to change)
    st = pk.state()                    # {"V": float64, "F": int64, every per-vertex skin array}
    pk.put_state(st)                   # V back into skin.npz as float32 (+ any per-vertex arrays named in `keys`)
    pk.set_npz("shading.npz", Sh); pk.set_json("micro_detail.json", md); pk.write_file("nac_height.png", bytes)
    pk.save(out_dir)
"""
import json, os, shutil
import numpy as np


class Pack:
    def __init__(self, path):
        self.path = path; self._npz = {}; self._json = {}; self._bytes = {}; self._order = []

    def _mark(self, name):
        if name in self._order: self._order.remove(name)
        self._order.append(name)

    def npz(self, name):
        if name in self._npz: return dict(self._npz[name])
        with np.load(os.path.join(self.path, name)) as z:     # read fully (an open npz cannot be removed on Windows)
            return {k: z[k] for k in z.files}

    def json(self, name):
        if name in self._json: return json.loads(json.dumps(self._json[name]))
        return json.load(open(os.path.join(self.path, name)))

    def exists(self, name):
        return name in self._npz or name in self._json or name in self._bytes or os.path.exists(os.path.join(self.path, name))

    def set_npz(self, name, d):
        self._npz[name] = dict(d); self._mark(name)

    def set_json(self, name, d):
        self._json[name] = d; self._mark(name)

    def write_file(self, name, data):
        self._bytes[name] = data; self._mark(name)

    def state(self):
        S = self.npz("skin.npz"); n = len(S["v"])
        st = {"V": S["v"].astype(np.float64), "F": S["f"].astype(np.int64)}
        for k, v in S.items():
            if k not in ("v", "f") and isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == n:
                st[k] = v
        return st

    def put_state(self, st, keys=()):
        S = self.npz("skin.npz"); S["v"] = st["V"].astype(np.float32)
        for k in keys: S[k] = st[k]
        self.set_npz("skin.npz", S)

    def save(self, out):
        if os.path.exists(out): shutil.rmtree(out)
        shutil.copytree(self.path, out)
        for name in self._order:
            p = os.path.join(out, name)
            if name in self._npz: np.savez_compressed(p, **self._npz[name])
            elif name in self._json: json.dump(self._json[name], open(p, "w"), indent=1)
            else: open(p, "wb").write(self._bytes[name])
        notify_language(out)


def notify_language(path):
    """(build L1) the language tool's jobs that read what was just written are brought current in the background
    (engine/tools/language.py notify); a no-op when no job reads it, and never breaks the writer"""
    if os.environ.get("LANGUAGE_NO_NOTIFY"):
        return
    try:
        import sys as _sys
        tools = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools")
        if tools not in _sys.path: _sys.path.insert(0, tools)
        import language
        language.notify([path])
    except Exception as ex:
        print("(pack_io: language notify skipped: %s)" % ex)


def same_pack(a, b):
    """every file of two packs equal by content: npz arrays (exact), json (parsed), other files (bytes). The proof a
    migrated stage must pass against the hand-written stage's output."""
    fa, fb = sorted(os.listdir(a)), sorted(os.listdir(b)); diffs = []
    if fa != fb: diffs.append("files differ: %s vs %s" % (sorted(set(fa) ^ set(fb)), ""))
    for fn in sorted(set(fa) & set(fb)):
        pa, pb = os.path.join(a, fn), os.path.join(b, fn)
        if fn.endswith(".npz"):
            with np.load(pa) as za, np.load(pb) as zb:
                if sorted(za.files) != sorted(zb.files): diffs.append(fn + ": keys"); continue
                for k in za.files:
                    x, y = za[k], zb[k]
                    if x.shape != y.shape or x.dtype != y.dtype or not np.array_equal(x, y, equal_nan=x.dtype.kind == "f"):
                        d = float(np.abs(x.astype(float) - y.astype(float)).max()) if x.shape == y.shape and x.dtype.kind in "fiu" else None
                        diffs.append("%s[%s] max diff %s" % (fn, k, d))
        elif fn.endswith(".json"):
            if json.load(open(pa)) != json.load(open(pb)): diffs.append(fn)
        elif open(pa, "rb").read() != open(pb, "rb").read():
            diffs.append(fn)
    return diffs
