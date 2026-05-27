#!/usr/bin/env python3
"""
Idea Validator — Kill-check-first evaluation for business ideas.

Runs 5 kill checks BEFORE scoring to avoid the pattern of getting excited
about demand signals, building, then discovering blockers (QuoteIQ, Goldie May).

Kill checks (run first, any KILL = stop):
  1. Competitor depth — AI-native competitor with >10K users?
  2. Data access — can you legally get the data the product needs?
  3. Incumbent AI roadmap — are big players already building this?
  4. Cold start — does it deliver value on Day 1 with zero users?
  5. Support model fit — does the customer self-serve?

Usage:
  python scripts/idea_validator.py "AI pricebook for solo plumbers"
  python scripts/idea_validator.py "AI genealogy research" --ke-data keywords.csv
  python scripts/idea_validator.py "AI genealogy research" --depth deep
  python scripts/idea_validator.py "AI genealogy research" --context notes.txt

Requires: ANTHROPIC_API_KEY in env or .env
Optional: BRAVE_API_KEY for live web search (free tier: 2000 req/month)
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


# ── Search ────────────────────────────────────────────────────────────


def brave_search(query: str, count: int = 10) -> list[dict]:
    """Search via Brave Search API. Free tier: 1 req/sec, 2000/month."""
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return []
    try:
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            params={"q": query, "count": count},
            timeout=10,
        )
        r.raise_for_status()
        results = r.json().get("web", {}).get("results", [])
        return [
            {"title": x.get("title", ""), "url": x.get("url", ""),
             "snippet": x.get("description", "")}
            for x in results
        ]
    except Exception as e:
        print(f"  [warn] search failed for '{query[:40]}': {e}")
        return []


def run_searches(queries: list[str], depth: str = "standard") -> dict:
    """Run all search queries. Returns {query: [results]}."""
    has_brave = bool(os.getenv("BRAVE_API_KEY"))
    if not has_brave:
        print("     No BRAVE_API_KEY — using Claude's training knowledge only")
        return {}

    max_results = {"quick": 5, "standard": 10, "deep": 20}.get(depth, 10)
    all_results = {}
    for i, q in enumerate(queries):
        print(f"     [{i+1}/{len(queries)}] {q[:60]}")
        all_results[q] = brave_search(q, count=max_results)
        time.sleep(1.1)  # rate limit
    return all_results


# ── KE Data ───────────────────────────────────────────────────────────


def parse_ke_data(filepath: str) -> dict:
    """Parse Keywords Everywhere CSV export."""
    keywords = []
    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kw = row.get("Keyword") or row.get("keyword") or ""
                vol = row.get("Vol") or row.get("Search Volume") or row.get("vol") or "0"
                cpc = row.get("CPC") or row.get("cpc") or "0"
                comp = row.get("Competition") or row.get("competition") or "0"
                # KE sometimes formats vol as "1,300"
                vol_clean = str(vol).replace(",", "").strip()
                cpc_clean = str(cpc).replace("$", "").replace(",", "").strip()
                comp_clean = str(comp).replace(",", "").strip()
                keywords.append({
                    "keyword": kw.strip(),
                    "volume": int(float(vol_clean)) if vol_clean else 0,
                    "cpc": float(cpc_clean) if cpc_clean else 0.0,
                    "competition": float(comp_clean) if comp_clean else 0.0,
                })
    except Exception as e:
        print(f"  [warn] KE parse error: {e}")
        return {}

    if not keywords:
        return {}

    total_vol = sum(k["volume"] for k in keywords)
    avg_cpc = sum(k["cpc"] for k in keywords) / len(keywords)
    max_cpc = max(k["cpc"] for k in keywords)
    high_intent = [k for k in keywords if k["cpc"] > 2.0]

    return {
        "keyword_count": len(keywords),
        "total_monthly_volume": total_vol,
        "avg_cpc": round(avg_cpc, 2),
        "max_cpc": round(max_cpc, 2),
        "high_intent_keywords": len(high_intent),
        "top_by_volume": sorted(keywords, key=lambda k: k["volume"], reverse=True)[:10],
        "top_by_cpc": sorted(keywords, key=lambda k: k["cpc"], reverse=True)[:5],
    }


# ── Claude Prompts ────────────────────────────────────────────────────


DECOMPOSE_PROMPT = """You are evaluating a business idea for a solo technical founder.
Decompose this idea into searchable components. Be specific and concrete.

Idea: {idea}

{context}

Return ONLY a JSON object (no markdown fences, no explanation) with these fields:
{{
  "target_customer": "who exactly — role, company size, industry, demographics",
  "core_value_prop": "the specific pain this solves and how",
  "data_dependencies": ["every external data source/API this product needs to function — be exhaustive, include obvious ones the idea description omits"],
  "competitor_search_queries": ["8-12 targeted search queries to find existing competitors — include: '[niche] software G2', '[niche] AI tool', specific product names you suspect exist, '[pain point] solution', 'product hunt [niche]', 'Y combinator [niche] startup'"],
  "incumbent_platforms": ["large existing platforms serving this market that might add AI features"],
  "support_model_expectation": "how this customer segment typically gets support — self-serve, email, phone, chat, in-person. cite evidence."
}}"""

ANALYZE_PROMPT = """You are a ruthlessly honest business analyst. Your job is to find kill signals, not encourage. You are the corrective for the optimism bias that scored "AI plumber pricebook" as Tier A with "zero competitors" — when QuoteIQ had 40K users.

## The Idea
{idea}

## Decomposition
{decomposition}

## Web Search Results
{search_results}

## Keywords Everywhere Demand Data
{ke_data}

## Additional Context
{context}

---

Run all 5 kill checks. For each, assign a verdict:

**KILL:** A concrete, verified blocker. Not "it might be hard" — a specific reason this fails. Examples: an AI-native competitor with 40K users doing the same thing; a critical API that's TOS-restricted; the target customer segment has 67% paper adoption.
**CAUTION:** A real risk that could waste months if not investigated before building. Needs a decision gate.
**PASS:** No significant risk. If you're uncertain, say CAUTION.

### Check 1: Competitor Depth
Find every competitor. For each: name, users/traction, AI features, pricing. Is there an AI-native competitor with >10K users doing substantially the same thing? If yes, what's the remaining gap, and is that gap DURABLE or will they close it within 12 months?

### Check 2: Data Access Feasibility
For EACH data dependency from the decomposition: Does the API exist? Is it gated/restricted? What are the TOS rules for commercial use? What does it cost? If the product concept fundamentally requires data it cannot legally access, that's a KILL. Be specific — don't say "API exists" without checking TOS.

### Check 3: Incumbent AI Roadmap
For each incumbent platform: have they announced AI features? Are they hiring ML/AI engineers? Have they presented AI plans at conferences? If 2+ incumbents are actively building AI features that overlap with this idea, the window is closing from above.

### Check 4: Cold Start Problem
Does this product deliver real value on Day 1 with zero users and zero accumulated data? If the core value requires a data flywheel, marketplace network, or community that needs 500+ users to spin up — the Day 1 product is hollow. What does the first user actually experience?

### Check 5: Support Model Fit
Does this target customer self-serve, or do they call/text/email for help? What's their tech adoption level? What % currently use digital tools vs paper/phone? If the support burden requires active handholding incompatible with a solo technical founder working <10 hrs/week, that's a structural mismatch.

---

Return ONLY a JSON object (no markdown fences):
{{
  "checks": [
    {{"name": "competitor_depth", "verdict": "KILL|CAUTION|PASS", "evidence": ["..."], "summary": "one line"}},
    {{"name": "data_access", "verdict": "...", "evidence": ["..."], "summary": "..."}},
    {{"name": "incumbent_ai_roadmap", "verdict": "...", "evidence": ["..."], "summary": "..."}},
    {{"name": "cold_start", "verdict": "...", "evidence": ["..."], "summary": "..."}},
    {{"name": "support_model_fit", "verdict": "...", "evidence": ["..."], "summary": "..."}}
  ],
  "overall_verdict": "KILL|CAUTION|PASS",
  "overall_summary": "2-3 sentences.",
  "scores": {{"demand": 0, "defensibility": 0, "solo_founder_fit": 0, "time_to_first_revenue_weeks": 0, "llm_leverage_depth": 0}},
  "what_could_go_wrong": ["3-5 concrete failure modes"],
  "next_steps": ["ordered gate 0 actions before any code"]
}}

Scores 1-10: demand (evidence of spend), defensibility (moat depth), solo_founder_fit, llm_leverage_depth (1=gimmick, 10=IS the product). time_to_first_revenue_weeks = honest estimate.

RULES: ANY KILL → overall KILL. 2+ CAUTION → overall CAUTION. Don't soften KILLs. Scores filled even on KILL for comparison.
"""


# ── Claude Calls ──────────────────────────────────────────────────────


def _extract_json(text: str) -> dict:
    """Extract JSON from Claude response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text)


def decompose_idea(client: "anthropic.Anthropic", idea: str, context: str) -> dict:
    """Break idea into searchable components."""
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": DECOMPOSE_PROMPT.format(
            idea=idea,
            context=f"Additional context from the user:\n{context}" if context else "",
        )}],
    )
    return _extract_json(resp.content[0].text)


def run_analysis(client: "anthropic.Anthropic", idea: str, decomposition: dict,
                 search_results: dict, ke_data: dict, context: str,
                 depth: str) -> dict:
    """Run 5 kill checks via Claude."""
    model = "claude-opus-4-20250514" if depth == "deep" else "claude-sonnet-4-20250514"

    search_text = json.dumps(search_results, indent=2) if search_results else (
        "No live search results — BRAVE_API_KEY not configured. "
        "Use your training knowledge to identify competitors, but flag "
        "anything you're uncertain about as needing verification."
    )

    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": ANALYZE_PROMPT.format(
            idea=idea,
            decomposition=json.dumps(decomposition, indent=2),
            search_results=search_text,
            ke_data=json.dumps(ke_data, indent=2) if ke_data else "No keyword data supplied.",
            context=context or "None.",
        )}],
    )
    return _extract_json(resp.content[0].text)


# ── Report Formatting ─────────────────────────────────────────────────


def format_report(idea: str, decomposition: dict, analysis: dict,
                  ke_data: dict, search_count: int, depth: str) -> str:
    """Format as markdown."""
    lines = []
    verdict = analysis.get("overall_verdict", "UNKNOWN")
    v_icon = {"KILL": "KILL", "CAUTION": "CAUTION", "PASS": "PASS"}.get(verdict, "?")

    lines.append(f"# Idea Validation: {idea}")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Depth:** {depth} | **Search results:** {search_count}")
    lines.append("")
    lines.append(f"## VERDICT: {v_icon}")
    lines.append(analysis.get("overall_summary", ""))
    lines.append("")

    # Kill checks
    lines.append("## Kill Checks")
    lines.append("")
    for check in analysis.get("checks", []):
        v = check.get("verdict", "?")
        lines.append(f"### {v} — {check['name'].replace('_', ' ').title()}")
        lines.append(check.get("summary", ""))
        for e in check.get("evidence", []):
            lines.append(f"- {e}")
        lines.append("")

    # Scores
    scores = analysis.get("scores", {})
    if scores:
        lines.append("## Scores")
        lines.append("")
        lines.append("| Dimension | Score |")
        lines.append("|-----------|-------|")
        lines.append(f"| Demand | {scores.get('demand', '?')}/10 |")
        lines.append(f"| Defensibility | {scores.get('defensibility', '?')}/10 |")
        lines.append(f"| Solo Founder Fit | {scores.get('solo_founder_fit', '?')}/10 |")
        lines.append(f"| Time to First Revenue | ~{scores.get('time_to_first_revenue_weeks', '?')} weeks |")
        lines.append(f"| LLM Leverage Depth | {scores.get('llm_leverage_depth', '?')}/10 |")
        lines.append("")

    # KE data
    if ke_data:
        lines.append("## Demand Data (Keywords Everywhere)")
        lines.append("")
        lines.append(f"- Keywords: {ke_data.get('keyword_count', 0)}")
        lines.append(f"- Total monthly volume: {ke_data.get('total_monthly_volume', 0):,}")
        lines.append(f"- Avg CPC: ${ke_data.get('avg_cpc', 0):.2f} | Max CPC: ${ke_data.get('max_cpc', 0):.2f}")
        lines.append(f"- High-intent keywords (CPC>$2): {ke_data.get('high_intent_keywords', 0)}")
        lines.append("")
        top = ke_data.get("top_by_volume", [])[:5]
        if top:
            lines.append("**Top by volume:**")
            for k in top:
                lines.append(f"- \"{k['keyword']}\" — {k['volume']:,}/mo, ${k['cpc']:.2f} CPC")
            lines.append("")

    # What could go wrong
    wcgw = analysis.get("what_could_go_wrong", [])
    if wcgw:
        lines.append("## What Could Go Wrong")
        for item in wcgw:
            lines.append(f"- {item}")
        lines.append("")

    # Next steps
    steps = analysis.get("next_steps", [])
    if steps:
        lines.append("## Next Steps")
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    # Decomposition reference
    lines.append("---")
    lines.append("## Decomposition (Reference)")
    lines.append(f"- **Target:** {decomposition.get('target_customer', '?')}")
    lines.append(f"- **Value prop:** {decomposition.get('core_value_prop', '?')}")
    lines.append(f"- **Data deps:** {', '.join(decomposition.get('data_dependencies', []))}")
    lines.append(f"- **Incumbents:** {', '.join(decomposition.get('incumbent_platforms', []))}")
    lines.append(f"- **Support model:** {decomposition.get('support_model_expectation', '?')}")
    lines.append("")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Idea Validator — kill-check-first evaluation",
    )
    parser.add_argument("idea", help="Business idea description (in quotes)")
    parser.add_argument("--ke-data", help="Keywords Everywhere CSV export")
    parser.add_argument("--context", help="Text file with additional context/research")
    parser.add_argument("--depth", choices=["quick", "standard", "deep"],
                        default="standard",
                        help="quick=sonnet+5 results, standard=sonnet+10, deep=opus+20")
    parser.add_argument("--output-dir", help="Output directory",
                        default=os.path.join(_root, "docs", "idea-validations"))
    args = parser.parse_args()

    if anthropic is None:
        print("ERROR: pip install anthropic")
        sys.exit(1)
    if requests is None:
        print("ERROR: pip install requests")
        sys.exit(1)
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set (check .env)")
        sys.exit(1)

    client = anthropic.Anthropic()
    os.makedirs(args.output_dir, exist_ok=True)

    context = ""
    if args.context:
        context = Path(args.context).read_text(encoding="utf-8")

    print("=== Idea Validator ===")
    print(f"  Idea:   {args.idea}")
    print(f"  Depth:  {args.depth}")
    print(f"  KE:     {args.ke_data or 'none'}")
    print(f"  Search: {'Brave' if os.getenv('BRAVE_API_KEY') else 'Claude knowledge only'}")
    print()

    # 1. Decompose
    print("[1/4] Decomposing idea...")
    decomposition = decompose_idea(client, args.idea, context)
    print(f"  Target: {decomposition.get('target_customer', '?')[:80]}")
    print(f"  Data deps: {len(decomposition.get('data_dependencies', []))}")
    queries = decomposition.get("competitor_search_queries", [])
    print(f"  Queries: {len(queries)}")
    print()

    # 2. Search
    print(f"[2/4] Searching ({len(queries)} queries)...")
    search_results = run_searches(queries, args.depth)
    search_count = sum(len(v) for v in search_results.values())
    print(f"  {search_count} results")
    print()

    # 3. KE data
    ke_data = {}
    if args.ke_data:
        print(f"[3/4] Parsing KE data...")
        ke_data = parse_ke_data(args.ke_data)
        print(f"  {ke_data.get('keyword_count', 0)} keywords, "
              f"{ke_data.get('total_monthly_volume', 0):,} vol/mo, "
              f"${ke_data.get('avg_cpc', 0):.2f} avg CPC")
    else:
        print("[3/4] No KE data (use --ke-data to add)")
    print()

    # 4. Analyze
    model_label = "opus" if args.depth == "deep" else "sonnet"
    print(f"[4/4] Running kill checks ({model_label})...")
    analysis = run_analysis(
        client, args.idea, decomposition, search_results,
        ke_data, context, args.depth,
    )
    print()

    # Generate report
    report = format_report(
        args.idea, decomposition, analysis, ke_data, search_count, args.depth,
    )

    # Save
    slug = re.sub(r"[^a-z0-9-]", "", args.idea.lower()[:50].replace(" ", "-"))
    date_str = datetime.now().strftime("%Y-%m-%d")
    md_path = os.path.join(args.output_dir, f"{date_str}-{slug}.md")
    json_path = os.path.join(args.output_dir, f"{date_str}-{slug}.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "idea": args.idea,
            "timestamp": datetime.now().isoformat(),
            "depth": args.depth,
            "decomposition": decomposition,
            "search_results_count": search_count,
            "ke_data": ke_data,
            "analysis": analysis,
        }, f, indent=2)

    # Print summary
    print("=== Results ===")
    print()
    verdict = analysis.get("overall_verdict", "UNKNOWN")
    print(f"  VERDICT: {verdict}")
    print(f"  {analysis.get('overall_summary', '')}")
    print()

    for check in analysis.get("checks", []):
        v = check.get("verdict", "?")
        print(f"  [{v:7s}] {check['name'].replace('_', ' ').title()}")
        print(f"           {check.get('summary', '')}")
    print()

    scores = analysis.get("scores", {})
    if scores:
        print(f"  Scores: demand={scores.get('demand','?')}/10  "
              f"defense={scores.get('defensibility','?')}/10  "
              f"fit={scores.get('solo_founder_fit','?')}/10  "
              f"LLM={scores.get('llm_leverage_depth','?')}/10  "
              f"rev=~{scores.get('time_to_first_revenue_weeks','?')}wk")
    print()
    print(f"  Report: {md_path}")
    print(f"  Data:   {json_path}")


if __name__ == "__main__":
    main()
