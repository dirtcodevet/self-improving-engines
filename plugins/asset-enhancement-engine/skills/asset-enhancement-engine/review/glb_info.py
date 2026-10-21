"""Read a GLB's structure (JSON chunk) without executing anything from it: meshes, primitives, vertex counts,
bounds, materials/textures, skins, animations. usage: python -I glb_info.py <file.glb>"""
import json
import struct
import sys

with open(sys.argv[1], "rb") as f:
    magic, ver, length = struct.unpack("<4sII", f.read(12))
    assert magic == b"glTF", magic
    clen, ctype = struct.unpack("<II", f.read(8))
    J = json.loads(f.read(clen).decode("utf-8"))
print("glTF v", ver, "total", length, "bytes; asset", J.get("asset"))
for k in ("scenes", "nodes", "meshes", "materials", "textures", "images", "skins", "animations", "accessors"):
    print(f"  {k}: {len(J.get(k, []))}")
acc = J.get("accessors", [])
for i, m in enumerate(J.get("meshes", [])):
    for j, p in enumerate(m["primitives"]):
        a = acc[p["attributes"]["POSITION"]]
        ni = acc[p["indices"]]["count"] if "indices" in p else None
        print(f"  mesh {i} '{m.get('name')}' prim {j}: verts {a['count']} indices {ni} min {a.get('min')} max {a.get('max')} "
              f"attrs {list(p['attributes'])} material {p.get('material')}")
for n in J.get("nodes", [])[:20]:
    print("  node", {k: n[k] for k in n if k in ("name", "mesh", "children", "translation", "rotation", "scale", "skin")})
for im in J.get("images", []):
    print("  image", {k: im[k] for k in im if k in ("name", "mimeType", "bufferView", "uri")})
for mt in J.get("materials", []):
    print("  material", mt.get("name"), list(mt.get("pbrMetallicRoughness", {}).keys()))
