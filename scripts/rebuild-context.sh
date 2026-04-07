#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -eq 0 ]]; then
  python3 scripts/run_cli.py rebuild-context
else
  python3 scripts/run_cli.py rebuild-context --project "$1"
fi
