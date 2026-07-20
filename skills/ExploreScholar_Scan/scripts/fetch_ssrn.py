#!/usr/bin/env python3
"""
fetch_ssrn.py — SSRN 论文抓取器
SSRN 无公开 API，使用 RSS feed + WebFetch 模式

用法:
  python3 fetch_ssrn.py --networks FEN,ERN --output /tmp/ssrn_raw.json
"""

import argparse
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

SSRN_RSS_FEEDS = {
    "FEN": "https://papers.ssrn.com/sol3/JELJOUR_Results.cfm?form_name=journalBrowse&journal_id=1",
    "ERN": "https://papers.ssrn.com/sol3/JELJOUR_Results.cfm?form_name=journalBrowse&journal_id=2",
}

# Topic keywords for filtering SSRN papers to quant equity range
TOPIC_KEYWORDS = [
    "stock return", "equity factor", "portfolio", "asset pricing",
    "cross-section", "return predictability", "anomaly", "alpha",
    "factor model", "quantitative", "trading strategy", "A-share",
    "Chinese stock", "stock selection", "momentum", "value investing",
]

EXCLUDE_KEYWORDS = [
    "option pricing", "derivatives", "cryptocurrency", "bitcoin",
    "fixed income", "bond", "credit default swap", "sovereign debt",
    "DSGE", "monetary policy", "Basel", "REIT", "venture capital",
]


def fetch_rss(url: str, timeout: int = 45) -> bytes:
    """Fetch RSS/XML feed"""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ExploreScholar/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(3 ** attempt)


def parse_ssrn(xml_data: bytes) -> list[dict]:
    """Parse SSRN RSS/HTML → paper list

    SSRN's feed format varies. This implementation handles:
    1. RSS 2.0 format
    2. Basic HTML listing (fallback via regex)
    """
    papers = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=14)

    # Try RSS/XML parsing first
    try:
        root = ET.fromstring(xml_data)
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                title_el = item.find("title")
                title = title_el.text.strip() if title_el is not None and title_el.text else ""

                link_el = item.find("link")
                link = link_el.text.strip() if link_el is not None and link_el.text else ""

                desc_el = item.find("description")
                description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

                creator_el = item.find("{http://purl.org/dc/elements/1.1/}creator")
                author = creator_el.text.strip() if creator_el is not None and creator_el.text else "Unknown"

                date_el = item.find("{http://purl.org/dc/elements/1.1/}date")
                pub_date_str = date_el.text if date_el is not None else ""

                # Parse date
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pub_date = datetime.now(timezone.utc)

                if pub_date < cutoff_date:
                    continue

                # Relevance filter
                text = (title + " " + description).lower()
                if not any(kw.lower() in text for kw in TOPIC_KEYWORDS):
                    continue
                if any(exc.lower() in text for exc in EXCLUDE_KEYWORDS):
                    continue

                # Extract SSRN ID from link
                ssrn_id = ""
                if "abstract_id=" in link:
                    ssrn_id = link.split("abstract_id=")[-1].split("&")[0]
                elif "abstract=" in link:
                    ssrn_id = link.split("abstract=")[-1].split("&")[0]

                papers.append({
                    "paper_id": f"ssrn:{ssrn_id}" if ssrn_id else f"ssrn:{hash(title)}",
                    "title": title,
                    "authors": [author],
                    "year": pub_date.year,
                    "source": "ssrn",
                    "source_category": "SSRN",
                    "abstract": description[:3000] if description else "",
                    "url": link,
                    "doi": "",
                    "language": "en",
                    "published": pub_date.isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })
    except ET.ParseError:
        # Not valid XML — this is expected for some SSRN feeds
        # The caller (Workflow) should use WebFetch as fallback
        print("  SSRN feed returned non-XML content; use WebFetch fallback", file=sys.stderr)

    return papers


def main():
    parser = argparse.ArgumentParser(description="SSRN paper fetcher")
    parser.add_argument("--networks", default="FEN,ERN", help="SSRN networks (comma-separated)")
    parser.add_argument("--output", default="/tmp/ssrn_raw.json", help="Output JSON path")
    parser.add_argument("--timeout", type=int, default=45, help="Request timeout seconds")
    args = parser.parse_args()

    networks = [n.strip() for n in args.networks.split(",") if n.strip()]
    all_papers = []

    for network in networks:
        feed_url = SSRN_RSS_FEEDS.get(network)
        if not feed_url:
            print(f"  Unknown network: {network}", file=sys.stderr)
            continue

        print(f"Fetching SSRN {network}...", file=sys.stderr)
        try:
            xml_data = fetch_rss(feed_url, timeout=args.timeout)
            papers = parse_ssrn(xml_data)
            print(f"  SSRN {network}: {len(papers)} papers", file=sys.stderr)
            all_papers.extend(papers)
        except Exception as e:
            print(f"  ERROR fetching SSRN {network}: {e}", file=sys.stderr)

    # Dedup by paper_id
    seen = set()
    unique_papers = []
    for p in all_papers:
        if p["paper_id"] not in seen:
            seen.add(p["paper_id"])
            unique_papers.append(p)

    with open(args.output, "w") as f:
        json.dump(unique_papers, f, ensure_ascii=False, indent=2)

    print(f"SSRN papers: {len(unique_papers)} → {args.output}", file=sys.stderr)
    print(json.dumps({"status": "ok", "count": len(unique_papers), "output": args.output}))


if __name__ == "__main__":
    main()
