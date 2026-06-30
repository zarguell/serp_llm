"""Reddit listing page extraction strategy.

Parses old.reddit.com listing HTML (subreddit feeds, search results) into
structured markdown with post titles, scores, comment counts, authors,
and URLs.  Individual post pages are handled by the default readability
extractor and don't reach this strategy.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from serp_llm.post_processing.strategies import StrategyResult

logger = logging.getLogger(__name__)

# Regex to extract individual post entries from old.reddit.com listing HTML
_THING_RE = re.compile(
    r'<div\s+class="thing[^"]*"\s+id="thing_([^"]+)"[^>]*'
    r'data-score="(\d+)"[^>]*'
    r'data-comments-count="(\d+)"[^>]*'
    r'data-author="([^"]*)"[^>]*'
    r'data-url="([^"]*)"[^>]*'
    r'data-rank="(\d+)"[^>]*'
    r'data-timestamp="(\d+)"[^>]*?>',
    re.DOTALL,
)

# Extract the post title (the <a> inside <p class="title">)
_TITLE_RE = re.compile(
    r'<p\s+class="title">.*?<a[^>]*class="title[^"]*"[^>]*>(.*?)</a>',
    re.DOTALL,
)

# Extract domain from <span class="domain">
_DOMAIN_RE = re.compile(
    r'<span\s+class="domain">.*?\(<a[^>]*>([^<]+)</a>\).*?</span>',
    re.DOTALL,
)

# Extract subreddit name from the page
_SUBREDDIT_RE = re.compile(
    r'data-subreddit="([^"]+)"',
    re.DOTALL,
)

# Extract "view more" / next page link
_NEXT_RE = re.compile(
    r'<span\s+class="next-button">.*?<a\s+href="([^"]+)"\s+rel="nofollow\s+next">',
    re.DOTALL,
)


def _parse_timestamp(ts_ms: str) -> str:
    """Convert a Unix millisecond timestamp to a relative time string."""
    try:
        ts = int(ts_ms) / 1000
        dt = datetime.fromtimestamp(ts, tz=UTC)
        now = datetime.now(tz=UTC)
        delta = now - dt
        if delta.days > 0:
            return f"{delta.days}d ago"
        if delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h ago"
        return f"{delta.seconds // 60}m ago"
    except (ValueError, OSError):
        return ""


def _clean_title(title: str) -> str:
    """Strip HTML tags and decode entities from a title."""
    title = re.sub(r"<[^>]+>", "", title)
    title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    title = title.replace("&quot;", '"').replace("&#x27;", "'").strip()
    return title


class RedditListingStrategy:
    """Extract post listings from old.reddit.com subreddit feeds."""

    async def extract(self, html: str, url: str) -> StrategyResult | None:
        """Parse old.reddit.com listing HTML into structured markdown.

        Returns ``None`` if the page doesn't look like a Reddit listing
        (no ``thing`` divs found), letting the next strategy in the
        priority chain handle it.
        """
        matches = _THING_RE.findall(html)
        if not matches:
            return None

        # Determine subreddit name
        sr_match = _SUBREDDIT_RE.search(html)
        subreddit = sr_match.group(1) if sr_match else "reddit"

        lines: list[str] = []
        lines.append(f"## r/{subreddit}")
        lines.append("")

        for match in matches:
            thing_id, score, comments, author, data_url, rank, timestamp = match
            rank_num = int(rank)

            # Extract title from within this thing's block
            # We search for the title in a block scoped to this thing
            thing_block_match = re.search(
                rf'<div\s+class="thing[^"]*"\s+id="thing_{re.escape(thing_id)}".*?</div>\s*</div>\s*<div\s+class="clearleft">',
                html,
                re.DOTALL,
            )
            title = ""
            domain = ""
            if thing_block_match:
                thing_block = thing_block_match.group(0)
                title_match = _TITLE_RE.search(thing_block)
                if title_match:
                    title = _clean_title(title_match.group(1))

                domain_match = _DOMAIN_RE.search(thing_block)
                if domain_match:
                    domain = domain_match.group(1).strip()

            if not title:
                continue

            score_int = int(score)
            comments_int = int(comments)
            time_str = _parse_timestamp(timestamp)

            # Build the post line
            line = f"{rank_num}. **{title}**"
            if domain:
                line += f" ({domain})"
            lines.append(line)

            details = []
            details.append(f"Score: {score_int}")
            details.append(f"Comments: {comments_int}")
            details.append(f"by {author}")
            if time_str:
                details.append(time_str)
            lines.append(f"   {' | '.join(details)}")

            post_url = data_url.replace("&amp;", "&")
            lines.append(f"   {post_url}")
            lines.append("")

        # Next page link
        next_match = _NEXT_RE.search(html)
        if next_match:
            next_url = next_match.group(1).replace("&amp;", "&")
            lines.append(f"---\n[Next page]({next_url})")

        return StrategyResult(
            content="\n".join(lines).strip(),
            format="markdown",
        )
