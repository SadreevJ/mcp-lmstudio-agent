#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/switch-project.sh PROJECT_NAME"
  exit 1
fi
python3 scripts/run_cli.py switch-project "$1"
