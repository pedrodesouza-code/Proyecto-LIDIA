#!/usr/bin/env sh
set -eu

cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

python -m devops.install_missing
python -m devops.run_all_checks
