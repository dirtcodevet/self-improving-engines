"""THE NAMED CATALOGUE (2026-10-20, the person: the engine should carry an issue from a spec with a simple orchestrator,
not a 500-line script per issue). Every reusable piece registers by name, in one of three kinds:

  descriptor  fn(state, **args) -> {key: value}          a measurement (core.measure runs a list of them)
  handle      factory(state, ctx, **args) -> handle       a smooth mechanism with .name .n .x0 .bounds .scale .apply
  op          fn(pack, ctx, **args) -> None               a step of a job on a pack (pack_io.Pack): a solve, a remesh,
                                                         a bake, a frame; it may set ctx["vars"] for later steps

Library modules live in engine/loop/lib/ and register with the decorators below; load_library() imports them all.
A job (engine/loop/job.py) names the pieces it uses; a missing name stops the job with the list of what exists.
`python engine/loop/catalogue.py` prints the catalogue (name, kind, first docstring line, module) for the primer.
"""
import importlib, os, pkgutil

DESCRIPTORS, HANDLES, OPS = {}, {}, {}
KINDS = {"descriptor": DESCRIPTORS, "handle": HANDLES, "op": OPS}


def _reg(table, name):
    def deco(fn):
        assert name not in table or table[name] is fn, "catalogue name taken: " + name
        table[name] = fn
        return fn
    return deco


def descriptor(name):
    return _reg(DESCRIPTORS, name)


def handle(name):
    return _reg(HANDLES, name)


def op(name):
    return _reg(OPS, name)


def get(kind, name):
    table = KINDS[kind]
    if name not in table:
        raise KeyError("no %s named %r in the catalogue; it has: %s" % (kind, name, ", ".join(sorted(table)) or "nothing"))
    return table[name]


def load_library():
    """imports every module in engine/loop/lib (each registers its pieces)"""
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
    for m in pkgutil.iter_modules([here]):
        try:
            importlib.import_module("loop.lib." + m.name)
        except ModuleNotFoundError:
            importlib.import_module("lib." + m.name)


def listing():
    rows = []
    for kind, table in KINDS.items():
        for name, fn in sorted(table.items()):
            doc = ((fn.__doc__ or "").strip().splitlines() or [""])[0]
            rows.append("| %s | %s | %s | %s |" % (name, kind, doc[:110], fn.__module__))
    return "| name | kind | what | module |\n|---|---|---|---|\n" + "\n".join(rows)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    load_library()
    print(listing())
