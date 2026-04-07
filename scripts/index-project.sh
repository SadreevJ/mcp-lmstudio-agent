#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -eq 0 ]]; then
  python3 scripts/run_cli.py index-project
else
  python3 scripts/run_cli.py index-project --project "$1"
fi
