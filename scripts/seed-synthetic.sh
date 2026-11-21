#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"
source .venv/bin/activate
if [[ -f ../.env ]]; then
  set -a
  source ../.env
  set +a
fi
python -m app.seed
