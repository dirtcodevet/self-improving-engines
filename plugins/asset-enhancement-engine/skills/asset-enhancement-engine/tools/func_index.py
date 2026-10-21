"""A short function index at the top of a big tool, so a builder reads the index and greps, not the whole file
(build A1, 2026-10-21: builders read whole part_frame.py and language.py, 266k-375k characters, to orient).
    python engine/tools/func_index.py FILE [FILE ...]     write / refresh the index block in each file
    python engine/tools/func_index.py --check FILE ...    exit 1 if a file's index is missing or out of date
    python engine/tools/func_index.py --big               every engine .py over 1,000 lines and whether it has one
The block is comments between two marker lines right after the module docstring: one line per public top-level
function or class (its signature, cut, and its docstring's first line); a class lists its public methods' names.
Private helpers (_name) are counted, not listed. Run it again after adding or renaming functions."""
import ast
import os
import sys

BEGIN = "# ---- FUNCTION INDEX (engine/tools/func_index.py; grep 'def <name>' to jump) ----"
END = "# ---- END FUNCTION INDEX ----"
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


def write(path, check=False):
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
                if f.endswith(".py"):
                    p = os.path.join(d, f); n = sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
                    if n > 1000:
                        print(f"{n:6d}  {os.path.relpath(p, ROOT)}  {'index' if BEGIN in open(p, encoding='utf-8').read() else 'NO INDEX'}")
        sys.exit(0)
    check = a[0] == "--check"; files = a[1:] if check else a
    bad = [f for f in files if not write(f, check)]
    if check and bad:
        print("out of date:", bad); sys.exit(1)
    print("ok", len(files))
