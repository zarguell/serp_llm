# config.yaml Reference

The `config.yaml` file defines all routing behavior, provider configuration, and operational parameters. It is safe to commit to version control — secrets live in `.env`.

## Structure

```yaml
# Top-level keys
max_concurrency:  # Max concurrent in-flight requests (semaphore)
defaults:         # Default behavior when no policy matches
policies:         # Routing rules (evaluated in order, first match wins)
proxies:          # Named proxy definitions
providers:        # Provider adapter configuration
llm_judge:        # LLM-based routing fallback
dlp_policies:     # Data loss prevention rules
auth:             # Static API keys (legacy, prefer SQLite-backed)
logging:          # Audit log configuration
sessions:         # Cookie jar / session store
stealth:          # Stealth browser settings
cache:            # Response cache configuration
circuit_breaker:  # Per-provider failure thresholds
quotas:           # Usage limits per provider
rate_limiting:    # Sliding window rate limiting
alerts:           # Webhook alerting
mcp:              # MCP server settings
post_processing:  # Content cleaning pipeline
```

## Defaults

```yaml
defaults:
  search_provider: searxng
  extract_provider: jina
  timeout: 15
  retry:
    strategy: fallback
    max_attempts: 3
    fallback_chain:
      - jina
      - firecrawl
      - playwright
```

## Providers

```yaml
providers:
  searxng:
    base_url: http://searxng:8080
  jina:
    api_key: ${JINA_API_KEY}
  brave:
    api_key: ${BRAVE_API_KEY}
```

Provider config values support `${ENV_VAR}` and `${ENV_VAR:-default}` syntax.

### max_concurrency

```yaml
max_concurrency: 3
```

Controls how many requests can hit providers simultaneously. When the LLM
sends more requests than this limit, excess requests queue in memory until a
slot opens. Prevents provider overload on modest hardware.

**Tuning guide:**
- 4‑core / 16 GB system: start at **2–3**
- 8‑core / 32 GB system: **4–6**
- 16+ cores: **8–16** (or disable with a high value)

The semaphore wraps only the provider dispatch call — policy evaluation,
DLP, and cache lookup still run concurrently. A value that is **too high**
provides no protection. A value that is **too low** underutilises available
bandwidth on large instances.

### rate_limiting

Sliding window rate limiting for search and extract endpoints.

```yaml
rate_limiting:
  enabled: true
  by_key:
    requests: 60
    window_seconds: 60
  by_ip:
    requests: 30
    window_seconds: 60
  cleanup_interval_seconds: 300
```

- `enabled`: Set to `true` to activate rate limiting (default: `false`).
- `by_key.requests`: Max requests per API key in the sliding window.
- `by_key.window_seconds`: Width of the sliding window in seconds.
- `by_ip.requests`: Max requests per client IP in the sliding window.
- `cleanup_interval_seconds`: How often stale tracking buckets are pruned.

### SSRF Protection (always active)

User-supplied URLs in `POST /extract` are validated for SSRF safety before any
provider dispatch. The validator:

- Rejects non-http/https schemes (file://, ftp://, data:, etc.)
- Blocks hostnames that resolve to private/reserved IP ranges (RFC 1918,
  loopback, link-local, carrier-grade NAT)
- Blocks known metadata endpoints (AWS/GCP internal hostnames)
- Uses `HttpUrl` pydantic validation for URL format

This protection is always active and does not require configuration.
