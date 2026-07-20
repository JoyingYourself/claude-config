#!/usr/bin/env python3
"""
merge_dedup.py — 四源论文去重合并引擎
复用自 scholar-megasearch/skills/scholar-megasearch/scripts/merge_corpus.py

三级去重策略:
  1. DOI 精确匹配（最高精度）
  2. 标题相似度 > 0.90（Levenshtein 比率）
  3. arXiv ID 匹配（跨源重复检测）

用法:
  python3 merge_dedup.py \
    --inputs /tmp/arxiv_raw.json,/tmp/nber_raw.json,/tmp/ssrn_raw.json,/tmp/journals_raw.json \
    --output /tmp/all_papers.json
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone


def normalize_title(title: str) -> str:
    """Normalize title for comparison"""
    t = title.lower()
    t = re.sub(r'[^a-z0-9\s]', '', t)  # Remove special chars
    t = re.sub(r'\s+', ' ', t).strip()  # Normalize whitespace
    return t


def levenshtein_ratio(s1: str, s2: str) -> float:
    """Compute Levenshtein ratio (0.0 to 1.0) between two strings"""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    # Use simple 2-row DP for memory efficiency
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    distance = prev_row[-1]
    max_len = max(len(s1), len(s2))
    return 1.0 - (distance / max_len)


def extract_arxiv_id(paper: dict) -> str | None:
    """Extract arXiv ID from paper record (any source)"""
    paper_id = paper.get("paper_id", "")
    if paper_id.startswith("arxiv:"):
        return paper_id.replace("arxiv:", "")

    # Check URL for arXiv reference
    url = paper.get("url", "")
    for pattern in [r'arxiv\.org/abs/([\d.]+v?\d*)', r'arxiv\.org/pdf/([\d.]+v?\d*)']:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Check abstract for arXiv ID
    abstract = paper.get("abstract", "")
    match = re.search(r'arxiv:(\d{4}\.\d{4,5})', abstract, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def dedup_papers(all_papers: list[dict], title_threshold: float = 0.90) -> list[dict]:
    """Deduplicate papers using three-level strategy"""
    if not all_papers:
        return []

    # Precompute normalized data
    for p in all_papers:
        p["_norm_title"] = normalize_title(p.get("title", ""))
        p["_arxiv_id"] = extract_arxiv_id(p)
        p["_doi"] = (p.get("doi") or "").lower().strip()

    # Sort: prefer papers with abstracts, then by source priority
    source_priority = {"arxiv": 1, "ssrn": 2, "nber": 3, "journal": 4}
    all_papers.sort(key=lambda p: (
        source_priority.get(p.get("source", ""), 5),
        -(len(p.get("abstract", ""))),
        -(len(p.get("authors", []))),
    ))

    kept = []
    seen_dois = set()
    seen_arxiv_ids = set()

    for paper in all_papers:
        is_dup = False

        # Level 1: DOI exact match
        doi = paper["_doi"]
        if doi and doi in seen_dois:
            # Merge: keep the paper with more complete metadata
            for kp in kept:
                if kp["_doi"] == doi:
                    if len(paper.get("abstract", "")) > len(kp.get("abstract", "")):
                        kp["abstract"] = paper["abstract"]
                    if paper.get("authors") and not kp.get("authors"):
                        kp["authors"] = paper["authors"]
                    # Record cross-source
                    alt_sources = kp.setdefault("alt_sources", [])
                    alt_sources.append(paper.get("source", ""))
                    break
            is_dup = True

        # Level 2: arXiv ID match
        arxiv_id = paper["_arxiv_id"]
        if not is_dup and arxiv_id and arxiv_id in seen_arxiv_ids:
            for kp in kept:
                if kp["_arxiv_id"] == arxiv_id:
                    if len(paper.get("abstract", "")) > len(kp.get("abstract", "")):
                        kp["abstract"] = paper["abstract"]
                    alt_sources = kp.setdefault("alt_sources", [])
                    alt_sources.append(paper.get("source", ""))
                    break
            is_dup = True

        # Level 3: Title similarity
        if not is_dup:
            norm_title = paper["_norm_title"]
            if len(norm_title) > 30:  # Only compare meaningful titles
                for kp in kept:
                    kp_title = kp.get("_norm_title", "")
                    if len(kp_title) < 30:
                        continue
                    if levenshtein_ratio(norm_title, kp_title) >= title_threshold:
                        if len(paper.get("abstract", "")) > len(kp.get("abstract", "")):
                            kp["abstract"] = paper["abstract"]
                        alt_sources = kp.setdefault("alt_sources", [])
                        alt_sources.append(paper.get("source", ""))
                        is_dup = True
                        break

        if not is_dup:
            if doi:
                seen_dois.add(doi)
            if arxiv_id:
                seen_arxiv_ids.add(arxiv_id)
            kept.append(paper)

    # Clean up internal fields
    for p in kept:
        p.pop("_norm_title", None)
        p.pop("_arxiv_id", None)
        p.pop("_doi", None)

    return kept


def main():
    parser = argparse.ArgumentParser(description="Merge and deduplicate papers from multiple sources")
    parser.add_argument("--inputs", required=True, help="Comma-separated input JSON files")
    parser.add_argument("--output", default="/tmp/all_papers.json", help="Output JSON path")
    parser.add_argument("--threshold", type=float, default=0.90, help="Title similarity threshold")
    args = parser.parse_args()

    input_files = [f.strip() for f in args.inputs.split(",") if f.strip()]
    all_papers = []
    source_counts = {}

    for filepath in input_files:
        try:
            with open(filepath) as f:
                papers = json.load(f)
            if isinstance(papers, list):
                source = papers[0].get("source", "unknown") if papers else "unknown"
                source_counts[source] = len(papers)
                all_papers.extend(papers)
                print(f"  Loaded {len(papers)} from {filepath} (source: {source})", file=sys.stderr)
            else:
                print(f"  SKIP {filepath}: not a JSON array", file=sys.stderr)
        except FileNotFoundError:
            print(f"  SKIP {filepath}: file not found", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"  SKIP {filepath}: invalid JSON ({e})", file=sys.stderr)

    total_before = len(all_papers)
    print(f"\nTotal before dedup: {total_before}", file=sys.stderr)
    print(f"Source breakdown: {source_counts}", file=sys.stderr)

    # Dedup
    unique_papers = dedup_papers(all_papers, title_threshold=args.threshold)
    total_after = len(unique_papers)
    removed = total_before - total_after

    # Add dedup metadata
    output_data = {
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "total": total_after,
        "total_before_dedup": total_before,
        "removed_duplicates": removed,
        "dedup_rate": round(removed / total_before, 3) if total_before > 0 else 0,
        "source_counts": source_counts,
        "papers": unique_papers,
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nMerge result: {total_before} → {total_after} ({removed} duplicates removed, "
          f"dedup rate: {output_data['dedup_rate']:.1%})", file=sys.stderr)
    print(f"Output: {args.output}", file=sys.stderr)
    print(json.dumps({
        "status": "ok",
        "total_before": total_before,
        "total_after": total_after,
        "removed": removed,
        "output": args.output,
    }))


if __name__ == "__main__":
    main()
