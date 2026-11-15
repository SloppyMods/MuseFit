# New file for MuseFit (job 009, checked and re-run in job 010; one fix: empty placeholder meshes no longer crash it).
"""Print a plain-text summary of one or more .mdl files: meshes, materials, attributes, bones, vertex layout and counts.

Read-only. Needs numpy. Run:  python3 -I mdl_study.py <file.mdl> [<file.mdl> ...]
Uses mdl_read.py for geometry and its own small header walk for the vertex declaration (which mdl_read does not keep).
"""
import os
import struct
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdl_read as R  # noqa: E402

USAGE = {0: "POSITION", 1: "BLENDWEIGHT", 2: "BLENDINDICES", 3: "NORMAL", 4: "UV", 6: "TANGENT", 7: "COLOR"}
KIND = {1: "float2", 2: "float3", 3: "float4", 5: "ubyte4", 8: "ubyte4n", 13: "half2", 14: "half4", 16: "ubyte8n", 17: "ubyte8"}


def declarations(path: str):
    """One list of (stream, offset, type name, usage name) per mesh, in file order."""
    data = open(path, "rb").read()
    mesh_count = struct.unpack_from("<IIIHH", data, 0)[3]  # vertex declaration count (the fix in mdl_read.py)
    out = []
    for i in range(mesh_count):
        block = data[R.HEADER_SIZE + R.DECL_SIZE * i:R.HEADER_SIZE + R.DECL_SIZE * (i + 1)]
        out.append([(s, o, KIND.get(k, f"type{k}"), USAGE.get(u, f"usage{u}") + (str(ui) if u in (4, 7) else ""))
                    for s, o, k, u, ui in R._elements(block)])
    return out


def summarize(path: str) -> str:
    m = R.read_mdl(path)
    decls = declarations(path)
    lines = [f"file: {path}", f"bones: {len(m.bones)}  meshes: {len(m.meshes)}"]
    lines.append("bone list: " + ", ".join(m.bones))
    for i, me in enumerate(m.meshes):
        if len(me.positions) == 0:  # e.g. the empty top_a placeholder mesh of the Track Suit
            lines.append(f"  mesh {i}: material {me.material}\n    vertices 0 (empty placeholder, no geometry)")
            continue
        lo, hi = me.positions.min(0), me.positions.max(0)
        attrs = sorted({a for sub in me.submeshes for a in sub[2]})
        used = sorted({m.bones[j] for j in set(me.joints[me.weights > 0].ravel().tolist())})
        layout = ", ".join(f"{u}:{k}@s{s}+{o}" for s, o, k, u in decls[i])
        lines += [f"  mesh {i}: material {me.material}",
                  f"    vertices {len(me.positions)}, triangles {len(me.triangles)}, submeshes {len(me.submeshes)}, attributes {attrs or 'none'}",
                  f"    bbox min {lo.round(3).tolist()} max {hi.round(3).tolist()}",
                  f"    bones used (weight>0): {len(used)}: {', '.join(used)}",
                  f"    vertex layout: {layout}"]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        print(summarize(p))
        print()
