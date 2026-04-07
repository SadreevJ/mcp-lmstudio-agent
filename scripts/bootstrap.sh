#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f ".env" ]]; then
  cp ".env.example" ".env"
fi
python3 scripts/run_cli.py bootstrap
