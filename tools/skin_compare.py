"""How far is each body's skin from the Muse skin? New file for MuseFit. Read-only. Needs numpy only.

    python3 -I -B skin_compare.py <muse body.mdl> <label=other.mdl[:mesh index]> [...]

Reads the skin mesh of the Muse .mdl (mesh 0) and of each other .mdl (mesh index after a colon, default 0) and prints the distance from
every vertex of the other body to the nearest Muse vertex: all vertices, and the chest (|x| < 0.12, y 1.16-1.32, front = +z), plus
how far forward the chest sticks out (front-most z). Vertex to nearest vertex, not to the surface, so a few mm are the mesh density.
"""
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdl_read as R  # noqa: E402
import techie_compare as T  # noqa: E402


def chest(p):
    return (abs(p[:, 0]) < 0.12) & (p[:, 1] > 1.16) & (p[:, 1] < 1.32) & (p[:, 2] > 0)


def main(argv):
    muse = R.read_mdl(argv[0]).meshes[0].positions
    for spec in argv[1:]:
        label, path = spec.split("=", 1)
        index = 0
        if ":" in path and path.rsplit(":", 1)[1].isdigit():
            path, index = path.rsplit(":", 1)[0], int(path.rsplit(":", 1)[1])
        other = R.read_mdl(path).meshes[index].positions
        d, _ = T.nearest(other, muse)
        print(f"{label} -> Muse, all {len(other)} vertices: {T.stats(d)}")
        c = chest(other)
        print(f"{label} -> Muse, chest {int(c.sum())} vertices: {T.stats(d[c])}; chest front-most z {other[c][:, 2].max():.3f} (Muse {muse[chest(muse)][:, 2].max():.3f})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1:])
