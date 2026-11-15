# New file for MuseFit (skeleton check, 2026-11-14).
"""Read an FFXIV skeleton (.sklb) and compare it with the skeleton a build .glb carries. Read-only. Needs numpy.

    python3 -I -B sklb_study.py <skeleton.sklb> <build.glb> [--list]

An .sklb is a small FFXIV header ("blks...") followed by a Havok binary tagfile; havok_tagfile.py reads it. Version 3
tagfiles (vanilla) read as is; version 5 ones (exported with hk_2014.2.5) start with an SDK version string, which also counts
as the first remembered string, and a few header bytes before the first class definition; this script handles that.

Prints: every hkaSkeleton in the file (name, bone count); for the one whose bone count matches the .glb (else the first):
bones missing on either side, parent differences, the chest and physics bones with parents, the rest-pose world position
difference to the .glb (from its inverse bind matrices) for the bones the build's meshes weight, and which weighted bones
are not in the skeleton. --list also prints every bone: index, name, parent, local translation, rotation (x y z w), scale.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import glb_raw as g  # noqa: E402
import havok_tagfile as tf  # noqa: E402
import muse_geom as mg  # noqa: E402

MAGIC = bytes.fromhex("1e0db0cacefa11d0")
CHEST = ("mune", "kyokin", "nipple", "fukubu", "c_mune")


def skeletons(path: str) -> list[dict]:
    data = open(path, "rb").read()
    tag = data[data.find(MAGIC):]
    reader = tf.Reader(tag)
    if tag[8:10] == b"\x02\x0a":  # version 5: "hk_2014..." string first
        size = tag[10] >> 1
        reader.version = 5
        reader.strings.append(tag[11:11 + size].decode("latin1"))
        reader.p = tag.find(b"\x04\x28hkRootLevelContainer")
        if reader.p < 0:
            sys.exit("version 5 tagfile without hkRootLevelContainer: unknown layout")
    reader.read()
    return [o for o in reader.objs[1:] if o and o["__class__"] == "hkaSkeleton"]


def quat_matrix(t: tuple) -> np.ndarray:
    x, y, z, w = t[4:8]
    m = np.eye(4)
    m[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                 [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                 [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    m[:3, :3] *= np.array(t[8:11])[None, :]
    m[:3, 3] = t[0:3]
    return m


def world(skel: dict) -> np.ndarray:
    parents, pose = skel["parentIndices"], skel["referencePose"]
    out = [None] * len(parents)

    def solve(i: int) -> np.ndarray:
        if out[i] is None:
            local = quat_matrix(pose[i])
            out[i] = local if parents[i] < 0 else solve(parents[i]) @ local
        return out[i]

    return np.stack([solve(i) for i in range(len(parents))])


def weighted_bones(path: str) -> dict[str, set[str]]:
    doc, blob, skin, cloth = mg.load(path)
    names = mg.bone_names(doc)
    return {"skin": {names[i] for i in np.flatnonzero(skin["W"].sum(0) > 0)},
            "cloth": {names[i] for i in np.flatnonzero(cloth["W"].sum(0) > 0)}}


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    sk_path, glb_path = args
    found = skeletons(sk_path)
    print(f"{os.path.basename(sk_path)}: {len(found)} hkaSkeleton: " + ", ".join(f"{s.get('name')} ({len(s['bones'])})" for s in found))
    doc, blob = g.load(glb_path)
    gnames, grest = g.joint_matrices(doc, blob)
    gpar = g.joint_parents(doc)
    skel = next((s for s in found if len(s["bones"]) == len(gnames)), found[0])
    names = [b["name"] for b in skel["bones"]]
    par = skel["parentIndices"]
    W = world(skel)
    print(f"using '{skel.get('name')}' ({len(names)} bones) against {os.path.basename(glb_path)} ({len(gnames)} joints)")
    only_s, only_g = sorted(set(names) - set(gnames)), sorted(set(gnames) - set(names))
    print(f" bones only in the .sklb: {len(only_s)} {only_s[:20]}")
    print(f" bones only in the .glb:  {len(only_g)} {only_g[:20]}")
    gi = {n: i for i, n in enumerate(gnames)}
    pdiff = [(n, names[par[i]] if par[i] >= 0 else None, gnames[gpar[gi[n]]] if gpar[gi[n]] >= 0 else None)
             for i, n in enumerate(names) if n in gi and (names[par[i]] if par[i] >= 0 else None) != (gnames[gpar[gi[n]]] if gpar[gi[n]] >= 0 else None)]
    print(f" parent differences: {len(pdiff)} {pdiff[:10]}")
    print(" chest / belly / physics bones (name <- parent; world position m):")
    for i, n in enumerate(names):
        if any(k in n for k in CHEST) and not n.startswith("nf_"):
            print(f"   {n:20s} <- {names[par[i]]:14s} {np.round(W[i][:3, 3], 4)}")
    used = weighted_bones(glb_path)
    for part, bones in used.items():
        missing = sorted(b for b in bones if b not in names)
        d = np.array([np.linalg.norm(W[names.index(b)][:3, 3] - grest[gi[b]][:3, 3]) * 1000 for b in sorted(bones) if b in names and b in gi])
        print(f" {part}: {len(bones)} weighted bones, missing from the .sklb: {missing}; rest position .sklb vs .glb mm: "
              f"median {np.median(d):.2f}, max {d.max():.2f}")
        worst = sorted(((np.linalg.norm(W[names.index(b)][:3, 3] - grest[gi[b]][:3, 3]) * 1000, b) for b in bones if b in names and b in gi), reverse=True)[:6]
        print("   largest: " + ", ".join(f"{b} {v:.1f}" for v, b in worst))
    if "--list" in sys.argv:
        for i, n in enumerate(names):
            t = skel["referencePose"][i]
            print(f"{i:4d} {n:28s} <- {names[par[i]] if par[i] >= 0 else '-':24s} t {np.round(t[0:3], 5)} q {np.round(t[4:8], 5)} s {np.round(t[8:11], 4)}")


if __name__ == "__main__":
    main()
