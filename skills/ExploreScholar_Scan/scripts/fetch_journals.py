#!/usr/bin/env python3
"""
fetch_journals.py — 金融期刊 TOC 抓取器
抓取 JF / JFE / RFS / JFQA / JPM 最新目录页

用法:
  python3 fetch_journals.py --journals JF,JFE,RFS,JFQA,JPM --output /tmp/journals_raw.json
"""

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

# Journal TOC URLs (configured for current issue detection)
JOURNALS = {
    "JF": {
        "name": "Journal of Finance",
        "toc_url": "https://onlinelibrary.wiley.com/toc/15406261/current",
        "publisher": "Wiley",
    },
    "JFE": {
        "name": "Journal of Financial Economics",
        "toc_url": "https://www.sciencedirect.com/journal/journal-of-financial-economics",
        "publisher": "Elsevier",
    },
    "RFS": {
        "name": "Review of Financial Studies",
        "toc_url": "https://academic.oup.com/rfs/issue",
        "publisher": "Oxford",
    },
    "JFQA": {
        "name": "Journal of Financial and Quantitative Analysis",
        "toc_url": "https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/latest-issue",
        "publisher": "Cambridge",
    },
    "JPM": {
        "name": "Journal of Portfolio Management",
        "toc_url": "https://jpm.pm-research.com/content/current",
        "publisher": "PM Research",
    },
}

TOPIC_KEYWORDS = [
    "stock return", "equity factor", "portfolio", "asset pricing",
    "cross-section", "return predictability", "anomaly", "alpha",
    "factor model", "quantitative", "trading strategy", "A-share",
    "Chinese stock", "stock selection", "momentum", "value investing",
    "profitability", "accruals", "investment", "machine learning",
]

EXCLUDE_KEYWORDS = [
    "option pricing", "derivatives", "cryptocurrency", "bitcoin",
    "fixed income", "bond", "credit default swap", "sovereign debt",
    "DSGE", "monetary policy", "Basel", "REIT", "venture capital",
    "market making", "order book", "IPO",
]


def fetch_html(url: str, timeout: int = 60) -> str:
    """Fetch HTML page with retry"""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(3 ** attempt)
    return ""


def extract_papers_from_html(html: str, journal_key: str) -> list[dict]:
    """Extract paper titles and links from journal TOC HTML

    This is a heuristic-based extractor. Each publisher uses different HTML structures.
    We look for common patterns: <a> tags with paper titles near author text.
    """
    papers = []
    journal_info = JOURNALS.get(journal_key, {})

    # Pattern 1: Look for research article sections
    # Common patterns across publishers:
    # - <h2>/<h3> with class containing "title" or "article-title"
    # - <a> tags with href containing "/doi/" or "/article/"

    # Extract all potential title + link pairs
    title_patterns = [
        r'<a[^>]*href="([^"]*(?:doi|article|abs)[^"]*)"[^>]*>\s*<[^>]*>\s*([^<]+)\s*</',
        r'<a[^>]*class="[^"]*title[^"]*"[^>]*href="([^"]*)"[^>]*>([^<]+)</a>',
        r'<h\d[^>]*class="[^"]*title[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>',
    ]

    for pattern in title_patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
            href = match.group(1)
            title = match.group(2).strip()
            title = re.sub(r'<[^>]+>', '', title)  # Strip HTML tags
            title = ' '.join(title.split())  # Normalize whitespace

            if not title or len(title) < 20:
                continue

            # Make absolute URL
            if href.startswith("/"):
                if "wiley.com" in journal_info.get("toc_url", ""):
                    href = "https://onlinelibrary.wiley.com" + href
                elif "oup.com" in journal_info.get("toc_url", ""):
                    href = "https://academic.oup.com" + href
                elif "cambridge.org" in journal_info.get("toc_url", ""):
                    href = "https://www.cambridge.org" + href

            # Relevance filter
            text_lower = title.lower()
            if not any(kw.lower() in text_lower for kw in TOPIC_KEYWORDS):
                continue
            if any(exc.lower() in text_lower for exc in EXCLUDE_KEYWORDS):
                continue

            papers.append({
                "paper_id": f"journal:{journal_key}:{hash(title) & 0x7FFFFFFF:08x}",
                "title": title,
                "authors": [],  # Authors hard to extract from HTML; filled by later dedup/LLM
                "year": datetime.now().year,
                "source": "journal",
                "source_category": journal_key,
                "journal": journal_info.get("name", journal_key),
                "abstract": "",  # May need separate abstract page fetch
                "url": href,
                "doi": "",
                "language": "en",
                "published": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })

    return papers


def main():
    parser = argparse.ArgumentParser(description="Financial journal TOC fetcher")
    parser.add_argument("--journals", default="JF,JFE,RFS,JFQA,JPM",
                        help="Journal keys (comma-separated)")
    parser.add_argument("--output", default="/tmp/journals_raw.json", help="Output JSON path")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout seconds")
    args = parser.parse_args()

    journal_keys = [j.strip() for j in args.journals.split(",") if j.strip()]
    all_papers = []

    for jk in journal_keys:
        journal_info = JOURNALS.get(jk)
        if not journal_info:
            print(f"  Unknown journal: {jk}", file=sys.stderr)
            continue

        print(f"Fetching {jk} ({journal_info['name']}) TOC...", file=sys.stderr)
        try:
            html = fetch_html(journal_info["toc_url"], timeout=args.timeout)
            papers = extract_papers_from_html(html, jk)
            print(f"  {jk}: {len(papers)} relevant papers", file=sys.stderr)
            all_papers.extend(papers)
        except Exception as e:
            print(f"  ERROR fetching {jk} TOC: {e}", file=sys.stderr)

    # Dedup by title
    seen_titles = set()
    unique_papers = []
    for p in all_papers:
        title_key = p["title"].lower()[:100]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_papers.append(p)

    with open(args.output, "w") as f:
        json.dump(unique_papers, f, ensure_ascii=False, indent=2)

    print(f"Journal papers: {len(unique_papers)} → {args.output}", file=sys.stderr)
    print(json.dumps({"status": "ok", "count": len(unique_papers), "output": args.output}))


if __name__ == "__main__":
    main()
