"""Reddit listing page extraction strategy.

Parses old.reddit.com listing HTML (subreddit feeds, search results) into
structured markdown with post titles, scores, comment counts, authors,
and URLs.  Individual post pages are handled by the default readability
extractor and don't reach this strategy.

The parser works on the old.reddit.com desktop HTML structure:
  <div class="entry unvoted">
    <div class="top-matter">
      <p class="title"><a class="title may-blank" href="...">Title</a> ...</p>
      <p class="tagline">submitted <time ...>...</time> by <a class="author">...</a></p>
      <ul class="flat-list buttons">
        <li class="first"><a class="comments may-blank">N comments</a></li>
      </ul>
    </div>
  </div>

Score comes from the preceding <div class="score likes" title="N"> div.
"""

from __future__ import annotations

import contextlib
import logging
import re

from serp_llm.post_processing.strategies import StrategyResult

logger = logging.getLogger(__name__)

# Match one post row: score div followed by entry div
_POST_RE = re.compile(
    r'<div\s+class="score\s+likes"\s+title="(\d+)"[^>]*>.*?</div>\s*'
    r'</div>\s*'
    r'<div\s+class="entry\s+unvoted">.*?'
    r'<p\s+class="title">'
    r'<a\s+class="title\s+may-blank[^"]*"\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    r'\s*<span\s+class="domain">\(<a[^>]*>([^<]*)</a>\)</span>.*?'
    r'<p\s+class="tagline[^"]*">.*?'
    r'submitted\s*(?:<time[^>]*>[^<]*</time>\s*)?'
    r'by\s*<a[^>]*class="author[^"]*"[^>]*>([^<]+)</a>.*?'
    r'<a[^>]*class="comments\s+may-blank[^"]*"[^>]*>([^<]*)</a>',
    re.DOTALL,
)

# Subreddit name
_SUBREDDIT_RE = re.compile(
    r'data-subreddit-prefixed="([^"]+)"',
)

# Next page link
_NEXT_RE = re.compile(
    r'<span\s+class="next-button">.*?<a\s+href="([^"]+)"',
    re.DOTALL,
)


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
        (no post rows found), letting the next strategy in the priority
        chain handle it.
        """
        matches = list(_POST_RE.finditer(html))
        if not matches:
            return None

        sr_match = _SUBREDDIT_RE.search(html)
        subreddit = sr_match.group(1) if sr_match else "r/reddit"
        lines: list[str] = []
        lines.append(f"## {subreddit}")
        lines.append("")

        for i, m in enumerate(matches):
            score, href, raw_title, domain, author, comments_text = m.groups()
            title = _clean_title(raw_title)
            score_int = int(score)

            # Parse comment count from text like "103 comments" or "comment"
            comments_count = 0
            comments_text = comments_text.strip().lower()
            if comments_text and comments_text != "comment":
                with contextlib.suppress(ValueError, IndexError):
                    comments_count = int(comments_text.split()[0])

            post_url = href if href.startswith("http") else "https://old.reddit.com" + href

            line = f"{i + 1}. **{title}**"
            if domain:
                line += f" ({domain})"
            lines.append(line)

            details = [f"Score: {score_int}"]
            if comments_count:
                details.append(f"Comments: {comments_count}")
            details.append(f"by {author}")
            lines.append(f"   {' | '.join(details)}")
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
