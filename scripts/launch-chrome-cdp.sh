#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-9222}"
PROFILE_DIR="/tmp/chrome-cdp-profile"
POLL_INTERVAL=0.5
POLL_ATTEMPTS=10  # 10 * 0.5s = 5s total

# Check if Chrome is already listening on the debug port
if curl -sf "http://localhost:${PORT}/json/version" > /dev/null 2>&1; then
    echo "Chrome CDP already running on port ${PORT}"
    exit 0
fi

# Detect Chrome binary
if [[ "$(uname)" == "Darwin" ]]; then
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if [[ ! -x "$CHROME" ]]; then
        echo "Error: Chrome not found at ${CHROME}" >&2
        exit 1
    fi
elif [[ "$(uname)" == "Linux" ]]; then
    CHROME=""
    for candidate in google-chrome google-chrome-stable; do
        if path="$(which "${candidate}" 2>/dev/null)"; then
            CHROME="${path}"
            break
        fi
    done
    if [[ -z "${CHROME}" ]]; then
        echo "Error: Chrome not found (tried: google-chrome, google-chrome-stable)" >&2
        exit 1
    fi
else
    echo "Error: Unsupported platform $(uname)" >&2
    exit 1
fi

echo "Launching Chrome CDP on port ${PORT}..."

# Ensure profile directory exists
mkdir -p "${PROFILE_DIR}"

nohup "${CHROME}" \
    --remote-debugging-port="${PORT}" \
    --remote-debugging-address=0.0.0.0 \
    --user-data-dir="${PROFILE_DIR}" \
    --no-first-run \
    --no-default-browser-check \
    > /dev/null 2>&1 &

# Wait for the debug port to become available
for ((i = 1; i <= POLL_ATTEMPTS; i++)); do
    sleep "${POLL_INTERVAL}"
    if curl -sf "http://localhost:${PORT}/json/version" > /dev/null 2>&1; then
        echo "Chrome CDP ready on port ${PORT}"
        exit 0
    fi
done

echo "Error: Chrome CDP failed to start on port ${PORT} within 5 seconds" >&2
exit 1
