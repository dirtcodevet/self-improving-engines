"""A short function index at the top of a big tool, so a builder reads the index and greps, not the whole file
(build A1, 2026-10-21: builders read whole part_frame.py and language.py, 266k-375k characters, to orient).
    python engine/tools/func_index.py FILE [FILE ...]     write / refresh the index block in each file
    python engine/tools/func_index.py --check FILE ...    exit 1 if a file's index is missing or out of date
    python engine/tools/func_index.py --big               every engine .py over 1,000 lines (.html: or 60,000 characters)
                                                          and whether it has one
The block is comments between two marker lines right after the module docstring: one line per public top-level
function or class (its signature, cut, and its docstring's first line); a class lists its public methods' names.
Private helpers (_name) are counted, not listed. Run it again after adding or renaming functions.
An .html file (build A2, 2026-10-21: part_frame_view.html, 82k characters) gets one HTML comment before its first <style>:
the file's layout (line ranges) and, per script section (a `// ------ title` divider), its top-level functions with the
line the section starts on; the line numbers are of the file with its index. A page generator that copies the file must
cut the block (translator_pages.template() does)."""
import ast
import os
import re
import sys

BEGIN = "# ---- FUNCTION INDEX (engine/tools/func_index.py; grep 'def <name>' to jump) ----"
END = "# ---- END FUNCTION INDEX ----"
HBEGIN = "<!-- FUNCTION INDEX (engine/tools/func_index.py; grep the name to jump; line numbers are of this file; the page builders cut this block out)"
HEND = "END FUNCTION INDEX -->"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _sig(n):
    a = n.args; names = [x.arg for x in a.posonlyargs + a.args]
    if a.vararg:
        names.append("*" + a.vararg.arg)
    names += [x.arg for x in a.kwonlyargs]
    if a.kwarg:
        names.append("**" + a.kwarg.arg)
    s = ", ".join(names)
    return s if len(s) <= 48 else s[:45] + "..."


def _doc1(n):
    d = ast.get_docstring(n) or ""
    return d.strip().split("\n")[0].strip()


def index_lines(src):
    t = ast.parse(src); out = []; private = 0
    for n in t.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.name.startswith("_"):
                private += 1; continue
            line = f"#   {n.name}({_sig(n)})"
        elif isinstance(n, ast.ClassDef):
            if n.name.startswith("_"):
                private += 1; continue
            meths = [m.name for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith("_")]
            line = f"#   class {n.name}" + (f" [{', '.join(meths)}]" if meths else "")
        else:
            continue
        d = _doc1(n)
        if d:
            line = (line + "  - " + d) if len(line) < 70 else line
        out.append(line if len(line) <= 120 else line[:117] + "...")
    out.append(f"#   (+ {private} private helpers: grep '^def _')")
    return out


# ------------------------------------------------------------------------------------------------ HTML (its script)
_JS_FN = re.compile(r"^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)")
_JS_ARROW = re.compile(r"^(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\(([^)]*)\)|([A-Za-z_$][\w$]*))\s*=>")
_JS_SECT = re.compile(r"^//\s*-{8,}\s*(.+?)\s*$")
_JS_MARK = re.compile(r"^/\*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\*/\s*$")


def strip_html_index(src):
    """src without its function-index block (if it has one), as it was before the block was written"""
    a = src.find(HBEGIN)
    if a < 0:
        return src
    b = src.index(HEND, a) + len(HEND)
    return src[:a] + src[b:].lstrip("\n")


def _wrap(prefix, items, width=118):
    """items joined by ', ' on lines of at most width characters, continuation lines indented under the first item"""
    pad = " " * len(prefix); lines = []; cur = prefix; fresh = True
    for i, it in enumerate(items):
        piece = it + ("," if i < len(items) - 1 else "")
        if not fresh and len(cur) + 1 + len(piece) > width:
            lines.append(cur); cur = pad + piece
        else:
            cur = cur + ("" if fresh else " ") + piece
        fresh = False
    lines.append(cur)
    return lines


def html_index_lines(body, shift):
    """index lines for an .html file whose text (without any index) is body; shift = the number of lines the index adds
    above everything it points at (the block's own length)"""
    L = body.split("\n"); n = len(L)
    first = lambda pat, start=0: next((i for i in range(start, n) if re.match(pat, L[i])), None)
    st = first(r"<style>"); se = first(r"</style>", st or 0); ap = first(r'<div id="app">')
    sc = first(r"<script>"); sce = first(r"</script>", (sc or 0) + 1)
    d1 = first(r'<script id="'); out = []
    ln = lambda i: i + 1 + shift                                   # 1-based line in the file with its index
    lay = []
    if st is not None and se is not None:
        lay.append(f"style {ln(st)}-{ln(se)}")
    if ap is not None and d1 is not None:
        lay.append(f"markup {ln(ap)}-{ln(d1) - 1}")
    if d1 is not None and sc is not None:
        lay.append(f"data script blocks {ln(d1)}-{ln(sc) - 1} (filled by the page generator)")
    if sc is not None and sce is not None:
        lay.append(f"script {ln(sc)}-{ln(sce)}")
    out += _wrap("layout: ", lay)
    if sc is None or sce is None:
        return out
    out.append("script, by section: [first line] title: its top-level functions (a name alone: arguments too long to list)")
    marks = {}                                                      # BEGIN / END marker comments: name -> line (e.g. a block the proofs cut out)
    for i in range(sc + 1, sce):
        k = _JS_MARK.match(L[i])
        if k:
            marks[k.group(1)] = ln(i)
    sections = [[ln(sc), "start", []]]; last = None
    for i in range(sc + 1, sce):
        t = L[i]
        m = _JS_SECT.match(t); k = _JS_MARK.match(t); f = _JS_FN.match(t); a = _JS_ARROW.match(t)
        if m:
            sections.append([ln(i), m.group(1), []])
        elif k:
            nm = k.group(1)
            if nm.endswith("-BEGIN") and nm[:-6] + "-END" in marks:
                sections.append([ln(i), f"{nm[:-6].lower()} block (to line {marks[nm[:-6] + '-END']}; the proofs cut it out)", []])
            elif nm.endswith("-END"):
                sections.append([ln(i), "after the " + nm[:-4].lower() + " block", []])
        elif f or a:
            name = (f or a).group(1)
            args = re.sub(r"\s+", " ", ((f.group(2) if f else (a.group(2) if a.group(2) is not None else a.group(3))) or "").strip())
            last = [name, []]
            sections[-1][2].append(last)
            last.append(f"{name}({args})" if args and len(args) <= 24 else name + ("()" if not args else ""))
        elif last is not None:
            g = re.match(r"^\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", t)
            if g:
                last[1].append(g.group(1))
    for line, title, fns in sections:
        items = [x[2] + (" {inside: " + ", ".join(x[1]) + "}" if x[1] else "") for x in fns]
        if items:
            out += _wrap(f"  [{line}] {title}: ", items)
        elif not title.startswith("after the "):
            out.append(f"  [{line}] {title}")
    return out


def html_block(body):
    """the whole index comment for body, its line numbers settled (the block's own length shifts them)"""
    shift = 0
    for _ in range(6):
        lines = [HBEGIN] + html_index_lines(body, shift) + [HEND]
        if len(lines) == shift:
            break
        shift = len(lines)
    return "\n".join(lines)


def write_html(path, check=False):
    src = open(path, encoding="utf-8").read()
    body = strip_html_index(src); L = body.split("\n")
    at = next(i for i, t in enumerate(L) if t.startswith("<style>"))        # right before the first <style>
    new = "\n".join(L[:at] + [html_block(body)] + L[at:])
    if check:
        return new == src
    if new != src:
        open(path, "w", encoding="utf-8").write(new)
    return True


def write(path, check=False):
    if path.lower().endswith((".html", ".htm")):
        return write_html(path, check)
    src = open(path, encoding="utf-8").read()
    body = src
    if BEGIN in src:
        a = src.index(BEGIN); b = src.index(END) + len(END)
        body = src[:a].rstrip("\n") + "\n" + src[b:].lstrip("\n")
    block = "\n".join([BEGIN] + index_lines(body) + [END])
    t = ast.parse(body); L = body.split("\n")
    at = t.body[0].end_lineno if t.body and isinstance(t.body[0], ast.Expr) and isinstance(getattr(t.body[0], "value", None), ast.Constant) else 0
    new = "\n".join(L[:at] + [block] + L[at:])
    if check:
        return new == src
    if new != src:
        ast.parse(new)
        open(path, "w", encoding="utf-8").write(new)
    return True


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(0)
    if a[0] == "--big":
        for d, _, fs in os.walk(os.path.join(ROOT, "engine")):
            if "vendor" in d or "__pycache__" in d:
                continue
            for f in fs:
                if f.endswith((".py", ".html")):
                    p = os.path.join(d, f); txt = open(p, encoding="utf-8", errors="replace").read(); n = txt.count("\n") + 1
                    if n > 1000 or (f.endswith(".html") and len(txt) > 60000):
                        print(f"{n:6d}  {os.path.relpath(p, ROOT)}  {'index' if (HBEGIN if f.endswith('.html') else BEGIN) in txt else 'NO INDEX'}")
        sys.exit(0)
    check = a[0] == "--check"; files = a[1:] if check else a
    bad = [f for f in files if not write(f, check)]
    if check and bad:
        print("out of date:", bad); sys.exit(1)
    print("ok", len(files))
