#!/usr/bin/env python3
"""
fetch_nber.py — NBER Working Papers RSS 抓取器
参考 social-science-claude-scholar 的 NBER 集成模式

用法:
  python3 fetch_nber.py --programs AP,CF,EF,ME --output /tmp/nber_raw.json
"""

import argparse
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

NBER_RSS_URL = "https://www.nber.org/rss/new.xml"
NAMESPACES = {"content": "http://purl.org/rss/1.0/modules/content/"}

# Program filter keywords (title + description matching)
PROGRAM_KEYWORDS = {
    "AP": ["stock", "equity", "return", "factor", "portfolio", "cross-section",
           "asset pricing", "risk premium", "anomaly", "predictability"],
    "CF": ["payout", "dividend", "repurchase", "investment", "capital structure",
           "equity", "shareholder", "corporate", "earnings"],
    "EF": ["stock market", "equity premium", "financial market", "asset price",
           "volatility", "bubble", "crisis"],
    "ME": ["stock", "equity", "financial market", "asset price", "bank lending",
           "credit channel"],
}

# Exclusion keywords (regardless of program match)
EXCLUDE_KEYWORDS = [
    "option pricing", "cryptocurrency", "bitcoin", "DSGE",
    "monetary policy", "Taylor rule", "sovereign debt", "Basel",
]


def fetch_rss(url: str, timeout: int = 30) -> bytes:
    """Fetch RSS feed with retry"""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ExploreScholar/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def parse_nber_rss(xml_data: bytes, programs: list[str]) -> list[dict]:
    """Parse NBER RSS XML → filtered paper list"""
    root = ET.fromstring(xml_data)
    papers = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)  # NBER weekly, use 30d window

    channel = root.find("channel")
    if channel is None:
        return papers

    for item in channel.findall("item"):
        title_el = item.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""

        link_el = item.find("link")
        link = link_el.text.strip() if link_el is not None and link_el.text else ""

        desc_el = item.find("description")
        description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        pubdate_el = item.find("pubDate")
        pub_date_str = pubdate_el.text if pubdate_el is not None else ""

        # Parse pubDate
        try:
            pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
        except (ValueError, TypeError):
            pub_date = datetime.now(timezone.utc)

        if pub_date < cutoff_date:
            continue

        # Extract NBER program tags from description or category
        paper_programs = []
        for prog in programs:
            if prog in description or f"Program: {prog}" in description:
                paper_programs.append(prog)

        # If no explicit program tag, check keywords
        if not paper_programs:
            for prog in programs:
                kw_list = PROGRAM_KEYWORDS.get(prog, [])
                if any(kw.lower() in (title + " " + description).lower() for kw in kw_list):
                    paper_programs.append(prog)

        if not paper_programs:
            continue

        # Exclusion check
        text = (title + " " + description).lower()
        if any(exc.lower() in text for exc in EXCLUDE_KEYWORDS):
            continue

        # Extract authors from description (typical format: "Author1, Author2 and Author3")
        authors = []
        # Simple heuristic: text before first "(" or "NBER Working Paper"
        author_part = description.split("(")[0].strip() if "(" in description else description.split("NBER")[0].strip()
        if author_part and len(author_part) < 200:
            # Split by " and " or ", "
            for part in author_part.replace(" and ", ", ").split(", "):
                name = part.strip()
                if name and len(name) > 3 and not name.startswith("http"):
                    authors.append(name)

        paper_id = f"nber:{link.split('/')[-1]}" if link else f"nber:{hash(title)}"

        papers.append({
            "paper_id": paper_id,
            "title": title,
            "authors": authors if authors else ["Unknown"],
            "year": pub_date.year,
            "source": "nber",
            "source_category": ",".join(paper_programs),
            "abstract": description[:2000] if description else "",
            "url": link,
            "doi": "",
            "language": "en",
            "published": pub_date.isoformat(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })

    return papers


def main():
    parser = argparse.ArgumentParser(description="NBER Working Papers RSS fetcher")
    parser.add_argument("--programs", default="AP,CF,EF,ME", help="NBER programs to filter (comma-separated)")
    parser.add_argument("--output", default="/tmp/nber_raw.json", help="Output JSON path")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout seconds")
    args = parser.parse_args()

    programs = [p.strip() for p in args.programs.split(",") if p.strip()]
    print(f"Fetching NBER RSS (programs: {programs})...", file=sys.stderr)

    try:
        xml_data = fetch_rss(NBER_RSS_URL, timeout=args.timeout)
        papers = parse_nber_rss(xml_data, programs)
        print(f"  NBER: {len(papers)} papers after program filter", file=sys.stderr)
    except Exception as e:
        print(f"  ERROR fetching NBER RSS: {e}", file=sys.stderr)
        papers = []

    with open(args.output, "w") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    print(f"NBER papers: {len(papers)} → {args.output}", file=sys.stderr)
    print(json.dumps({"status": "ok", "count": len(papers), "output": args.output}))


if __name__ == "__main__":
    main()
