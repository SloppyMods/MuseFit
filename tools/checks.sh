#!/usr/bin/env bash
# MuseFit check: every tools/*.py parses, and no bytecode (.pyc / __pycache__) is left in tools/. Writes nothing.
# Run from anywhere:  bash tools/checks.sh   (exit 0 = fine)
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -I -B - <<'PY'
import pathlib
import sys

files = sorted(pathlib.Path("tools").glob("*.py"))
if not files:
    sys.exit("no tools/*.py")
bad = 0
for f in files:
    try:
        compile(f.read_text(), str(f), "exec")  # parse only; compile() does not write a .pyc
    except SyntaxError as e:
        print(f"SYNTAX ERROR {f}: {e}", file=sys.stderr)
        bad += 1
leftovers = list(pathlib.Path("tools").rglob("*.pyc")) + list(pathlib.Path("tools").rglob("__pycache__"))
if leftovers:
    print(f"bytecode left in tools/: {leftovers}", file=sys.stderr)
    bad += 1
print(f"{len(files)} tools/*.py checked, {bad} problem(s)")
sys.exit(1 if bad else 0)
PY
