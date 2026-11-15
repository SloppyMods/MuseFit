# New file for MuseFit (skeleton check, 2026-11-14).
"""Write a CHECK-ONLY copy of a build whose mesh sits on another skeleton's rest pose. Never import its output into Penumbra.

    python3 -I -B skeleton_rest_glb.py <build.glb> <skeleton.sklb> <out.glb>

Every vertex of every mesh (skin and cloth) is carried from the build's rest pose onto the .sklb's rest pose by its own bone
weights (the same carry posed_clip.py --skeleton uses), and the skin's inverse bind matrices are replaced by the .sklb's.
Checks that read the skeleton from the file (e.g. XIVAutoFit's dionys_exposed.py) then pose about the new rest pose.
NORMAL is left as it was (the c0201 -> c0801 change is a move of the bones, with at most a 3.4 degree turn at j_kosi).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import glb_raw as g  # noqa: E402
import muse_geom as mg  # noqa: E402
import posed_clip  # noqa: E402


def main(src: str, sklb: str, out: str) -> None:
    if os.path.exists(out):
        sys.exit(f"refusing to overwrite {out}")
    doc, blob = g.load(src)
    names, rest = g.joint_matrices(doc, blob)
    target = posed_clip.skeleton_rest(sklb, names, rest)
    base = target @ np.linalg.inv(rest)
    writer = g.GlbWriter(doc, blob)
    for prim in g.primitives(doc):
        P = g.read_accessor(doc, blob, prim["attributes"]["POSITION"]).astype(float)
        W = mg.dense_weights(doc, blob, prim, len(names))
        moved = mg.posed(P, W, base)
        writer.doc["meshes"][prim["mesh"]]["primitives"][prim["prim"]]["attributes"]["POSITION"] = writer.add_accessor(moved.astype("<f4"), 5126, "VEC3")
    inverse = np.linalg.inv(target).transpose(0, 2, 1).reshape(-1, 16)  # glTF stores matrices column by column
    writer.doc["skins"][0]["inverseBindMatrices"] = writer.add_accessor(inverse.astype("<f4"), 5126, "MAT4")
    writer.save(out)
    print(f"wrote {out}: bones moved median {np.median(np.linalg.norm(target[:, :3, 3] - rest[:, :3, 3], axis=1)) * 1000:.1f} mm (CHECK ONLY)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
