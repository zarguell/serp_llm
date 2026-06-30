# Authenticated Extraction for Bot-Protected Sites

Some sites (Reddit, Twitter/X, WSJ, etc.) block headless browsers or serve
CAPTCHAs to unauthenticated traffic. The gateway handles this at two levels:

- **Policy routing** — send the domain to a stealth browser provider
  (`invisible_playwright`, `flaresolverr`) that has better anti-detection.
- **Cookie sessions** — provide authenticated cookies so the browser appears
  logged in, which avoids CAPTCHAs entirely.

## Reddit End-to-End

### 1. Policy rule (already applied)

`config.selfhosted.yaml` routes `*.reddit.com` to InvisiblePlaywright:

```yaml
policies:
  - name: reddit
    match:
      domain_glob: "*.reddit.com"
    extract_provider: invisible_playwright
```

This sends all Reddit extract requests through the stealth Firefox browser
instead of the default Jina/Crawl4AI fallback chain.

### 2. Create a cookie session

You need cookies from a real logged-in Reddit session. The gateway stores
them encrypted and makes them available to InvisiblePlaywright.

**Option A: Admin UI** (easier)

1. Open `https://your-domain/admin` and log in with an admin API key.
2. Navigate to **Sessions** in the sidebar.
3. Click **Create Session** and fill in:
   - **Session ID:** `reddit_session_1`
   - **Browser:** `invisible_playwright`
   - **Domain:** `reddit.com`
4. For the cookie values, export them from your real browser first (see below).

**Option B: Admin API**

```bash
curl -k -X POST https://gateway.localhost/admin/sessions/create \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "reddit_session_1",
    "browser": "invisible_playwright",
    "domain": "reddit.com",
    "cookies": [
      {"name": "token", "value": "<reddit_session_token>", "domain": ".reddit.com"},
      {"name": "loid", "value": "<loid_value>", "domain": ".reddit.com"},
      {"name": "session_tracker", "value": "<session_tracker>", "domain": ".reddit.com"}
    ],
    "user_agent": "Mozilla/5.0 ..."
  }'
```

### 3. Export cookies from your real browser

**Before you start:** Open Reddit in your real browser and **log in**. The
session must be authenticated.

**Chrome / Brave / Edge:**

1. Press `F12` to open DevTools, go to the **Application** tab.
2. In the left sidebar, expand **Cookies** and select `https://www.reddit.com`.
3. Click anywhere in the cookie table, press `Ctrl+A` to select all, `Ctrl+C` to copy.
4. Paste into a text file — you'll see tab-separated values.
5. Extract the `name` and `value` columns for each row.

The minimum cookies you need for Reddit:
- `token` — the main session token (required)
- `loid` — device identifier
- `session_tracker` — session tracking

**Firefox:**

1. Press `F12` to open DevTools, go to the **Storage** tab.
2. Expand **Cookies** and select `https://www.reddit.com`.
3. Right-click any cookie → **Select All**, then right-click → **Copy**.
4. Paste and extract `name`/`value` pairs.

> **Security:** Cookie values are encrypted at rest in the session store.
> They are never returned in API list/status responses.

### 4. Extract with the session

Once the session is saved, pass `session_profile` in extract requests:

```bash
curl -k -X POST https://gateway.localhost/extract \
  -H "Authorization: Bearer $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.reddit.com/r/programming/",
    "session_profile": "reddit_session_1"
  }'
```

InvisiblePlaywright loads Reddit with the stored cookies. The server sees a
logged-in Firefox session and serves the page without challenges.

For **MCP** clients, pass `session_profile` as an extract parameter — your
agent sends it in the tool call arguments.

### 5. Session lifecycle

- Sessions are stored in `./sessions/` (volume-mounted in the compose file)
- They persist across container restarts
- When Reddit invalidates a session (logout, password change), the gateway
  auto-detects login walls and invalidates the session automatically
- Refresh a session by repeating the cookie export and updating via the
  Admin UI or the `/admin/sessions/update` endpoint

### Auto-invalidation

When `auto_invalidate_on_login_wall` is enabled (default), the gateway checks
response content for login-wall patterns. If Reddit returns a login page, the
session is automatically marked invalid and subsequent requests fall back to
the unauthenticated provider chain.

## Other Sites

The same approach works for any domain that InvisiblePlaywright supports:

| Site | Domain | Notes |
|---|---|---|
| Reddit | `reddit.com` | Needs `token` + `loid` cookies |
| Twitter/X | `twitter.com` | Needs `auth_token` + `ct0` cookies |
| WSJ | `wsj.com` | Paywall, needs full subscription cookies |
| NYT | `nytimes.com` | Paywall, needs `NYT-S` cookie |
| Bloomberg | `bloomberg.com` | Paywall, needs session cookies |

For each site:
1. Log in via your real browser
2. Export cookies for the domain
3. Create a session via Admin UI or API
4. Pass `session_profile` in extract requests
5. Add a policy rule to route the domain to `invisible_playwright`
