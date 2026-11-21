#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="http://127.0.0.1:8000/api/health"
FRONTEND_URL="http://127.0.0.1:5173/"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  trap - EXIT INT TERM
  for pid in "$BACKEND_PID" "$FRONTEND_PID"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  for pid in "$BACKEND_PID" "$FRONTEND_PID"; do
    if [[ -n "$pid" ]]; then
      wait "$pid" 2>/dev/null || true
    fi
  done
}

portal_responds() {
  local name="$1"
  local url="$2"
  local response

  if ! response=$(curl --silent --show-error --max-time 2 --include "$url" 2>/dev/null); then
    return 1
  fi

  if [[ "$name" == API ]]; then
    [[ ${response,,} == *$'\nx-credweave-mode: portal\r\n'* ]] && return 0
  elif [[ "$response" == *'<meta name="credweave-mode" content="development" />'* ||
          "$response" == *'<meta name="credweave-mode" content="production" />'* ]]; then
    return 0
  fi

  printf '%s answered at %s, but it is not the current CredWeave portal. Stop the old server and rerun ./scripts/run-project.sh.\n' "$name" "$url" >&2
  return 2
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local pid="$3"
  local attempt

  for attempt in {1..60}; do
    if portal_responds "$name" "$url"; then
      printf '%s is ready: %s\n' "$name" "$url"
      return 0
    elif [[ $? == 2 ]]; then
      return 1
    fi
    if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
      printf '%s exited before becoming ready. Check the startup output above.\n' "$name" >&2
      return 1
    fi
    sleep 1
  done

  printf '%s did not respond within 60 seconds: %s\n' "$name" "$url" >&2
  return 1
}

if ! command -v curl >/dev/null 2>&1; then
  printf 'curl is required to check service readiness.\n' >&2
  exit 1
fi

if [[ ! -x "$ROOT_DIR/backend/.venv/bin/uvicorn" ]]; then
  printf 'Backend environment not found. Install backend dependencies first; see README.md.\n' >&2
  exit 1
fi

if [[ ! -x "$ROOT_DIR/frontend/node_modules/.bin/vite" ]]; then
  printf 'Frontend dependencies not found. Run npm ci in frontend/ first.\n' >&2
  exit 1
fi

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  printf 'Local .env not found. Copy .env.example to .env and configure DATABASE_URL first.\n' >&2
  exit 1
fi

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if portal_responds API "$BACKEND_URL"; then
  printf 'API already responds: %s\n' "$BACKEND_URL"
elif [[ $? == 2 ]]; then
  exit 1
else
  "$ROOT_DIR/scripts/start-backend.sh" &
  BACKEND_PID=$!
  wait_for_url "API" "$BACKEND_URL" "$BACKEND_PID"
fi

if portal_responds Frontend "$FRONTEND_URL"; then
  printf 'Frontend already responds: %s\n' "$FRONTEND_URL"
elif [[ $? == 2 ]]; then
  exit 1
else
  "$ROOT_DIR/scripts/start-frontend.sh" &
  FRONTEND_PID=$!
  wait_for_url "Frontend" "$FRONTEND_URL" "$FRONTEND_PID"
fi

printf '\nCREDWEAVE AI is running.\n'
printf 'Sign-in portal: http://localhost:5173/\n'
printf 'API docs: http://localhost:8000/docs\n'
printf 'API health: http://localhost:8000/api/health\n'

if [[ -z "$BACKEND_PID" && -z "$FRONTEND_PID" ]]; then
  printf '\nBoth services were already running.\n'
  exit 0
fi

printf 'Press Ctrl+C to stop services started by this script.\n\n'

if [[ -n "$BACKEND_PID" && -n "$FRONTEND_PID" ]]; then
  wait -n "$BACKEND_PID" "$FRONTEND_PID"
elif [[ -n "$BACKEND_PID" ]]; then
  wait "$BACKEND_PID"
else
  wait "$FRONTEND_PID"
fi
