#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UVICORN="$ROOT_DIR/backend/.venv/bin/uvicorn"
PORT="${CREDWEAVE_JURY_PORT:-8080}"

if [[ ! "$PORT" =~ ^[0-9]{1,5}$ ]] || (( 10#$PORT < 1 || 10#$PORT > 65535 )); then
  printf 'CREDWEAVE_JURY_PORT must be a port number from 1 to 65535.\n' >&2
  exit 1
fi

if [[ ! -x "$UVICORN" || ! -x "$ROOT_DIR/frontend/node_modules/.bin/vite" ]]; then
  printf 'Install the backend and frontend dependencies first. See README.md.\n' >&2
  exit 1
fi

DEMO_DIR="$(mktemp -d)"
SERVER_PID=""
cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf -- "$DEMO_DIR"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'Building the CREDWEAVE AI jury demo…\n'
VITE_API_BASE_URL='' npm --prefix "$ROOT_DIR/frontend" run build -- --mode jury --outDir "$DEMO_DIR/frontend" --emptyOutDir

export DATABASE_URL="sqlite:///$DEMO_DIR/demo.sqlite3"
export DEMO_MODE=1
export CREDWEAVE_JURY_FRONTEND="$DEMO_DIR/frontend"
cd "$ROOT_DIR/backend"
printf '\nOpen http://127.0.0.1:%s/demo once startup completes. Press Ctrl+C to stop the demo.\n\n' "$PORT"
"$UVICORN" app.jury:app --host 127.0.0.1 --port "$PORT" --timeout-graceful-shutdown 3 &
SERVER_PID=$!
wait "$SERVER_PID"
