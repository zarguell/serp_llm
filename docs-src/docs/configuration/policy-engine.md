# Policy Engine — Rule Syntax

Policies are YAML rules evaluated in order. First match wins.

## Match Criteria

```yaml
policies:
  - name: reddit
    match:
      domain: "*.reddit.com"         # Exact domain or glob
      domain_glob: ["*.wsj.com"]     # List of domain globs
      url_pattern: ".*/pricing"      # URL regex
      api_key_id: "key_agent1"       # Specific API key
      content_type: "search"         # "search" or "extract"
      query_contains: ["diagnosis"]  # Search query keywords
      on_error_class: ["403", "bot_detected"]  # Error-based fallback
```

## Actions

```yaml
  - name: paywalled_news
    match:
      domain_glob: ["*.wsj.com", "*.nytimes.com"]
    extract_provider: playwright    # Override provider
    search_provider: brave          # Override search provider
    proxy: gluetun                  # Route through proxy
    playwright_profile: wsj_session # Use specific session
    fallback_chain:                 # Custom fallback order
      - playwright
      - firecrawl
    dlp_policy: no_cloud_health     # Apply DLP policy
    allowed_providers:              # Restrict to these
      - searxng
      - crawl4ai
```

## Dry Run — Preview Policy Decisions

Append `?dry_run=true` to `/search` or `/extract` to see what the policy engine would decide without executing the request. Useful for debugging routing rules and verifying fallback chains.

```bash
# Preview search routing
curl -X POST "http://localhost:8080/search?dry_run=true" \
  -H "Authorization: Bearer $AGENT1_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning papers", "num_results": 5}'

# Preview extract routing
curl -X POST "http://localhost:8080/extract?dry_run=true" \
  -H "Authorization: Bearer $AGENT1_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.reddit.com/r/python"}'
```

Response shows the full routing decision:

```json
{
  "decision": {
    "policy_matched": "reddit",
    "provider": "invisible_playwright",
    "proxy": "gluetun",
    "fallback_chain": ["firecrawl", "jina"],
    "retry_strategy": "fallback",
    "dlp_policy": null,
    "judge_invoked": false,
    "judge_reasoning_tag": null
  },
  "request_id": "req_a1b2c3"
}
```

**Fields:**

| Field | Description |
|-------|-------------|
| `policy_matched` | Name of the matched policy rule, or `null` if no rule matched (uses defaults) |
| `provider` | Provider selected for this request |
| `proxy` | Named proxy, or `null` if no proxy |
| `fallback_chain` | Ordered list of fallback providers |
| `retry_strategy` | Retry strategy from the matched rule |
| `dlp_policy` | DLP policy applied, or `null` |
| `judge_invoked` | Whether the LLM judge was consulted for this decision |
| `judge_reasoning_tag` | Tag from the LLM judge explaining its reasoning |
