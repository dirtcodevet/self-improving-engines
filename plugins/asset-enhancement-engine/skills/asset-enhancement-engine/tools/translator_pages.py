"""THE TRANSLATOR'S PAGES (build L3, 2026-10-21): one home page listing every Translator view, the way between a
model's views, the viewer template filled in one place, and one command that opens a view on any OS.

Why it exists. The person (2026-10-21), after leaving woman2's whole-body view for the 13a parts list: "now that I've
left that window I no longer know how to get the full body view back up! It isn't in the list, and there's no real way
for me to figure it out." And: "If I want to open a hand, or an ear, or a nose, or a breast, or an arm, or... whatever,
I don't always need to be in the full body view. And if I'm in the list, I shouldn't be prevented from seeing the full
body." Before this, each view (a job's folder: index.html, object.html, one page per part) stood alone.

WHAT IT KEEPS (all made by the engine, never by hand):
  - <home>/index.html, the home page: every view of every model, grouped by model (the mesh file the views are built
    from, so a generated whole-object view and a hand-written parts job on the same skin are one model), newest first,
    each model's whole-object view first; a find box for models and parts. <home> is cases/ (TRANSLATOR_HOME or
    --home to change it); it opens from disk and as the top address of the case-pages server (which serves cases/).
  - <home>/translator_views.js: the same list, read by every page at load to draw its links (so a page made before a
    view of its model existed still links to it), and <home>/translator_elsewhere.json: views made outside <home>.
  - Every page (viewer pages, lists, home) carries the way back: Translator home, the model's whole body / object, its
    list of parts, its other views, and a "go to a part" box that finds a part by the name a person would use.
WHEN: the engine's page writers call touch() after they write (part_frame.build, language.write_object_page,
language.sync), so the home is current whenever a view is; `language.py home` writes it on demand.
NAMES A PERSON WOULD USE: spoken(): a part's file name with its side and number read out (breast_L -> left breast,
finger_L_1 -> left thumb: L / R are the model's own left / right); a pack may add, as data (language.json "spoken"),
numbered words (finger 1 = thumb) and other words a person may type to find a part ("also": feet, toes, boob).
OPEN: find(query) -> the page a query means (nothing: the home page; a model: its whole view, else its list; a model
and a part: that part's page; a folder, a page or a model file); open_page() opens it with Python's webbrowser
(Windows, macOS and Linux).
RE-TEMPLATE: pages(): every viewer page rewritten around its own data block with the current template (the data byte
for byte as it was, but for the object pages' frame record, corrected by build L3), every list rewritten, the home.
"""
import datetime
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TEMPLATE = os.path.join(HERE, "part_frame_view.html")
VIEWS_JS = "translator_views.js"
ELSEWHERE = "translator_elsewhere.json"
DATA_OPEN = '<script id="data" type="application/json">'
SKIP = {"src", "work", "__pycache__", "node_modules", "proof"}
_E = html.escape


def home_dir(home=None):
    return os.path.abspath(home or os.environ.get("TRANSLATOR_HOME") or os.path.join(ROOT, "cases"))


def _p(path):
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def _nc(p):
    return os.path.normcase(os.path.abspath(p)).rstrip("\\/")


def _under(p, d):
    p, d = _nc(p), _nc(d)
    return p == d or p.startswith(d + os.sep)


def _url(p):
    return pathlib.Path(os.path.abspath(p)).as_uri()


def _link(path, home):
    """a path as the home and its pages write it: relative to the home (/), or a file URL when outside it"""
    return os.path.relpath(path, home).replace(os.sep, "/") if _under(path, home) else _url(path)


def _write(path, text):
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)                                             # atomic: a reader never sees half a page


# ------------------------------------------------------------------------------------------------ spoken names
_SPOKEN = {}


def spoken_rules(domain):
    if domain not in _SPOKEN:
        try:
            r = json.load(open(os.path.join(ROOT, "engine", "packs", domain, "language.json"), encoding="utf-8")).get("spoken") or {}
        except Exception:
            r = {}
        _SPOKEN[domain] = r
    return _SPOKEN[domain]


def spoken(name, domain=None):
    """the name a person would use: breast_L -> left breast, finger_R_2 -> right index finger (pack data), piece_3 ->
    piece 3; L / R are the model's own left / right (its left hand is hand_L)"""
    r = spoken_rules(domain) if domain else {}; sides = {"L": "left", "R": "right", **r.get("sides", {})}
    toks = [t for t in str(name).split("_") if t]
    side = next((sides[t] for t in toks if t in sides), None); rest = [t for t in toks if t not in sides]
    numbered = r.get("numbered", {})                                  # the words keep their order (two names never read alike)
    if len(rest) == 2 and rest[1].isdigit() and rest[0] in numbered and 1 <= int(rest[1]) <= len(numbered[rest[0]]):
        rest = [numbered[rest[0]][int(rest[1]) - 1]]
    return " ".join(([side] if side else []) + rest) or str(name)


def also(word, domain):
    return (spoken_rules(domain).get("also") or {}).get(word or "", []) if domain else []


# ------------------------------------------------------------------------------------------------------- views
def _job(d):
    try:
        j = json.load(open(os.path.join(d, "job.json"), encoding="utf-8"))
    except Exception:
        return None
    return j if isinstance(j, dict) and {"definitions", "parts", "sources"} <= set(j) else None


def _domain(job):
    if "language" in job:
        return job["language"].get("pack")
    m = re.search(r"packs[/\\]([^/\\]+)[/\\]", job.get("definitions", ""))
    return m.group(1) if m else None


def _mesh_key(m):
    """a job source's mesh as a model key (the file the views are made from)"""
    if isinstance(m, str):
        f = m
    elif "follow_pack" in m:
        f = m["follow_pack"].rstrip("/\\") + "/" + m.get("file", "")
    else:
        f = next((m[k] for k in ("npz", "ply", "obj", "stl", "file", "path") if k in m), json.dumps(m, sort_keys=True))
    return os.path.relpath(_p(f), ROOT).replace(os.sep, "/").lower() if not f.startswith("{") else f


def _items(job):
    out = []
    for item in job["parts"]:
        for side in (item.get("sides") or [item.get("side")]):
            out.append((item, side, item.get("name") or (item["part"] + ("_" + side if side else ""))))
    return out


def view(d, home):
    """one job's folder -> its view's records, one per model it holds parts of (a hand-written job may read two
    meshes); the pages are in the job's out_dir"""
    job = _job(d)
    if not job:
        return []
    d = _p(job.get("out_dir") or d) if os.path.isdir(_p(job.get("out_dir") or d)) else d
    try:
        pages = {f for f in os.listdir(d) if f.endswith(".html")}
    except OSError:
        return []
    if not pages:
        return []
    dom = _domain(job); L = job.get("language"); rel = lambda f: _link(os.path.join(d, f), home)
    data = [f for f in os.listdir(d) if f.endswith(".npz") or f == "segmentation.json"]   # when the view was built (its
    upd = max(os.path.getmtime(os.path.join(d, f)) for f in (data or pages))               # pages may be re-templated later)
    if L:
        try:
            seg = json.load(open(os.path.join(d, "segmentation.json"), encoding="utf-8")); recs = seg["parts"]
        except Exception:
            recs = [{"name": n} for _, _, n in _items(job)]
        groups = {_mesh_key(L["model"]): [(r["name"], r.get("word"), (r.get("descriptors") or {}).get("area_cm2")) for r in recs]}
        labels = {_mesh_key(L["model"]): job["sources"].get("model", {}).get("label", L.get("name", ""))}
    else:
        groups, labels = {}, {}
        for item, side, n in _items(job):
            s = job["sources"].get(item["source"], {}); k = _mesh_key(s.get("mesh", item["source"]))
            groups.setdefault(k, []).append((n, item["part"], None)); labels.setdefault(k, s.get("label", item["source"]))
    out = []
    for k, names in groups.items():
        parts = [{"n": n, "s": spoken(n, dom), "w": w or "", "p": rel(n + ".html"), "a": also(w, dom),
                  **({"cm2": round(float(ar), 1)} if ar is not None else {})}
                 for n, w, ar in names if n + ".html" in pages]
        out.append({"dir": _link(d, home), "folder": os.path.basename(d.rstrip("\\/")), "model": k, "label": labels[k],
                    "name": (L or {}).get("name"), "domain": dom, "language": bool(L),
                    "object": rel("object.html") if L and "object.html" in pages else None,
                    "list": rel("index.html") if "index.html" in pages else None, "parts": parts, "updated": upd,
                    "case": _link(d, home).split("/")[0] if _under(d, home) else d})
    return out


def scan(home=None):
    """every view: Translator jobs with pages under the home (any depth) and the views registered from elsewhere"""
    home = home_dir(home); dirs = []
    for dp, dn, fn in os.walk(home):
        dn[:] = sorted(x for x in dn if x not in SKIP and not x.startswith("."))
        if "job.json" in fn:
            dirs.append(dp)
    try:
        dirs += [d for d in json.load(open(os.path.join(home, ELSEWHERE), encoding="utf-8")).get("views", []) if os.path.isdir(d)]
    except Exception:
        pass
    out, seen = [], set()
    for d in dirs:
        for v in view(d, home):
            if (v["dir"], v["model"]) not in seen:                     # a copied job pointing at the same pages: once
                seen.add((v["dir"], v["model"])); out.append(v)
    return out


def _title(v):
    """a model's name from one of its views: a hand-written job's source label up to its first ':' or '(',
    else the language job's name"""
    if not v["language"]:
        return re.split(r"[:(]", v["label"])[0].strip(" ,") or v["model"]
    return (v["name"] or v["model"]).replace("_", " ")


def models(views):
    """views grouped by model (newest first); in each, the whole-object views first (a pack with words before the
    generic one), then the lists"""
    G = {}
    for v in views:
        G.setdefault(v["model"], []).append(v)
    out = []
    for k, vs in G.items():
        vs.sort(key=lambda v: (v["object"] is None, v["domain"] == "generic", -v["updated"]))
        plain = [v for v in vs if not v["language"]]
        noun = "body" if any(v["domain"] == "human" for v in vs) else "object"
        nobj = sum(v["object"] is not None for v in vs); nlang = sum(v["language"] for v in vs)
        for v in vs:
            q = f" · {v['domain']} words" if v["language"] and nlang > 1 else (f" · {v['folder']}" if not v["language"] and len(vs) > 1 else "")
            v["object_label"] = f"Whole {noun}" + (f" · {v['domain']} words" if nobj > 1 else "") if v["object"] else None
            v["list_label"] = f"Parts list ({len(v['parts'])})" + q
        name = _title(plain[0]) if plain else _title(vs[0])
        out.append({"key": k, "name": name, "label": (plain or vs)[0]["label"], "noun": noun, "updated": max(v["updated"] for v in vs),
                    "cases": sorted({v["case"] for v in vs}), "views": vs})
    out.sort(key=lambda m: -m["updated"])
    return out


def registry(home=None):
    home = home_dir(home); M = models(scan(home))
    return {"_": "every Translator view, by model (engine/tools/translator_pages.py; made by the engine)",
            "made": datetime.datetime.now().isoformat(timespec="seconds"), "home": "index.html",
            "models": [{**m, "updated": time.strftime("%Y-%m-%d %H:%M", time.localtime(m["updated"])),
                        "views": [{k: v[k] for k in ("dir", "folder", "label", "name", "domain", "object", "list", "parts",
                                                     "object_label", "list_label", "case")} for v in m["views"]]} for m in M]}


# ------------------------------------------------------------------------------------------------- page chrome
CSS = (":root{--bg:#f6f5f2;--panel:#fff;--ink:#1d1d1f;--mute:#66666b;--line:#ddd9d0;--acc:#c75b12;--chip:#efece6}"
       "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#18181b;--panel:#222226;--ink:#ececef;--mute:#9a9aa2;--line:#34343a;--acc:#ff9a4d;--chip:#2d2d33}}"
       ":root[data-theme=dark]{--bg:#18181b;--panel:#222226;--ink:#ececef;--mute:#9a9aa2;--line:#34343a;--acc:#ff9a4d;--chip:#2d2d33}"
       "*{box-sizing:border-box}body{font:14px/1.45 system-ui,-apple-system,'Segoe UI',sans-serif;margin:0;padding:14px 16px 28px;background:var(--bg);color:var(--ink)}"
       "a{color:var(--acc)}.wrap{max-width:1100px;margin:auto}.mute{color:var(--mute)}h1{font-size:22px;margin:6px 0 2px}"
       ".tnav{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:center;font-size:13px;padding:6px 0 10px;border-bottom:1px solid var(--line);margin-bottom:10px}"
       ".tnav a{text-decoration:none}.tnav a:hover{text-decoration:underline}.tnav .here{font-weight:700;color:var(--ink)}.tnav .home{font-weight:700}"
       ".big{display:inline-block;padding:7px 13px;border:1px solid var(--acc);border-radius:8px;margin:4px 8px 4px 0;font-weight:600;text-decoration:none}"
       ".find{width:100%;max-width:520px;font:inherit;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink)}"
       ".tbl{overflow-x:auto}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top;white-space:nowrap}"
       ".sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}.pn{font-weight:600}.fn{color:var(--mute);font-size:12px;margin-left:6px}")
NAV_JS = r"""
// build L3: the way between a model's views, from the home's list of every view (translator_views.js)
function tnav(N, el, opts){ opts = opts || {};
  const up = p => /^[a-z]+:/i.test(p) ? p : N.up + p, here = N.self;
  const a = (href, t, cls) => `<a href="${href}"${cls ? ` class="${cls}"` : ""}>${t}</a>`;
  const own = () => { let s = a(N.home, "Translator", "home"); if (N.object) s += a(N.object, "Whole " + (N.noun || "object"), here.endsWith("object.html") ? "here" : ""); if (N.list) s += a(N.list, "Parts list", here.endsWith("index.html") ? "here" : ""); return s; };
  el.innerHTML = own(); const R = window.TRANSLATOR_VIEWS; if (!R) return null;
  const dir = here.replace(/[^/]*$/, "").replace(/\/$/, ""); let M = null, V = null;
  for (const m of R.models) for (const v of m.views) if (!M && (v.object === here || v.parts.some(p => p.p === here))) { M = m; V = v; }
  for (const m of R.models) for (const v of m.views) if (!M && v.dir === dir) { M = m; V = v; }
  if (!M) return null;
  let s = a(N.home, "Translator", "home") + `<span class="mute">${M.name}</span>`;
  for (const v of M.views){ if (v.object) s += a(up(v.object), v.object_label, v.object === here ? "here" : "");
    if (v.list) s += a(up(v.list), v.list_label, v.list === here ? "here" : ""); }
  el.innerHTML = s;
  const parts = []; for (const v of M.views) for (const p of v.parts) parts.push({...p, href: up(p.p), view: v.list_label});
  return {model: M, view: V, parts};
}
function tfind(q, parts){ const T = q.toLowerCase().match(/[a-z0-9]+/g) || []; if (!T.length) return parts.slice();
  const hit = p => { const H = (p.s + " " + p.n.replace(/_/g, " ") + " " + (p.w || "") + " " + (p.a || []).join(" ") + " " + (p.m || "")).toLowerCase().match(/[a-z0-9]+/g) || [];
    return T.every(t => H.some(h => h.startsWith(t) || t.startsWith(h) && h.length >= 3)); };
  return parts.filter(hit).sort((x, y) => (x.s.toLowerCase() === q.toLowerCase() ? -1 : 0) - (y.s.toLowerCase() === q.toLowerCase() ? -1 : 0)); }
"""


def nav_for(page, home=None, noun=None):
    """what a page needs to draw its links: the way up to the home (relative inside the home, a file URL outside),
    its own path as the home's list writes it, its folder's list and whole-object page"""
    home = home_dir(home); d = os.path.dirname(os.path.abspath(page))
    up = (os.path.relpath(home, d).replace(os.sep, "/") + "/") if _under(d, home) else _url(home) + "/"
    up = "" if up == "./" else up
    return {"up": up, "home": up + "index.html", "views": up + VIEWS_JS, "self": _link(page, home),
            "object": "object.html" if os.path.exists(os.path.join(d, "object.html")) else None,
            "list": "index.html", "noun": noun or "object"}


def _noun(d):
    job = _job(d) or {}
    return "body" if _domain(job) == "human" else "object"


_GROUPS = {}


def group_noun(d, home=None):
    """'body' when the model this folder's view belongs to has a human view (a generic view of a body is a body),
    else 'object'; the scan is kept for 20 s (a build writes many pages)"""
    home = home_dir(home); c = _GROUPS.get(home)
    if not c or time.time() - c[0] > 20:
        c = _GROUPS[home] = (time.time(), models(scan(home)))
    me = _link(d, home)
    for m in c[1]:
        if any(v["dir"] == me for v in m["views"]):
            return m["noun"]
    return _noun(d)


def _views_script(N):
    return f"<script src=\"{_E(N['views'])}\"></script>"


# ----------------------------------------------------------------------------------------------- viewer pages
def template():
    t = open(TEMPLATE, encoding="utf-8").read()                       # the stamp: the template and the links' script
    return t, hashlib.sha1((t + NAV_JS).encode("utf-8")).hexdigest()[:12]


def fill_viewer(title, data_text, page, home=None):
    """the viewer template filled: its title, the page's way around (nav_for), and its data block (already escaped)"""
    t, sha = template(); N = nav_for(page, home, group_noun(os.path.dirname(os.path.abspath(page)), home))
    t = t.replace("__TITLE__", _E(title)).replace("__TEMPLATE__", sha).replace("/*__NAV__*/null", json.dumps(N).replace("</", "<\\/"))
    t = t.replace("/*__NAVJS__*/", NAV_JS)
    i = t.index("/*__DATA__*/null")
    return t[:i] + data_text + t[i + len("/*__DATA__*/null"):]


def page_stamp(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            m = re.search(r'name="translator-template" content="([0-9a-f]+)"', f.read(4000))
        return m.group(1) if m else None
    except OSError:
        return None


def data_block(text):
    i = text.find(DATA_OPEN)
    if i < 0:
        return None, None, None
    i += len(DATA_OPEN); j = text.index("</script>", i)
    return text[i:j], i, j


def split_info(block):
    dec = json.JSONDecoder(); k = len('{"info": ')
    if not block.startswith('{"info": '):
        raise ValueError("a data block that does not start with its info")
    info, end = dec.raw_decode(block, k)
    return info, block[k:end], block[end:]


def object_parts(block):
    """the parts list an object page shows (its data's object.parts)"""
    i = block.rfind(', "object": {')
    if i < 0:
        return None
    obj, _ = json.JSONDecoder().raw_decode(block, i + len(', "object": '))
    return obj


def retemplate(path, home=None):
    """a viewer page rewritten with the current template around its own data block (kept as it is, byte for byte);
    an object page's frame record is corrected (build L3: language.object_frame_record). Returns what changed."""
    t = open(path, encoding="utf-8").read(); block, _, _ = data_block(t)
    if block is None:
        return None
    info, info_txt, rest = split_info(block); fixed = []
    if info.get("definition") == "(the whole object)":
        sys.path.insert(0, HERE)
        import language as LG
        obj = object_parts(block); dim = int(obj["dim"]) if obj else 3
        for k, v in LG.object_frame_record(dim).items():
            if info.get(k) != v:
                info[k] = v; fixed.append(k)
        if fixed:
            info_txt = json.dumps(info).replace("</", "<\\/")
    new = '{"info": ' + info_txt + rest
    _write(path, fill_viewer(f"{info['part']} - Translator", new, path, home))
    return {"page": path, "fixed": fixed}


# ------------------------------------------------------------------------------------------------- list pages
def write_list(out_dir, title, sub_html, columns, rows, intro="", home=None):
    """a view's list of parts (index.html): every part under the name a person would use, a find box, the way to the
    model's whole body / object (this folder's object.html, or its other views) and home.
    rows: [{"name", "page", "spoken", "cells": [html], "colour": css or None, "find": extra words}]"""
    home = home_dir(home); page = os.path.join(out_dir, "index.html"); noun = group_noun(out_dir, home); N = nav_for(page, home, noun)
    trs = []
    for r in rows:
        sw = f"<span class='sw' style='background:{r['colour']}'></span>" if r.get("colour") else ""
        words = " ".join([r["spoken"], r["name"].replace("_", " "), r.get("find", "")]).lower()
        trs.append(f"<tr data-find='{_E(words)}'><td>{sw}<a class='pn' href='{_E(r['page'])}'>{_E(r['spoken'])}</a>"
                   f"<span class='fn'>{_E(r['name'])}</span></td>" + "".join(f"<td>{c}</td>" for c in r["cells"]) + "</tr>")
    big = (f"<a class='big' href='object.html'>Open the whole {noun}</a>" if N["object"] else "") + "<span id='otherwhole'></span>"
    eg = ", ".join(list(dict.fromkeys(r["spoken"] for r in sorted(rows, key=lambda r: len(r["spoken"]))))[:4])
    body = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_E(title)} - parts - Translator</title><style>{CSS}</style></head><body><div class='wrap'>"
            f"<nav class='tnav' id='tnav'></nav><h1>{_E(title)}</h1><p class='mute'>{sub_html}</p><p>{big}</p>"
            f"<p><input class='find' id='find' placeholder='Find a part: {_E(eg)} ...' autocomplete='off'> "
            f"<span class='mute' id='nfound'></span></p>{('<p class=mute>' + intro + '</p>') if intro else ''}"
            f"<div class='tbl'><table id='parts'><tr><th>part</th>" + "".join(f"<th>{_E(c)}</th>" for c in columns) + "</tr>" + "".join(trs) +
            "</table></div><div id='others'></div></div>"
            f"<script type='application/json' id='nav-data'>{json.dumps(N)}</script>{_views_script(N)}<script>{NAV_JS}" + r"""
const N = JSON.parse(document.getElementById("nav-data").textContent), T = tnav(N, document.getElementById("tnav")) || {};
const rows = [...document.querySelectorAll("#parts tr[data-find]")], box = document.getElementById("find"), nf = document.getElementById("nfound");
let others = [];
if (T.model){ const ow = document.getElementById("otherwhole"); for (const v of T.model.views) if (v.object && v.dir !== T.view.dir) ow.innerHTML += `<a class="big" href="${/^[a-z]+:/i.test(v.object) ? v.object : N.up + v.object}">${v.object_label}</a>`;
  others = T.parts.filter(p => !T.view.parts.some(q => q.p === p.p));
  if (others.length) document.getElementById("others").innerHTML = `<h3>Other parts of this model</h3><div id="olist"></div>`; }
function show(){ const q = box.value.trim(), T_ = (q.toLowerCase().match(/[a-z0-9]+/g) || []); let n = 0;
  for (const r of rows){ const H = r.dataset.find.match(/[a-z0-9]+/g) || []; const ok = T_.every(t => H.some(h => h.startsWith(t) || t.startsWith(h) && h.length >= 3)); r.style.display = ok ? "" : "none"; n += ok; }
  const ol = document.getElementById("olist"); if (ol){ const f = tfind(q, others); ol.innerHTML = f.map(p => `<a href="${p.href}">${p.s}</a> <span class="fn">${p.n} &middot; ${p.view}</span>`).join("<br>") || `<span class="mute">none match</span>`; }
  nf.textContent = q ? `${n} of ${rows.length} here` : `${rows.length} parts`; }
box.oninput = show; box.onkeydown = e => { if (e.key === "Enter"){ const r = rows.find(r => r.style.display !== "none"); const o = tfind(box.value, others)[0];
  if (r) location.href = r.querySelector("a").href; else if (o) location.href = o.href; } };
show(); box.focus();
</script></body></html>""")
    _write(page, body)
    return page


# --------------------------------------------------------------------------------------------------- the home
def write_home(home=None):
    """<home>/index.html and <home>/translator_views.js: every view by model"""
    home = home_dir(home); os.makedirs(home, exist_ok=True); R = registry(home)
    _write(os.path.join(home, VIEWS_JS), "window.TRANSLATOR_VIEWS = " + json.dumps(R).replace("</", "<\\/") + ";\n")
    cards = []
    for m in R["models"]:
        rows = []                                                     # one line per view: its whole view, its list
        for v in m["views"]:
            o = f"<a class='big' href='{_E(v['object'])}'>{_E(v['object_label'])}</a>" if v["object"] else ""
            li = f"<a href='{_E(v['list'])}'>{_E(v['list_label'])}</a>" if v["list"] else ""
            rows.append(f"<div class='vrow'>{o}{li}</div>")
        allp = list({p["s"]: p for v in reversed(m["views"]) for p in v["parts"]}.values())   # one per name, the first view's
        allp.sort(key=lambda p: -p.get("cm2", 0)); chips = allp[:8]                               # the biggest parts first
        chip_html = "".join(f"<a href='{_E(p['p'])}'>{_E(p['s'])}</a>" for p in chips)
        more = f"<span class='mute'> and {len(allp) - len(chips)} more</span>" if len(allp) > len(chips) else ""
        cards.append(f"<div class='card' data-key='{_E(m['key'])}'><div class='ct'><b>{_E(m['name'])}</b><span class='mute'>{_E(m['updated'])}</span></div>"
                     f"<div class='mute lbl' title='{_E(m['label'])}'>{_E(m['label'])}</div>{''.join(rows)}"
                     f"<div class='chips'>{chip_html}{more}</div>"
                     f"<div class='mute src'>{_E(m['key'])} &middot; {_E(', '.join(m['cases']))}</div></div>")
    page = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Translator</title><style>{CSS}"
            ".cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px;margin-top:14px}"
            ".card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px}.ct{display:flex;justify-content:space-between;gap:8px;font-size:15px}"
            ".lbl{font-size:12px;margin:2px 0 4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.src{font-size:11px;margin-top:6px;overflow-wrap:anywhere}"
            ".vrow{display:flex;flex-wrap:wrap;align-items:center;gap:0 4px}.vrow .big{margin:3px 8px 3px 0;padding:5px 11px}"
            ".chips{margin-top:6px;font-size:12.5px}.chips a{display:inline-block;background:var(--chip);border-radius:5px;padding:1px 6px;margin:2px 3px 0 0;text-decoration:none}"
            "#hits a{display:inline-block;margin:2px 10px 2px 0}</style></head><body><div class='wrap'>"
            "<h1>Translator</h1><p class='mute'>Every model the Translator has mapped, newest first. Open the whole body or object, or a part "
            "from its list; every page links back here. In Claude Code, <b>/translator</b> brings you back.</p>"
            "<p><input class='find' id='find' placeholder='Find a model or a part: 13a3, brick, left hand, thumb ...' autocomplete='off'></p>"
            f"<div id='hits'></div><div class='cards'>{''.join(cards)}</div>"
            f"<p class='mute' style='margin-top:18px;font-size:12px'>{sum(len(m['views']) for m in R['models'])} views of {len(R['models'])} models; "
            f"made by the engine {R['made']} (engine/tools/translator_pages.py).</p></div>"
            f"<script src='{VIEWS_JS}'></script><script>{NAV_JS}" + r"""
const R = window.TRANSLATOR_VIEWS, box = document.getElementById("find"), hits = document.getElementById("hits"), cards = [...document.querySelectorAll(".card")];
const all = []; for (const m of R.models) for (const v of m.views) for (const p of v.parts) all.push({...p, href: p.p, m: m.name + " " + m.key, model: m.name});
function show(){ const q = box.value.trim(), T = q.toLowerCase().match(/[a-z0-9]+/g) || [];
  const mhit = m => { const H = (m.name + " " + m.key + " " + m.label + " " + m.cases.join(" ") + " " + m.views.map(v => v.dir).join(" ")).toLowerCase().match(/[a-z0-9]+/g) || []; return T.every(t => H.some(h => h.includes(t))); };
  const keep = new Set(R.models.filter(m => !T.length || mhit(m)).map(m => m.key));
  const ph = T.length ? tfind(q, all).slice(0, 40) : [];
  for (const p of ph) for (const m of R.models) if (m.name === p.model) keep.add(m.key);
  for (const c of cards) c.style.display = keep.has(c.dataset.key) ? "" : "none";
  hits.innerHTML = ph.length ? "<p><b>Parts:</b> " + ph.map(p => `<a href="${p.href}">${p.s}</a><span class="fn">${p.model}</span>`).join(" ") + "</p>" : ""; }
box.oninput = show; box.onkeydown = e => { if (e.key === "Enter"){ const a = hits.querySelector("a") || [...document.querySelectorAll(".card")].find(c => c.style.display !== "none")?.querySelector("a"); if (a) location.href = a.href; } };
box.focus();
</script></body></html>""")
    _write(os.path.join(home, "index.html"), page)
    return os.path.join(home, "index.html"), len(R["models"]), sum(len(m["views"]) for m in R["models"])


def register(d, home=None):
    """a view made outside the home: listed on it from now on"""
    home = home_dir(home); f = os.path.join(home, ELSEWHERE)
    try:
        r = json.load(open(f, encoding="utf-8"))
    except Exception:
        r = {"_": "Translator views made outside this folder (engine/tools/translator_pages.py register)", "views": []}
    d = os.path.abspath(d)
    if d not in r["views"]:
        r["views"].append(d); os.makedirs(home, exist_ok=True); _write(f, json.dumps(r, indent=1))


def touch(out_dir=None, home=None):
    """what the engine's page writers call after writing a view: register it if it is outside the home (not a
    scratch folder), then rewrite the home. Never raises (a build is never broken by its home page)."""
    try:
        home = home_dir(home)
        if out_dir and not _under(out_dir, home) and not _under(out_dir, tempfile.gettempdir()):
            register(out_dir, home)
        return write_home(home)
    except Exception as ex:
        print(f"(translator home not written: {type(ex).__name__}: {ex})", file=sys.stderr)
        return None


# ------------------------------------------------------------------------------------------------ re-template
def pages(dirs=None, home=None, only_stale=False, log=print):
    """every view's pages (or those in `dirs`) with the current template and lists, then the home"""
    home = home_dir(home); _, sha = template(); done = {"pages": 0, "fixed": 0, "lists": 0}
    targets = [os.path.abspath(_p(d)) for d in dirs] if dirs else sorted({os.path.abspath(os.path.join(home, v["dir"])) if not v["dir"].startswith("file:")
                                                                        else v["dir"] for v in scan(home)})
    sys.path.insert(0, HERE)
    import language as LG
    for d in targets:
        d = d if os.path.isdir(d) else os.path.dirname(d)
        if not _job(d):
            log(f"  {d}: not a Translator view"); continue
        objparts = None
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            if not f.endswith(".html") or f == "index.html" or (only_stale and page_stamp(p) == sha):
                continue
            r = retemplate(p, home)
            if r:
                done["pages"] += 1; done["fixed"] += bool(r["fixed"])
                if f == "object.html":
                    objparts = object_parts(data_block(open(p, encoding="utf-8").read())[0])
        job = _job(d)
        if "language" in job:
            if objparts is not None or os.path.exists(os.path.join(d, "object.html")):
                if objparts is None:
                    objparts = object_parts(data_block(open(os.path.join(d, "object.html"), encoding="utf-8").read())[0])
                LG.reindex(LG.Obj(os.path.join(d, "job.json")), objparts["parts"]); done["lists"] += 1
        else:
            LG.reindex_plain(os.path.join(d, "job.json")); done["lists"] += 1
        log(f"  {_link(d, home)}: pages current")
    write_home(home)
    return done


# ------------------------------------------------------------------------------------------------------- open
def _tok(s):
    return re.findall(r"[a-z0-9]+", str(s).lower())


def find(query=None, home=None):
    """the page a query means -> (absolute path, what it is). Nothing: the home page. A page or a folder: it (a
    folder: the first view of the model it holds). A model file: its model's first view. Text: the model whose name,
    label, file or folders match best (an exact word beats a prefix; the newest wins a tie) and, when the words also
    name one of its parts, that part's page; else its whole view (else its list)."""
    home = home_dir(home); R = models(scan(home)); here = lambda rel: rel if rel.startswith("file:") else os.path.normpath(os.path.join(home, rel))
    first = lambda m: here(next((v["object"] for v in m["views"] if v["object"]), None) or m["views"][0]["list"])
    if not query or not str(query).strip():
        write_home(home); return os.path.join(home, "index.html"), "the home page"
    q = str(query).strip().strip('"')
    if os.path.exists(q):
        q_ = os.path.abspath(q)
        if q_.endswith(".html"):
            return q_, "that page"
        absd = lambda v: v["dir"] if v["dir"].startswith("file:") else os.path.join(home, v["dir"])
        hits = []
        for m in R:
            if os.path.isfile(q_) and m["key"] == _mesh_key(q_):
                return first(m), f"{m['name']}: {'its whole ' + m['noun'] if 'object.html' in first(m) else 'its list of parts'}"
            vs = [v for v in m["views"] if os.path.isdir(q_) and _under(absd(v), q_)]
            if vs:
                hits.append((any(_nc(absd(v)) == _nc(q_) for v in vs), max(v["updated"] for v in vs), m, vs))
        if hits:                                                      # that folder's own view (whole first), else the newest under it
            _, _, m, vs = max(hits, key=lambda h: (h[0], h[1])); v = next((v for v in vs if _nc(absd(v)) == _nc(q_)), vs[0])
            return here(v["object"] or v["list"]), f"{m['name']}: {'its whole ' + m['noun'] if v['object'] else 'its list of parts'} ({v['dir']})"
        raise ValueError(f"no Translator view of {q}")
    T = _tok(q); best = None
    for m in R:
        H = set(_tok(" ".join([m["name"], m["label"], m["key"]] + [v["dir"] + " " + (v["name"] or "") for v in m["views"]])))
        ms = [3 if t in H else 1 if any(h.startswith(t) for h in H) else 0 for t in T]
        cands = [(None, 0, [s > 0 for s in ms])]                          # the model itself, before any of its parts
        for v in m["views"]:
            for p in v["parts"]:
                P = set(_tok(" ".join([p["s"], p["n"].replace("_", " "), p["w"]] + list(p["a"]))))
                ps = [3 if t in P else 1 if any(h.startswith(t) for h in P) else 0 for t in T]
                extra = [b if not a else 0 for a, b in zip(ms, ps)]      # words the model's own names do not cover
                if any(extra):                                         # (L4) a word both name counts for the part at half
                    both = 0.5 * sum(b for a, b in zip(ms, ps) if a)   # weight: "woman2 13a4 right eye" is the right eye
                    cands.append((p, sum(extra) + both, [a > 0 or b > 0 for a, b in zip(ms, ps)]))   # though "right" is in
                                                                       # the model's label (its pack README's title)
        for p, pscore, cover in cands:
            score = (sum(cover), sum(ms) + pscore, m["updated"])
            if best is None or score > best[0]:
                best = (score, m, p)
    if not best or best[0][0] == 0:
        raise ValueError(f"no Translator model or part matches '{q}'")
    _, m, p = best
    if p is not None:
        return here(p["p"]), f"{m['name']}: {p['s']} ({p['n']})"
    return first(m), f"{m['name']}: {'its whole ' + m['noun'] if 'object.html' in first(m) else 'its list of parts'}"


def open_page(page):
    """the page in the person's browser: Python's webbrowser (Windows, macOS, Linux)"""
    url = page if str(page).startswith(("file:", "http:", "https:")) else _url(page)
    return webbrowser.open(url)


def where(page, home=None):
    home = home_dir(home)
    return {"page": os.path.abspath(page), "url": _url(page), "rel": _link(page, home) if _under(page, home) else None}


# ------------------------------------------------------------------------------------------------------ proof
def prove(log=print):
    """Planted views in a scratch home (A28: once, at the tool's making; the viewer's drawing is checked in a browser:
    cases/translator_l3/checks/shots.py and the pages' #selftest): two views of one model (a generated whole object with
    its list, a hand-written parts job on the same mesh) and one of another model ->
    1. grouped by the mesh they are made from, the whole view first, a hand-written job's label naming the model;
    2. names a person would use (finger_R_1 -> right thumb, by the human pack's data; toe_L_2 -> left second toe);
    3. find: nothing -> the home; the model's name -> its whole view; the model and a part's spoken name -> that part;
       a part's other word ("feet") -> it; a folder -> its own view;
    4. a page's way around: up to the home relative, its list and whole view; the home's paths relative to it;
    5. re-templating keeps a page's data block byte for byte, corrects an object page's frame record (left-handed,
       its true matrix) and is a no-op for a page already current."""
    import shutil
    sys.path.insert(0, HERE)
    import language as LG
    home = tempfile.mkdtemp(prefix="translator_prove_"); ok = True; res = {}
    try:
        def page(d, name, info, extra=""):
            block = json.dumps({"info": info, "V": "AAAA", "F": ""}) [:-1] + extra + "}"
            p = os.path.join(d, name); _write(p, fill_viewer(f"{info['part']} - Translator", block, p, home)); return p, block
        a = os.path.join(home, "case1", "language"); b = os.path.join(home, "case1", "parts"); c = os.path.join(home, "case2", "language")
        for d in (a, b, c):
            os.makedirs(d)
        json.dump({"language": {"model": "cases/x/body.npz", "pack": "human", "name": "body_x"}, "definitions": "d.json", "parts": [],
                   "sources": {"model": {"label": "body_x (body.npz; human pack)"}}, "out_dir": a}, open(os.path.join(a, "job.json"), "w"))
        json.dump({"parts": [{"name": n, "word": w, "descriptors": {"area_cm2": ar}} for n, w, ar in
                             [("torso", "torso", 900), ("finger_R_1", "finger", 3), ("toe_L_2", "toe", 2), ("foot_L", "foot", 60)]]},
                  open(os.path.join(a, "segmentation.json"), "w"))
        json.dump({"definitions": "engine/packs/human/part_frames.json", "out_dir": b, "sources": {"s": {"label": "body x, build 7: the planted body", "mesh": {"npz": "cases/x/body.npz"}}},
                   "parts": [{"part": "breast", "source": "s", "sides": ["L", "R"]}]}, open(os.path.join(b, "job.json"), "w"))
        json.dump({"language": {"model": "cases/y/brick.ply", "pack": "masonry", "name": "brick_y"}, "definitions": "d.json", "parts": [],
                   "sources": {"model": {"label": "brick_y"}}, "out_dir": c}, open(os.path.join(c, "job.json"), "w"))
        json.dump({"parts": [{"name": "frog_floor", "word": "frog_floor"}]}, open(os.path.join(c, "segmentation.json"), "w"))
        old_obj = {"part": "body_x", "definition": "(the whole object)", "handedness": "right-handed (the object's page frame: x right, y up, z toward its front)",
                   "axes": {"x": "right", "y": "up", "z": "front"}, "frame": {"origin_source": [0, 0, 0], "R_rows_source": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "source_units_to_cm": 100.0}}
        po, bo = page(a, "object.html", old_obj, ', "object": {"dim": 3, "parts": []}')
        pf, bf = page(a, "finger_R_1.html", {"part": "finger_R_1", "handedness": "mirrored (left-handed) so lateral is +X on both sides"})
        for n in ("torso", "toe_L_2", "foot_L"):
            page(a, n + ".html", {"part": n, "handedness": "right-handed"})
        for n in ("breast_L", "breast_R"):
            page(b, n + ".html", {"part": n, "handedness": "right-handed"})
        page(c, "object.html", {"part": "brick_y", "definition": "x"}); page(c, "frog_floor.html", {"part": "frog_floor"})
        for d in (a, b, c):
            _write(os.path.join(d, "index.html"), "<!doctype html>")
        os.utime(os.path.join(c, "frog_floor.html"), (1, 1)); os.utime(os.path.join(c, "object.html"), (1, 1))   # the brick is older
        M = models(scan(home)); m0 = M[0]
        res["1_grouped"] = (len(M) == 2 and m0["key"] == "cases/x/body.npz" and [v["dir"] for v in m0["views"]] == ["case1/language", "case1/parts"]
                            and m0["name"] == "body x, build 7" and m0["noun"] == "body" and m0["views"][0]["object_label"] == "Whole body")
        sp = {p["n"]: p["s"] for v in m0["views"] for p in v["parts"]}
        res["2_spoken"] = sp.get("finger_R_1") == "right thumb" and sp.get("toe_L_2") == "left second toe" and sp.get("breast_R") == "right breast"
        f = lambda q: os.path.relpath(find(q, home)[0], home).replace(os.sep, "/")
        res["3_find"] = {"": f(""), "body x": f("body x"), "body x right thumb": f("body x right thumb"), "feet": f("feet"),
                         "brick": f("brick"), "folder": f(b)}
        res["3_find_ok"] = res["3_find"] == {"": "index.html", "body x": "case1/language/object.html", "body x right thumb": "case1/language/finger_R_1.html",
                                             "feet": "case1/language/foot_L.html", "brick": "case2/language/object.html", "folder": "case1/parts/index.html"}
        N = nav_for(pf, home); write_home(home); R = registry(home)
        res["4_nav"] = (N["up"] == "../../" and N["self"] == "case1/language/finger_R_1.html" and N["object"] == "object.html"
                        and R["models"][0]["views"][0]["object"] == "case1/language/object.html"
                        and os.path.exists(os.path.join(home, VIEWS_JS)) and "case1/language/object.html" in open(os.path.join(home, "index.html"), encoding="utf-8").read())
        r1 = retemplate(pf, home); r2 = retemplate(po, home)
        nb = data_block(open(pf, encoding="utf-8").read())[0]; ob = data_block(open(po, encoding="utf-8").read())[0]; oi, _, orest = split_info(ob)
        res["5_retemplate"] = (nb == bf and r1["fixed"] == [] and orest == split_info(bo)[2] and sorted(r2["fixed"]) == ["axes", "frame", "handedness"]
                               and oi["handedness"].startswith("left-handed") and oi["frame"]["R_rows_source"] == LG.page_matrix(3).tolist()
                               and retemplate(po, home)["fixed"] == [])
        for k in ("1_grouped", "2_spoken", "3_find_ok", "4_nav", "5_retemplate"):
            ok &= bool(res[k]); log(f"  {k}: {'PASS' if res[k] else 'FAIL'}")
        if not res["3_find_ok"]:
            log(f"    {res['3_find']}")
    finally:
        shutil.rmtree(home, ignore_errors=True)
    log(f"translator_pages prove: {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "prove":
        sys.exit(0 if prove() else 1)
    print(__doc__)
