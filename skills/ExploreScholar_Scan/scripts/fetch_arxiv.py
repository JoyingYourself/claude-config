#!/usr/bin/env python3
"""
fetch_arxiv.py — arXiv API 论文抓取器
复用自 introduction-to-quantitative-finance/scripts/arxiv_crawler.py
改：q-fin 类别 + cs.LG/stat.ML/stat.AP 关键词过滤

用法:
  python3 fetch_arxiv.py --cats q-fin.PM,q-fin.ST --days 7 --max 200 --output /tmp/arxiv_raw.json
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# ── arXiv API 配置 ──
ARXIV_API_BASE = "http://export.arxiv.org/api/query"
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# 跨类别关键词（cs.LG/stat.ML/stat.AP 需要额外关键词过滤）
CROSS_CATEGORY_KEYWORDS = [
    "stock return", "equity factor", "portfolio", "trading signal",
    "cross-section", "A-share", "Chinese stock", "asset pricing",
    "return predictability", "quantitative investment",
]

# ── 工具函数 ──


def build_query(categories: list[str], max_results: int, days: int) -> str:
    """构建 arXiv API 查询 URL"""
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    params = {
        "search_query": cat_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    return f"{ARXIV_API_BASE}?{urllib.parse.urlencode(params)}"


def fetch_with_retry(url: str, max_retries: int = 3, timeout: int = 30) -> bytes:
    """带重试的 HTTP GET"""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ExploreScholar/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f"  Retry {attempt + 1}/{max_retries} after {wait}s: {e}", file=sys.stderr)
            time.sleep(wait)


def parse_atom(xml_data: bytes) -> list[dict]:
    """解析 arXiv Atom XML → 论文列表"""
    root = ET.fromstring(xml_data)
    papers = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

    for entry in root.findall("atom:entry", NAMESPACES):
        title_el = entry.find("atom:title", NAMESPACES)
        title = " ".join(title_el.text.split()) if title_el is not None and title_el.text else ""

        summary_el = entry.find("atom:summary", NAMESPACES)
        abstract = " ".join(summary_el.text.split()) if summary_el is not None and summary_el.text else ""

        published_el = entry.find("atom:published", NAMESPACES)
        published = published_el.text if published_el is not None else ""

        # Parse date
        try:
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pub_date = datetime.now(timezone.utc)

        # Filter by date
        if pub_date < cutoff_date:
            continue

        # Extract arXiv ID from the <id> tag
        id_el = entry.find("atom:id", NAMESPACES)
        raw_id = id_el.text if id_el is not None else ""
        arxiv_id = raw_id.replace("http://arxiv.org/abs/", "").strip()

        # Extract authors
        authors = []
        for author_el in entry.findall("atom:author", NAMESPACES):
            name_el = author_el.find("atom:name", NAMESPACES)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        # Extract categories
        categories = []
        for cat_el in entry.findall("atom:category", NAMESPACES):
            term = cat_el.get("term", "")
            if term:
                categories.append(term)

        # Extract links
        links = []
        for link_el in entry.findall("atom:link", NAMESPACES):
            href = link_el.get("href", "")
            rel = link_el.get("rel", "alternate")
            title = link_el.get("title", "")
            if href:
                links.append({"rel": rel, "href": href, "title": title})

        paper = {
            "paper_id": f"arxiv:{arxiv_id}",
            "title": title,
            "authors": authors,
            "year": pub_date.year,
            "source": "arxiv",
            "source_category": categories[0] if categories else "unknown",
            "all_categories": categories,
            "abstract": abstract,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
            "doi": "",
            "language": "en",
            "published": published,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        papers.append(paper)

    return papers


def is_relevant_cross_category(paper: dict) -> bool:
    """检查跨类别论文是否与量化选股相关"""
    text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
    return any(kw.lower() in text for kw in CROSS_CATEGORY_KEYWORDS)


def main():
    parser = argparse.ArgumentParser(description="arXiv API paper fetcher for q-fin + cross categories")
    parser.add_argument("--cats", default="q-fin.PM,q-fin.ST,q-fin.PR,q-fin.RM,q-fin.GN,q-fin.TR,q-fin.MF,q-fin.CP,q-fin.EC",
                        help="arXiv categories (comma-separated)")
    parser.add_argument("--cross-cats", default="cs.LG,stat.ML,stat.AP",
                        help="Cross-discipline categories needing keyword filter")
    parser.add_argument("--days", type=int, default=7, help="Lookback days")
    parser.add_argument("--max", type=int, default=200, dest="max_results", help="Max results per batch")
    parser.add_argument("--output", default="/tmp/arxiv_raw.json", help="Output JSON path")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout seconds")
    args = parser.parse_args()

    categories = [c.strip() for c in args.cats.split(",") if c.strip()]
    cross_cats = [c.strip() for c in args.cross_cats.split(",") if c.strip()]

    all_papers = []

    # Phase 1: Fetch q-fin categories (no keyword filter needed)
    print(f"Fetching arXiv q-fin: {categories}", file=sys.stderr)
    url = build_query(categories, args.max_results, args.days)
    try:
        xml_data = fetch_with_retry(url, timeout=args.timeout)
        papers = parse_atom(xml_data)
        print(f"  q-fin: {len(papers)} papers", file=sys.stderr)
        all_papers.extend(papers)
    except Exception as e:
        print(f"  ERROR fetching q-fin: {e}", file=sys.stderr)

    # Phase 2: Fetch cross-discipline categories (with keyword filter)
    if cross_cats:
        print(f"Fetching cross-discipline: {cross_cats}", file=sys.stderr)
        url = build_query(cross_cats, args.max_results, args.days)
        try:
            xml_data = fetch_with_retry(url, timeout=args.timeout)
            papers = parse_atom(xml_data)
            # Apply keyword filter for cross-category papers
            filtered = [p for p in papers if is_relevant_cross_category(p)]
            print(f"  cross-discipline: {len(papers)} raw → {len(filtered)} after keyword filter", file=sys.stderr)
            all_papers.extend(filtered)
        except Exception as e:
            print(f"  ERROR fetching cross-discipline: {e}", file=sys.stderr)

    # Dedup by arXiv ID within arXiv results
    seen = set()
    unique_papers = []
    for p in all_papers:
        if p["paper_id"] not in seen:
            seen.add(p["paper_id"])
            unique_papers.append(p)

    # Write output
    with open(args.output, "w") as f:
        json.dump(unique_papers, f, ensure_ascii=False, indent=2)

    print(f"\nTotal arXiv papers: {len(unique_papers)} → {args.output}", file=sys.stderr)
    print(json.dumps({"status": "ok", "count": len(unique_papers), "output": args.output}))


if __name__ == "__main__":
    main()
