#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
python_cli="${OTTER_CAD_PYTHON:-/usr/bin/python3}"

# Generated binaries stay ignored. A clean checkout rebuilds from the exact
# source closure; it never substitutes an arbitrary downloaded CAD binary.
"$python_cli" "$script_dir/verify-cad-kernel-source.py"
if ! "$python_cli" "$script_dir/verify-cad-kernel-binaries.py" --check-receipt >/dev/null; then
  printf '%s\n' 'CAD source/toolchain/binary receipt is missing or stale; rebuilding from exact source.' >&2
  "$script_dir/build-cad-kernel.sh" --clean-rebuild
fi
"$python_cli" "$script_dir/verify-cad-kernel-binaries.py" --check-receipt >/dev/null
