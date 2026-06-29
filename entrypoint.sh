#!/bin/sh
set -e

# Ensure volume-mounted directories are writable by the non-root user.
# Docker bind mounts inherit host ownership, which may not match
# the container UID. Fix ownership only if the directory already exists
# and is not writable (bind mount scenario).
for dir in /app/data /app/logs /app/sessions; do
    if [ -d "$dir" ] && [ ! -w "$dir" ]; then
        chown "$(id -u):$(id -g)" "$dir" 2>/dev/null || true
    fi
done

# Build uvicorn command.
# Default to h11 (pure-Python HTTP parser) to avoid httptools' strict Host
# header validation when behind a reverse proxy like Traefik.  httptools
# rejects Host headers that don't match the server address (421 Misdirected
# Request), which breaks MCP Streamable HTTP POST through Traefik.
#
# When FORWARDED_ALLOW_IPS is set, switch to httptools and trust the
# specified proxy IP(s).  Example: "172.18.0.2" or "172.18.0.0/16" for
# the Docker bridge network.
if [ -n "$FORWARDED_ALLOW_IPS" ]; then
    exec uvicorn serp_llm.main:app --host 0.0.0.0 --port 8080 \
        --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
else
    exec uvicorn serp_llm.main:app --host 0.0.0.0 --port 8080 \
        --http h11
fi
