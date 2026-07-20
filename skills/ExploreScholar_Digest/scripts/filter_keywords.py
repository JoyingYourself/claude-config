#!/usr/bin/env python3
"""
filter_keywords.py — 关键词白名单+黑名单双层过滤
零 token 消耗，纯 Python 关键词匹配

用法:
  python3 filter_keywords.py \
    --input /tmp/all_papers.json \
    --config config/scope_filter.yaml \
    --output /tmp/keyword_filtered.json
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_filter_config(config_path: str) -> dict:
    """Load filter configuration from YAML"""
    with open(config_path) as f:
        return yaml.safe_load(f)


def match_keywords(text: str, keywords: list[str], case_sensitive: bool = False) -> set[str]:
    """Match keywords against text, return set of matched keywords"""
    if not case_sensitive:
        text = text.lower()
    matched = set()
    for kw in keywords:
        search_kw = kw if case_sensitive else kw.lower()
        if search_kw in text:
            matched.add(kw)
    return matched


def filter_papers(papers: list[dict], config: dict) -> tuple[list[dict], list[dict], dict]:
    """Apply whitelist + blacklist filter to papers

    Returns:
        (kept_papers, excluded_papers, stats)
    """
    whitelist = config.get("whitelist_keywords", [])
    blacklist = config.get("blacklist_keywords", [])
    filter_cfg = config.get("filter", {})
    match_fields = filter_cfg.get("match_fields", ["title", "abstract"])
    case_sensitive = filter_cfg.get("case_sensitive", False)
    min_abstract_len = filter_cfg.get("min_abstract_length", 50)

    kept = []
    excluded = []
    stats = {
        "whitelist_only": 0,
        "blacklist_only": 0,
        "both_matched": 0,
        "no_match": 0,
        "short_abstract": 0,
    }

    for paper in papers:
        # Build search text
        search_text = ""
        for field in match_fields:
            val = paper.get(field, "")
            if val:
                search_text += val + " "

        # Skip papers with too-short abstract (likely incomplete)
        abstract = paper.get("abstract", "")
        if abstract and len(abstract) < min_abstract_len:
            stats["short_abstract"] += 1
            excluded.append({**paper, "exclude_reason": "short_abstract"})
            continue

        # Match keywords
        whitelist_hits = match_keywords(search_text, whitelist, case_sensitive)
        blacklist_hits = match_keywords(search_text, blacklist, case_sensitive)

        if whitelist_hits and blacklist_hits:
            # Overlap resolution: whitelist wins (per config)
            stats["both_matched"] += 1
            paper["_whitelist_hits"] = list(whitelist_hits)
            paper["_blacklist_hits"] = list(blacklist_hits)
            paper["_filter_note"] = "whitelist_wins_over_blacklist"
            kept.append(paper)
        elif whitelist_hits:
            stats["whitelist_only"] += 1
            paper["_whitelist_hits"] = list(whitelist_hits)
            kept.append(paper)
        elif blacklist_hits:
            stats["blacklist_only"] += 1
            paper["_blacklist_hits"] = list(blacklist_hits)
            excluded.append({**paper, "exclude_reason": f"blacklist: {list(blacklist_hits)[:3]}"})
        else:
            stats["no_match"] += 1
            excluded.append({**paper, "exclude_reason": "no_whitelist_match"})

    # Clean up internal fields
    for p in kept:
        p.pop("_whitelist_hits", None)
        p.pop("_blacklist_hits", None)
        p.pop("_filter_note", None)

    return kept, excluded, stats


def main():
    parser = argparse.ArgumentParser(description="Keyword-based paper filter (zero token)")
    parser.add_argument("--input", required=True, help="Input JSON (merged_all.json)")
    parser.add_argument("--config", required=True, help="Filter config YAML path")
    parser.add_argument("--output", default="/tmp/keyword_filtered.json", help="Output JSON path")
    args = parser.parse_args()

    # Load input
    with open(args.input) as f:
        data = json.load(f)

    # Handle both raw list and wrapped format (from merge_dedup)
    if isinstance(data, dict) and "papers" in data:
        papers = data["papers"]
        print(f"Loaded {len(papers)} papers from merged output", file=sys.stderr)
    elif isinstance(data, list):
        papers = data
        print(f"Loaded {len(papers)} papers (raw list)", file=sys.stderr)
    else:
        print(f"ERROR: unexpected input format", file=sys.stderr)
        sys.exit(1)

    # Load config
    config = load_filter_config(args.config)
    print(f"Config: {len(config.get('whitelist_keywords', []))} whitelist + "
          f"{len(config.get('blacklist_keywords', []))} blacklist keywords", file=sys.stderr)

    # Filter
    kept, excluded, stats = filter_papers(papers, config)

    # Build output
    output_data = {
        "filtered_at": datetime.now(timezone.utc).isoformat(),
        "total_before": len(papers),
        "total_after": len(kept),
        "total_excluded": len(excluded),
        "filter_rate": round(len(kept) / len(papers), 3) if papers else 0,
        "stats": stats,
        "papers": kept,
        "excluded": excluded,
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nFilter result: {len(papers)} → {len(kept)} kept, {len(excluded)} excluded", file=sys.stderr)
    print(f"  whitelist_only={stats['whitelist_only']}, blacklist_only={stats['blacklist_only']}, "
          f"both={stats['both_matched']}, no_match={stats['no_match']}", file=sys.stderr)
    print(json.dumps({
        "status": "ok",
        "total_before": len(papers),
        "total_after": len(kept),
        "stats": stats,
        "output": args.output,
    }))


if __name__ == "__main__":
    main()
