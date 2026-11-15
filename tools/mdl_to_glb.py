# New file for MuseFit.
"""Write one mesh of a .mdl as a Penumbra-style skinned .glb, with no Penumbra export and no Blender. New file for MuseFit.

Penumbra's glTF export fails on the Muse body, so the body has to be built straight from its .mdl file.

    python3 -I -B mdl_to_glb.py <body.mdl> <shell.glb> <out.glb> [mesh index (0)] [material substring ("bibo")]

- The skeleton (nodes, inverse bind matrices) is copied from <shell.glb>, any Penumbra export of a c0201 outfit
  (the Track Suit export works). Every bone the .mdl uses must exist in that skeleton, or the script stops.
- The chosen mesh is split by submesh into "mesh 0.N". The .mdl's atr_* tags become node extras `true`.
- Attribute names follow Penumbra's export: UV0 (float4) -> TEXCOORD_0 + TEXCOORD_1, UV1 (float2) -> TEXCOORD_2,
  COLOR0 -> _FFXIV_COLOR (normalised ushort), BLENDINDICES/BLENDWEIGHT -> JOINTS_0/1 + WEIGHTS_0/1 (by bone name).
- No TANGENT is written (hard rule: Penumbra computes it on import).
- The material is only named (/mt_c0201b0001_bibo.mtrl); no textures are written.

Refuses to overwrite <out.glb>. `compare_export.py` checks this converter against a real Penumbra export.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_raw  # noqa: E402
import mdl_read as R  # noqa: E402

FLOAT, USHORT, UBYTE = 5126, 5123, 5121
SKELETON_NODES = 455  # nodes 0..454 of a c0201 export are the bones; the mesh nodes follow


def submesh_vertices(mesh: R.MdlMesh, first: int, count: int):
    """(vertex ids used by this submesh in order of first use, its triangles re-indexed to those ids)."""
    tris = mesh.triangles.reshape(-1)[first:first + count].reshape(-1, 3)
    flat = tris.reshape(-1)
    first_seen = np.unique(flat, return_index=True)
    used = first_seen[0][np.argsort(first_seen[1])]  # Penumbra numbers the vertices in order of first use
    lookup = np.full(len(mesh.positions), -1, np.int64)
    lookup[used] = np.arange(len(used))
    return used, lookup[tris]


def weights_by_joint(mesh: R.MdlMesh, bones: tuple, joint_of: dict, rows: np.ndarray):
    """(n,8) joint indices into the shell skin and (n,8) weights for the chosen vertex rows."""
    j = np.array([joint_of[b] for b in bones], np.int64)[mesh.joints[rows]]
    w = mesh.weights[rows]
    w = w / np.maximum(w.sum(1, keepdims=True), 1e-12)  # ubyte8 weights come raw (0..255); scale each row to sum 1
    j[w <= 0] = 0
    return j, w


def build(mdl_path: str, shell_path: str, out_path: str, mesh_index: int = 0, material_part: str = "bibo") -> None:
    model = R.read_mdl(mdl_path)
    mesh = model.meshes[mesh_index]
    if material_part not in mesh.material:
        sys.exit(f"{mdl_path}: mesh {mesh_index} uses {mesh.material}, not a '{material_part}' material")
    shell_doc, shell_blob = glb_raw.load(shell_path)
    skin = shell_doc["skins"][0]
    names = [shell_doc["nodes"][n].get("name") for n in skin["joints"]]
    joint_of = {n: i for i, n in enumerate(names)}
    missing = [b for b in model.bones if b not in joint_of]
    if missing:
        sys.exit(f"bones in the .mdl but not in the shell skeleton: {missing}")
    if os.path.exists(out_path):
        sys.exit(f"refusing to overwrite {out_path}; pick a new name")

    doc = {"asset": {"version": "2.0", "generator": "MuseFit mdl_to_glb.py"},
           "nodes": [dict(n) for n in shell_doc["nodes"][:SKELETON_NODES]],
           "accessors": [], "bufferViews": [], "buffers": [{"byteLength": 0}], "meshes": [], "skins": [],
           "materials": [{"name": mesh.material}], "scene": 0, "scenes": [{"nodes": [0]}]}
    writer = glb_raw.GlbWriter(doc, b"")
    ibm = writer.copy_accessor(shell_doc, shell_blob, skin["inverseBindMatrices"])
    scene_nodes = [0]
    for number, (first, count, attrs) in enumerate(mesh.submeshes):
        rows, tris = submesh_vertices(mesh, first, count)
        joints, weights = weights_by_joint(mesh, model.bones, joint_of, rows)
        uv0, uv1 = mesh.uvs[0], mesh.uvs[1]
        a = {"POSITION": writer.add_accessor(mesh.positions[rows], FLOAT, "VEC3"),
             "NORMAL": writer.add_accessor(mesh.normals[rows], FLOAT, "VEC3"),
             "TEXCOORD_0": writer.add_accessor(uv0[rows][:, :2], FLOAT, "VEC2"),
             "TEXCOORD_1": writer.add_accessor(uv0[rows][:, 2:4], FLOAT, "VEC2"),
             "TEXCOORD_2": writer.add_accessor(uv1[rows][:, :2], FLOAT, "VEC2"),
             "_FFXIV_COLOR": writer.add_accessor(np.round(mesh.colors[rows] * 65535), USHORT, "VEC4", True),
             "JOINTS_0": writer.add_accessor(joints[:, :4], USHORT, "VEC4"),
             "JOINTS_1": writer.add_accessor(joints[:, 4:], USHORT, "VEC4"),
             "WEIGHTS_0": writer.add_accessor(weights[:, :4], FLOAT, "VEC4"),
             "WEIGHTS_1": writer.add_accessor(weights[:, 4:], FLOAT, "VEC4")}
        indices = writer.add_accessor(tris.reshape(-1), USHORT if len(rows) < 65535 else 5125, "SCALAR")
        writer.doc["meshes"].append({"name": f"mesh {mesh_index}.{number}", "primitives": [{"attributes": a, "indices": indices, "material": 0}]})
        writer.doc["skins"].append({"inverseBindMatrices": ibm, "joints": list(skin["joints"])})
        writer.doc["nodes"].append({"extras": {t: True for t in attrs}, "mesh": number, "skin": number})
        scene_nodes.append(len(writer.doc["nodes"]) - 1)
    writer.doc["scenes"][0]["nodes"] = scene_nodes
    writer.save(out_path)
    print(f"wrote {out_path}: {len(mesh.submeshes)} submeshes, {len(mesh.positions)} vertices, material {mesh.material}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 0,
          sys.argv[5] if len(sys.argv) > 5 else "bibo")
