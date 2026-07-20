#!/usr/bin/env python3
"""
classify_papers.py — LLM 三问审核 + 按配额精选 35 篇
此脚本准备分类输入数据；实际 LLM 审核由 Workflow Agent 执行

用法:
  python3 classify_papers.py \
    --input /tmp/keyword_filtered.json \
    --prompt prompts/classify_filter.md \
    --output /tmp/classified_papers.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None


def load_quotas(quotas_path: str) -> dict:
    """Load quota configuration"""
    if yaml is None:
        # Default quotas if PyYAML unavailable
        return {
            "fundamental": {"total": 20, "en": 12, "zh": 8},
            "momentum": {"total": 10, "en": 6, "zh": 4},
            "alternative": {"total": 5, "en": 3, "zh": 2},
        }
    with open(quotas_path) as f:
        return yaml.safe_load(f).get("quotas", {})


def prepare_classification_input(papers: list[dict]) -> list[dict]:
    """Prepare papers for LLM classification

    Returns a list of paper summaries suitable for LLM processing,
    with metadata needed for the three-question audit.
    """
    prepared = []
    for i, paper in enumerate(papers):
        prepared.append({
            "index": i,
            "paper_id": paper.get("paper_id", ""),
            "title": paper.get("title", ""),
            "authors": paper.get("authors", [])[:5],  # First 5 authors
            "year": paper.get("year", 0),
            "source": paper.get("source", ""),
            "abstract": paper.get("abstract", "")[:1500],  # Truncate long abstracts
            "url": paper.get("url", ""),
            "language": paper.get("language", "en"),
        })
    return prepared


def apply_quota_selection(
    classified_papers: list[dict],
    quotas: dict,
) -> dict:
    """Select papers by quota from classified results

    Args:
        classified_papers: Papers with LLM classification results
            Each paper must have: category, language, llm_q1/q2/q3, priority_score
        quotas: Quota configuration

    Returns:
        Selected papers organized by category
    """
    # Filter: only papers with 3 YES answers
    eligible = [
        p for p in classified_papers
        if p.get("llm_q1") == "yes" and p.get("llm_q2") == "yes" and p.get("llm_q3") == "yes"
    ]

    # Group by category
    by_category = {
        "fundamental": [],
        "momentum": [],
        "alternative": [],
    }

    for p in eligible:
        cat = p.get("category", "fundamental")
        if cat not in by_category:
            cat = "fundamental"
        by_category[cat].append(p)

    # Sort each category by priority score (descending)
    for cat in by_category:
        by_category[cat].sort(
            key=lambda p: (
                p.get("novelty_score", 0) * 0.40 +
                p.get("replicability_score", 0) * 0.35 +
                p.get("significance_score", 0) * 0.25
            ),
            reverse=True,
        )

    # Select by quota
    selected = {
        "fundamental": {"en": [], "zh": [], "all": []},
        "momentum": {"en": [], "zh": [], "all": []},
        "alternative": {"en": [], "zh": [], "all": []},
    }

    for cat_key, cat_label in [("fundamental", "fundamental"), ("momentum", "momentum"),
                                 ("alternative", "alternative")]:
        cat_quota = quotas.get(cat_label, {})
        en_quota = cat_quota.get("en", 0)
        zh_quota = cat_quota.get("zh", 0)
        total_quota = cat_quota.get("total", 0)

        papers_en = [p for p in by_category[cat_key] if p.get("language", "en") == "en"]
        papers_zh = [p for p in by_category[cat_key] if p.get("language", "zh") == "zh"]

        selected[cat_key]["en"] = papers_en[:en_quota]
        selected[cat_key]["zh"] = papers_zh[:zh_quota]
        selected[cat_key]["all"] = papers_en[:en_quota] + papers_zh[:zh_quota]

    return selected


def main():
    parser = argparse.ArgumentParser(description="Prepare classification input for LLM three-question audit")
    parser.add_argument("--input", required=True, help="Input JSON (keyword_filtered.json)")
    parser.add_argument("--prompt", default="prompts/classify_filter.md", help="Classification prompt template")
    parser.add_argument("--quotas", default="config/quotas.yaml", help="Quota config YAML")
    parser.add_argument("--output", default="/tmp/classified_papers.json", help="Output JSON path")
    args = parser.parse_args()

    # Load input
    with open(args.input) as f:
        data = json.load(f)

    if isinstance(data, dict) and "papers" in data:
        papers = data["papers"]
    elif isinstance(data, list):
        papers = data
    else:
        print("ERROR: unexpected input format", file=sys.stderr)
        sys.exit(1)

    # Prepare for LLM classification
    prepared = prepare_classification_input(papers)

    # Try to load prompt template
    prompt_text = ""
    try:
        with open(args.prompt) as f:
            prompt_text = f.read()
    except FileNotFoundError:
        print(f"Warning: prompt file {args.prompt} not found, using default", file=sys.stderr)

    # Output prepared data for LLM processing
    output_data = {
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(prepared),
        "prompt_template": prompt_text,
        "quotas": load_quotas(args.quotas) if args.quotas else {},
        "candidates": prepared,
        # These fields are filled by the LLM Agent during Workflow Phase 2:
        "classified_papers": [],    # Agent fills this
        "selected": {},             # Agent fills this after quota selection
        "excluded": [],             # Papers excluded by LLM (with reasons)
        "stats": {},                # Agent fills this
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Classification input prepared: {len(prepared)} candidates → {args.output}", file=sys.stderr)
    print(f"\n⚠️  NOTE: This script only prepares the data. The actual LLM three-question audit")
    print(f"    and quota selection is performed by the Workflow Agent during Phase 2.", file=sys.stderr)
    print(f"    The Agent reads {args.output} and fills classified_papers/selected/excluded.", file=sys.stderr)
    print(json.dumps({"status": "ok", "candidates": len(prepared), "output": args.output}))


if __name__ == "__main__":
    main()
