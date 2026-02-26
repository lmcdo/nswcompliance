#!/usr/bin/env python3
"""
DCP Pre-flight Assessment Script
=================================

Objectively assesses a Development Control Plan PDF before ingestion into
the compliance engine. Produces a structured JSON report covering:

  1. PDF type        — native text vs scanned (determines OCR need)
  2. Section pattern — numbering style and extraction regex
  3. Control notation — C/O-numbers, must/shall, notation dominance
  4. Layer structure  — generic / use_specific / condition / precinct (from TOC)
  5. Precincts        — count, names, boundary sourcing effort estimate
  + OCR artifacts, provision count estimate, blockers, flags, next steps

Usage:
  python scripts/dcp_preflight.py <pdf_path> [--lga <name>] [--output <report.json>]
  python scripts/dcp_preflight.py <pdf_path> --json-only > report.json

Output:
  Human-readable summary to stdout  +  optional JSON file
"""

import argparse
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure stdout handles Unicode (box-drawing chars, emoji) on all platforms,
# including Windows terminals that default to cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)


# ── Section pattern registry ──────────────────────────────────────────────────
# (name, regex, human description, example)
# Ordered from most specific to least — first dominant hit wins.

SECTION_PATTERNS = [
    ("numeric_4level",  r"^\d+\.\d+\.\d+\.\d+\s+\S",  "4-level numeric",        "2.6.1.1 Controls"),
    ("numeric_3level",  r"^\d+\.\d+\.\d+\s+\S",        "3-level numeric",        "2.6.1 Privacy Controls"),
    ("numeric_2level",  r"^\d+\.\d+\s+\S",              "2-level numeric",        "2.6 Privacy"),
    ("numeric_1level",  r"^\d+\s+[A-Z]\S",              "1-level numeric",        "2 Generic Provisions"),
    ("alpha_3level",    r"^[A-Z]\d+\.\d+\.\d+\s+\S",   "alpha-prefixed 3-level", "C2.1.1 Objectives"),
    ("alpha_2level",    r"^[A-Z]\d+\.\d+\s+\S",         "alpha-prefixed 2-level", "C2.1 Building Form"),
    ("alpha_code",      r"^[A-Z]\d{1,2}\s+[A-Z]\S",    "letter+number code",     "B1 Waste, C2 Residential"),
    ("part_alpha",      r"^Part\s+[A-Z]\b",             "Part + letter",          "Part C Section 1"),
    ("chapter_alpha",   r"^Chapter\s+[A-Z]\b",          "Chapter + letter",       "Chapter F Development Categories"),
    ("section_numeric", r"^Section\s+\d+\b",            "Section + number",       "Section 3.1 Heritage"),
]

# ── Layer keyword mapping ─────────────────────────────────────────────────────
# Checked against TOC section titles (lowercase). Order matters for classification:
# condition before generic to catch "heritage" before "all development".

LAYER_KEYWORDS: dict[str, list[str]] = {
    "condition": [
        "heritage", "heritage conservation", "heritage item",
        "flood", "flood prone", "flood risk",
        "bushfire", "bush fire",
        "contamination", "contaminated land",
        "acid sulfate", "acid sulphate",
        "biodiversity", "ecological",
        "coastal", "foreshore",
        "mine subsidence", "landslide", "land slip",
    ],
    "precinct": [
        "precinct", "site specific", "site-specific",
        "key site", "strategic site",
        "character area", "local area", "locality",
        "development area", "specific location",
    ],
    "use_specific": [
        "residential flat building", "multi dwelling", "attached dwelling",
        "secondary dwelling", "dual occupancy", "shop top",
        "mixed use", "commercial", "retail", "industrial",
        "childcare", "child care", "education establishment",
        "health services", "place of worship", "tourist",
        "dwelling house", "alterations and additions",
    ],
    "generic": [
        "generic provision", "general provision", "general control",
        "all development", "urban design", "landscaping", "open space",
        "car parking", "bicycle", "amenity", "energy efficiency",
        "water management", "stormwater", "waste", "acoustic", "privacy",
        "setback", "height", "floor space", "fsr", "building form",
        "materials", "fencing", "signage", "advertising",
        "access", "mobility", "subdivision", "earthworks", "drainage",
        "sustainability", "tree", "vegetation",
    ],
}

# ── Control notation patterns ─────────────────────────────────────────────────

CONTROL_PATTERNS: dict[str, re.Pattern] = {
    "c_numbered":    re.compile(r"(?m)^\s*C\d+[\s.]"),
    "o_numbered":    re.compile(r"(?m)^\s*O\d+[\s.]"),
    "p_numbered":    re.compile(r"(?m)^\s*P\d+[\s.]"),
    "must_shall":    re.compile(r"\b(must|shall|is to|are to)\b", re.I),
    "should_may":    re.compile(r"\b(should|may|is encouraged|is recommended)\b", re.I),
    "minimum":       re.compile(r"\b(minimum|maximum|at least|no more than|not exceed)\b", re.I),
    "numeric_value": re.compile(r"\d+\.?\d*\s*(m|metres?|m2|m²|%|storeys?)", re.I),
}

# ── OCR running-header pattern (Marrickville-style) ───────────────────────────

OCR_RUNNING_HEADER = re.compile(
    r"^PART \d+:\s+[^\n]+\n\d+\s*\n(?:\s*[A-Z][^\n]*Development Control Plan[^\n]*\n)?",
    re.MULTILINE,
)
OCR_CONFUSION = re.compile(r"[lI]{5,}|\bI{3,}\b")   # OCR l/I/1 confusion
NON_ASCII_CLUSTER = re.compile(r"[^\x00-\x7F]{4,}")  # garbled non-ASCII runs
MERGED_WORD = re.compile(r"\b\w{30,}\b")              # impossibly long words

# ── TOC line detection ────────────────────────────────────────────────────────

TOC_PAGE_SIGNAL = re.compile(
    r"(table\s+of\s+contents|contents|index)\s*$",
    re.I | re.M,
)
# Single-line format: "Section Title ........ 42" or "Section Title          42"
TOC_ENTRY_RE = re.compile(
    r"^(.{5,80}?)\s*\.{3,}\s*(\d+)\s*$|^(.{5,80}?)\s{4,}(\d+)\s*$",
    re.MULTILINE,
)

# Multi-line format: code on line 1, title on line 2, page on line 3
#   B1\nWaste\n4  (only fires if pdfplumber actually splits them onto separate lines)
MULTILINE_TOC_ENTRY_RE = re.compile(
    r"^([A-Z]\d{1,2}(?:\.\d+)?|Part\s+[A-Z])\s*\n"
    r"([A-Z][^\n]{4,79}?)\s*\n"
    r"[ \t]*(\d+)[ \t]*(?:\n|$)",
    re.MULTILINE,
)

# Inline alpha-code format: "B1 Waste 4" — code + title + page all on one line,
# separated by single spaces (pdfplumber collapses leading/trailing whitespace).
# Requires the line to START with an alpha-code (e.g. B1, A1, C2, B17).
INLINE_TOC_CODE_RE = re.compile(
    r"^([A-Z]\d{1,2}(?:\.\d+)?)\s+(.{3,70}?)\s+(\d+)\s*$",
    re.MULTILINE,
)

# Part header format: "Part B General Provisions" — no page number.
# Captured for layer classification only (tells us B = generic, C = residential, etc.)
PART_HEADER_TOC_RE = re.compile(
    r"^(Part\s+[A-Z])\s+([A-Z][^\n]{3,70}?)\s*$",
    re.MULTILINE,
)

# ── Precinct name extraction ──────────────────────────────────────────────────

# Precinct heading: must look like "Precinct 1: Lewisham North" or "E1 Bondi Junction Centre"
# Requires a proper-noun-style name (starts uppercase, no lowercase run-on sentences)
PRECINCT_HEADER_RE = re.compile(
    r"(?:^|\n)"
    r"(?:[A-Z]\d{1,2}\s+|(?:precinct|site[\s-]specific|key\s+site)\s*\d*\s*[:\-\u2013]\s*)"
    r"([A-Z][A-Za-z ,'\-]{3,60}?)(?:\s*\n|\s{3,}|\Z)",
    re.MULTILINE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Assessment functions
# ─────────────────────────────────────────────────────────────────────────────

def assess_pdf_type(pdf) -> dict:
    """
    Determine whether the PDF is native text, scanned, or mixed.
    Samples from beginning, middle, and end of the document.
    """
    n = len(pdf.pages)
    sample_idx = sorted(set([
        0, 1, 2,
        n // 4, n // 2, 3 * n // 4,
        max(0, n - 3), max(0, n - 2), max(0, n - 1),
    ]))

    char_counts: list[int] = []
    image_heavy: int = 0

    for i in sample_idx:
        if i >= n:
            continue
        page = pdf.pages[i]
        text = page.extract_text() or ""
        chars = len(text.strip())
        char_counts.append(chars)
        images = getattr(page, "images", []) or []
        if len(images) > 0 and chars < 100:
            image_heavy += 1

    sampled = len(char_counts)
    avg_chars = sum(char_counts) / sampled if sampled else 0
    image_ratio = image_heavy / sampled if sampled else 0

    if avg_chars > 200 and image_ratio < 0.2:
        kind = "native"
        confidence = min(1.0, avg_chars / 600)
        note = "Text is selectable — pdfplumber extraction expected to work cleanly."
    elif avg_chars < 60 or image_ratio > 0.6:
        kind = "scanned"
        confidence = max(0.6, image_ratio)
        note = (
            "PDF is image-based — OCR required before ingestion. "
            "pdfplumber will return near-empty text. "
            "Use PyMuPDF + tesseract or similar OCR pipeline."
        )
    else:
        kind = "mixed"
        confidence = 0.6
        note = (
            "PDF has mixed native/scanned pages. "
            "Extraction quality will vary. Inspect mid-document pages manually."
        )

    return {
        "type": kind,
        "confidence": round(confidence, 2),
        "avg_chars_per_sampled_page": round(avg_chars),
        "image_heavy_page_ratio": round(image_ratio, 2),
        "ocr_required": kind in ("scanned", "mixed"),
        "note": note,
    }


def detect_section_pattern(pdf, sample_pages: int = 40) -> dict:
    """
    Test all known section numbering patterns against extracted headings.
    Returns the dominant pattern with confidence and sample headings.
    """
    lines: list[str] = []
    for page in pdf.pages[:min(sample_pages, len(pdf.pages))]:
        text = page.extract_text() or ""
        lines.extend(text.splitlines())

    # Candidate headings: short lines, mixed case, not pure boilerplate
    candidates = [
        ln.strip() for ln in lines
        if 8 < len(ln.strip()) < 130
        and not ln.strip().isupper()
        and not ln.strip().isdigit()
    ]

    hits: dict[str, int] = {}
    samples: dict[str, list[str]] = {}

    for name, regex, _desc, _ex in SECTION_PATTERNS:
        compiled = re.compile(regex)
        matched = [ln for ln in candidates if compiled.match(ln)]
        hits[name] = len(matched)
        samples[name] = matched[:4]

    total = sum(hits.values())
    if total == 0:
        return {
            "detected": None,
            "confidence": 0.0,
            "all_counts": hits,
            "note": "No recognisable section numbering found. Manual inspection required.",
        }

    best = max(hits, key=hits.get)
    best_count = hits[best]
    confidence = best_count / total

    meta = next((p for p in SECTION_PATTERNS if p[0] == best), None)

    return {
        "detected": best,
        "regex": meta[1] if meta else None,
        "description": meta[2] if meta else None,
        "example": meta[3] if meta else None,
        "confidence": round(confidence, 2),
        "hit_count": best_count,
        "sample_headings": samples.get(best, [])[:4],
        "all_counts": {k: v for k, v in sorted(hits.items(), key=lambda x: -x[1]) if v > 0},
        "note": (
            f"High confidence: '{meta[2] if meta else best}' pattern dominates "
            f"({best_count} of {total} headings, {confidence:.0%})."
            if confidence > 0.7
            else f"Low confidence ({confidence:.0%}): multiple patterns present. "
                 "Review sample headings and tune regex if needed."
        ),
    }


def detect_control_notation(pdf, sample_pages: int = 60) -> dict:
    """
    Count control notation styles across a document sample.
    Determines what the actionable classifier will encounter.
    """
    full_text = ""
    for page in pdf.pages[:min(sample_pages, len(pdf.pages))]:
        full_text += (page.extract_text() or "") + "\n"

    counts = {name: len(pat.findall(full_text)) for name, pat in CONTROL_PATTERNS.items()}

    primary = {
        "c_numbered": counts["c_numbered"],
        "o_numbered": counts["o_numbered"],
        "must_shall":  counts["must_shall"],
    }
    dominant = max(primary, key=primary.get) if any(primary.values()) else "none"

    notes = {
        "c_numbered": (
            "C-numbered controls dominant — high actionable classification accuracy expected. "
            "^C\\d+ regex will capture most controls directly."
        ),
        "o_numbered": (
            "O-numbered objectives dominant — check whether these are actionable in this council's context. "
            "Some councils use O-numbers for non-binding guidance only."
        ),
        "must_shall": (
            "must/shall prose dominant — actionable classifier will rely on language detection. "
            "Expected accuracy is high (must/shall are always included)."
        ),
        "none": (
            "No dominant control notation detected. Manual review of provision structure required."
        ),
    }

    return {
        "counts": counts,
        "dominant_notation": dominant,
        "uses_c_numbers": counts["c_numbered"] > 10,
        "uses_o_numbers": counts["o_numbered"] > 5,
        "uses_must_shall": counts["must_shall"] > 20,
        "actionable_estimate": max(
            counts["c_numbered"],
            counts["must_shall"] // 3,
        ),
        "note": notes.get(dominant, ""),
    }


def extract_toc(pdf, max_toc_pages: int = 20) -> list[dict]:
    """
    Extract table of contents entries from early pages.
    Returns list of {title, page_number}.
    """
    entries: list[dict] = []

    # Apply both TOC patterns to all early pages unconditionally.
    # The "TABLE OF CONTENTS" heading may appear AFTER the TOC content starts
    # (e.g. Waverley: TOC content on page 2, heading on page 3), so we don't
    # gate on finding the signal first. The patterns are tight enough to avoid
    # significant false positives on body text.
    for page in pdf.pages[:max_toc_pages]:
        text = page.extract_text() or ""

        # Pass 1: single-line entries ("Section Title ......... 42")
        for m in TOC_ENTRY_RE.finditer(text):
            title = (m.group(1) or m.group(3) or "").strip()
            page_num_str = m.group(2) or m.group(4)
            if title and page_num_str and len(title) > 4:
                entries.append({
                    "title": title,
                    "page_number": int(page_num_str),
                })

        # Pass 2: multi-line entries ("B1\nWaste\n4" — only if pdfplumber preserves newlines)
        for m in MULTILINE_TOC_ENTRY_RE.finditer(text):
            title = m.group(2).strip()
            page_num_str = m.group(3)
            if title and page_num_str and len(title) > 4:
                entries.append({
                    "title": title,
                    "page_number": int(page_num_str),
                })

        # Pass 3: inline alpha-code entries ("B1 Waste 4" — pdfplumber collapses to one line)
        for m in INLINE_TOC_CODE_RE.finditer(text):
            title = m.group(2).strip()
            page_num_str = m.group(3)
            if title and page_num_str and len(title) > 3:
                entries.append({
                    "title": title,
                    "page_number": int(page_num_str),
                })

        # Pass 4: Part headers without page numbers ("Part B General Provisions")
        # These carry the section title used for layer classification even when the
        # TOC row has no page number (common in Waverley-style DCPs).
        for m in PART_HEADER_TOC_RE.finditer(text):
            title = m.group(2).strip()
            if title and len(title) > 3:
                entries.append({
                    "title": title,
                    "page_number": 0,
                })

        if len(entries) > 300:
            break

    # Deduplicate by title
    seen: set[str] = set()
    unique: list[dict] = []
    for e in entries:
        key = e["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


def classify_toc_layers(toc_entries: list[dict]) -> dict:
    """
    Classify each TOC entry into the 4-layer model using keyword matching.
    Condition checked before generic to avoid misclassifying heritage as generic.
    """
    layer_matches: dict[str, list[str]] = defaultdict(list)
    unclassified: list[str] = []

    for entry in toc_entries:
        title_lower = entry["title"].lower()
        matched = False
        for layer in ("condition", "precinct", "use_specific", "generic"):
            if any(kw in title_lower for kw in LAYER_KEYWORDS[layer]):
                layer_matches[layer].append(entry["title"])
                matched = True
                break
        if not matched:
            unclassified.append(entry["title"])

    n_entries = len(toc_entries)
    n_classified = sum(len(v) for v in layer_matches.values())

    if n_entries == 0:
        confidence = "low"
    elif n_classified / n_entries > 0.7:
        confidence = "high"
    elif n_classified / n_entries > 0.4:
        confidence = "medium"
    else:
        confidence = "low"

    result = {}
    for layer in ("generic", "use_specific", "condition", "precinct"):
        titles = layer_matches[layer]
        result[layer] = {
            "detected": len(titles) > 0,
            "section_titles": titles[:12],
            "count": len(titles),
        }

    result["unclassified"] = unclassified[:20]
    result["unclassified_count"] = len(unclassified)
    result["confidence"] = confidence
    result["toc_entries_total"] = n_entries
    result["toc_entries_classified"] = n_classified

    return result


def detect_precincts(pdf, toc_entries: list[dict]) -> dict:
    """
    Detect and count precincts. Extracts names where possible.
    """
    precinct_toc = [
        e for e in toc_entries
        if any(kw in e["title"].lower() for kw in LAYER_KEYWORDS["precinct"])
    ]

    # Scan document body for explicit precinct heading lines
    # Reject matches that look like sentence fragments (contain lowercase runs or digits mid-word)
    _sentence_fragment = re.compile(r"\b[a-z]{4,}\b.*\b[a-z]{4,}\b")
    names: list[str] = []
    for page in pdf.pages[:min(120, len(pdf.pages))]:
        text = page.extract_text() or ""
        for m in PRECINCT_HEADER_RE.finditer(text):
            name = m.group(1).strip().rstrip(".,;:")
            if (name and len(name) > 3
                    and not _sentence_fragment.search(name)
                    and len(name.split()) <= 8         # precinct names are short
                    and not name.isupper()):           # reject ALL-CAPS section headings
                names.append(name)
        if len(names) > 150:
            break

    # Deduplicate names
    seen: set[str] = set()
    unique_names: list[str] = []
    for name in names:
        key = name[:30].lower()
        if key not in seen:
            seen.add(key)
            unique_names.append(name)

    has_precincts = len(precinct_toc) > 0 or len(unique_names) > 0
    count = max(len(precinct_toc), len(unique_names))

    if count == 0:
        effort = "none"
    elif count <= 5:
        effort = "low (~1h)"
    elif count <= 20:
        effort = "medium (~2-4h)"
    else:
        effort = f"high (~{round(count * 0.1 + 1)}h)"

    return {
        "detected": has_precincts,
        "estimated_count": count,
        "precinct_toc_entries": [e["title"] for e in precinct_toc[:20]],
        "precinct_names_sample": unique_names[:25],
        "boundary_sourcing_effort": effort,
        "note": (
            f"~{count} precincts detected. Boundary GeoJSON sourcing will be the primary manual effort."
            if has_precincts
            else "No precinct chapter detected — precinct layer can be skipped."
        ),
    }


def detect_ocr_artifacts(pdf, sample_pages: int = 15) -> dict:
    """
    Check for OCR running-header artifacts even in nominally native PDFs.
    Also detects character confusion and merged words.
    """
    sample_text = ""
    for page in pdf.pages[:min(sample_pages, len(pdf.pages))]:
        sample_text += (page.extract_text() or "") + "\n"

    running_header_count = len(OCR_RUNNING_HEADER.findall(sample_text))
    confusion_count = len(OCR_CONFUSION.findall(sample_text))
    non_ascii_count = len(NON_ASCII_CLUSTER.findall(sample_text))
    merged_count = len(MERGED_WORD.findall(sample_text))

    total = running_header_count + confusion_count + non_ascii_count + merged_count

    return {
        "running_header_count": running_header_count,
        "ocr_confusion_count": confusion_count,
        "non_ascii_cluster_count": non_ascii_count,
        "merged_word_count": merged_count,
        "total_artifacts_in_sample": total,
        "strip_filter_needed": running_header_count > 0,
        "note": (
            "No OCR artifacts detected — clean extraction expected."
            if total == 0
            else (
                f"Running-header OCR artifacts detected ({running_header_count}). "
                "The unconditional strip filter in the API handles these automatically."
            )
            if running_header_count > 0
            else (
                f"{total} potential artifacts detected (confusion/non-ASCII/merged). "
                "Spot-check provision_text quality after extraction."
            )
        ),
    }


def estimate_provision_count(pdf, section_pattern: dict) -> dict:
    """
    Estimate the number of provisions by counting section headers across the full document.
    """
    if not section_pattern.get("detected") or not section_pattern.get("regex"):
        return {
            "estimated_provisions": None,
            "section_headers_found": None,
            "note": "Cannot estimate — no section pattern detected.",
        }

    compiled = re.compile(section_pattern["regex"], re.MULTILINE)
    header_count = 0
    for page in pdf.pages:
        text = page.extract_text() or ""
        header_count += len(compiled.findall(text))

    return {
        "section_headers_found": header_count,
        "estimated_provisions": header_count,
        "note": (
            "Lower-bound estimate (1 provision per section header). "
            "Actual count may be 20-40% higher if sections contain multiple controls."
        ),
    }


def build_recommendations(
    pdf_type: dict,
    section_pattern: dict,
    control_notation: dict,
    layer_structure: dict,
    precincts: dict,
    ocr_artifacts: dict,
) -> dict:
    """
    Synthesise all findings into blockers, flags, and next steps.
    """
    blockers: list[str] = []
    flags: list[str] = []

    # PDF type
    if pdf_type["type"] == "scanned":
        blockers.append(
            "PDF is scanned — pdfplumber returns near-empty text. "
            "OCR pipeline (PyMuPDF + tesseract or AWS Textract) must run before extraction."
        )
    elif pdf_type["type"] == "mixed":
        flags.append(
            f"Mixed native/scanned PDF (image-heavy page ratio: "
            f"{pdf_type['image_heavy_page_ratio']:.0%}). "
            "Extraction quality will vary. Manual spot-check required after extraction."
        )

    # Section pattern
    if not section_pattern.get("detected"):
        blockers.append(
            "No recognisable section numbering detected. "
            "Manual inspection required to identify provision delimiters before extraction can run."
        )
    elif section_pattern["confidence"] < 0.55:
        flags.append(
            f"Low-confidence section pattern ({section_pattern['detected']}, "
            f"{section_pattern['confidence']:.0%}). "
            "Review sample headings — regex may need manual tuning."
        )

    # OCR artifacts
    if ocr_artifacts["strip_filter_needed"]:
        flags.append(
            "Running-header OCR artifacts present. "
            "The API-level strip filter handles these automatically — no action needed."
        )

    # Layer structure
    if layer_structure["confidence"] == "low":
        flags.append(
            "Low confidence on layer structure (sparse TOC). "
            "Manual layer assignment will be needed after extraction."
        )
    if not layer_structure["generic"]["detected"] and layer_structure["toc_entries_total"] > 5:
        flags.append(
            "No generic layer detected in TOC. "
            "Verify that some parts apply to all development types — all provisions may be condition-gated."
        )

    # Precincts
    if precincts["detected"] and precincts["estimated_count"] > 30:
        flags.append(
            f"Large precinct count (~{precincts['estimated_count']}). "
            f"Boundary sourcing is the dominant manual effort ({precincts['boundary_sourcing_effort']})."
        )

    # Control notation
    if control_notation["dominant_notation"] == "none":
        flags.append(
            "No dominant control notation detected. "
            "Actionable classification accuracy may be lower — manual spot-check 50 provisions post-extraction."
        )

    # Estimate total onboarding hours
    base = 2.0
    if pdf_type["type"] == "scanned":
        base += 5.0
    if not section_pattern.get("detected"):
        base += 3.0
    elif section_pattern["confidence"] < 0.55:
        base += 1.5
    if layer_structure["confidence"] == "low":
        base += 1.5
    if precincts["detected"]:
        base += min(precincts["estimated_count"] * 0.12, 10.0)

    extraction_ready = len(blockers) == 0
    regex = section_pattern.get("regex", "TBD")

    next_steps = []
    if blockers:
        next_steps.append("1. Resolve all BLOCKERS listed above before proceeding.")
    else:
        next_steps = [
            f"1. Run extraction:   python scripts/dcp_extract.py --pdf <path> --regex '{regex}' --lga <name>",
            "2. Run enrichment:   python enrichment/pipeline.py --council <name>",
            "3. Spot-check 20 provisions for actionable classification accuracy.",
            "4. Add config files: lib/council-configs/<council>.json  +  lib/lga-configs/<lga>.json",
        ]
        if precincts["detected"]:
            next_steps.append(
                f"5. Source {precincts['estimated_count']} precinct boundary GeoJSON files "
                f"({precincts['boundary_sourcing_effort']})."
            )

    return {
        "extraction_ready": extraction_ready,
        "needs_ocr": pdf_type["ocr_required"],
        "section_regex": regex,
        "estimated_onboarding_hours": round(base, 1),
        "blockers": blockers,
        "flags": flags,
        "next_steps": next_steps,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def run_preflight(pdf_path: str, lga_name: Optional[str] = None) -> dict:
    """
    Run all assessment dimensions and return the complete report dict.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    report: dict = {
        "assessment_date": datetime.now().isoformat(),
        "pdf_path": str(path.resolve()),
        "pdf_filename": path.name,
        "lga_name": lga_name or "not specified",
    }

    def _log(msg: str) -> None:
        print(f"[preflight] {msg}", file=sys.stderr)

    _log(f"Opening {path.name} ...")

    with pdfplumber.open(str(path)) as pdf:
        report["page_count"] = len(pdf.pages)
        _log(f"{len(pdf.pages)} pages")

        _log("1/6  Assessing PDF type ...")
        report["pdf_type"] = assess_pdf_type(pdf)

        _log("2/6  Detecting section numbering pattern ...")
        report["section_pattern"] = detect_section_pattern(pdf)

        _log("3/6  Detecting control notation ...")
        report["control_notation"] = detect_control_notation(pdf)

        _log("4/6  Extracting table of contents ...")
        toc_entries = extract_toc(pdf)
        report["toc_entry_count"] = len(toc_entries)
        report["toc_sample"] = [e["title"] for e in toc_entries[:20]]

        _log("5/6  Classifying layer structure ...")
        report["layer_structure"] = classify_toc_layers(toc_entries)

        _log("6/6  Detecting precincts ...")
        report["precincts"] = detect_precincts(pdf, toc_entries)

        _log("      Checking for OCR artifacts ...")
        report["ocr_artifacts"] = detect_ocr_artifacts(pdf)

        _log("      Estimating provision count ...")
        report["provision_estimate"] = estimate_provision_count(pdf, report["section_pattern"])

        _log("      Building recommendations ...")
        report["recommendations"] = build_recommendations(
            report["pdf_type"],
            report["section_pattern"],
            report["control_notation"],
            report["layer_structure"],
            report["precincts"],
            report["ocr_artifacts"],
        )

    _log("Done.")
    return report


# ─────────────────────────────────────────────────────────────────────────────
# Human-readable summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(report: dict) -> None:
    rec  = report["recommendations"]
    pt   = report["pdf_type"]
    sp   = report["section_pattern"]
    cn   = report["control_notation"]
    ls   = report["layer_structure"]
    pr   = report["precincts"]
    pe   = report["provision_estimate"]
    ocr  = report["ocr_artifacts"]

    W = 65

    def rule(char: str = "-") -> None:
        print(char * W)

    def section(title: str) -> None:
        print(f"\n-- {title} {'-' * (W - len(title) - 4)}")

    print()
    rule("=")
    print(f"  DCP PRE-FLIGHT ASSESSMENT")
    print(f"  {report['pdf_filename']}")
    if report["lga_name"] != "not specified":
        print(f"  LGA: {report['lga_name']}")
    print(f"  {report['assessment_date'][:10]}  |  {report['page_count']} pages")
    rule("=")

    # Verdict
    if rec["extraction_ready"]:
        print(f"\n  ✅  READY TO EXTRACT  (~{rec['estimated_onboarding_hours']}h total estimated)")
    else:
        print(f"\n  ❌  BLOCKERS FOUND  — must resolve before extraction")

    # PDF type
    section("PDF TYPE")
    icons = {"native": "✅", "mixed": "⚠️ ", "scanned": "❌"}
    print(f"  {icons.get(pt['type'], '?')}  {pt['type'].upper()}  "
          f"(confidence {pt['confidence']:.0%}, "
          f"avg {pt['avg_chars_per_sampled_page']} chars/page)")
    print(f"     {pt['note']}")

    # Section pattern
    section("SECTION NUMBERING PATTERN")
    if sp.get("detected"):
        conf_icon = "✅" if sp["confidence"] > 0.7 else "⚠️ "
        print(f"  {conf_icon}  {sp['description']}  (confidence {sp['confidence']:.0%}, {sp['hit_count']} hits)")
        print(f"     Regex: {sp['regex']}")
        for s in sp.get("sample_headings", [])[:3]:
            print(f"     e.g.  {s[:72]}")
    else:
        print("  ❌  Not detected — manual inspection required")

    # Control notation
    section("CONTROL NOTATION")
    c = cn["counts"]
    print(f"  C-numbered controls  : {c['c_numbered']:>5}")
    print(f"  O-numbered objectives: {c['o_numbered']:>5}")
    print(f"  P-numbered criteria  : {c['p_numbered']:>5}")
    print(f"  must / shall         : {c['must_shall']:>5}")
    print(f"  should / may         : {c['should_may']:>5}")
    print(f"  numeric values       : {c['numeric_value']:>5}")
    print(f"  Dominant: {cn['dominant_notation']}")
    print(f"  → {cn['note']}")

    # Layer structure
    section("LAYER STRUCTURE")
    for layer in ("generic", "use_specific", "condition", "precinct"):
        info = ls[layer]
        icon = "✅" if info["detected"] else "○ "
        samples = info["section_titles"][:2]
        suffix = f"  — e.g. {', '.join(samples[:2])}" if samples else ""
        print(f"  {icon}  {layer:<14}  {info['count']} sections{suffix}")
    if ls["unclassified_count"] > 0:
        print(f"  ◌   unclassified      {ls['unclassified_count']} sections "
              f"(review manually)")
    print(f"  Confidence: {ls['confidence'].upper()}  "
          f"({ls['toc_entries_classified']} of {ls['toc_entries_total']} TOC entries classified)")

    # Precincts
    section("PRECINCTS")
    if pr["detected"]:
        print(f"  ⚠️   ~{pr['estimated_count']} precincts  "
              f"(boundary sourcing: {pr['boundary_sourcing_effort']})")
        for name in pr["precinct_names_sample"][:6]:
            print(f"       · {name[:65]}")
        if len(pr["precinct_names_sample"]) > 6:
            print(f"       · ... and {len(pr['precinct_names_sample']) - 6} more")
    else:
        print("  ✅  No precinct chapter — precinct layer can be skipped")

    # OCR artifacts
    section("OCR ARTIFACTS")
    if ocr["total_artifacts_in_sample"] == 0:
        print(f"  ✅  None detected in {15}-page sample")
    else:
        print(f"  ⚠️   {ocr['total_artifacts_in_sample']} artifacts in sample")
        print(f"       running headers: {ocr['running_header_count']}, "
              f"confusion: {ocr['ocr_confusion_count']}, "
              f"non-ASCII: {ocr['non_ascii_cluster_count']}")
    print(f"  → {ocr['note']}")

    # Provision estimate
    if pe.get("estimated_provisions"):
        section("PROVISION ESTIMATE")
        print(f"  ~{pe['estimated_provisions']} provisions  "
              f"({pe['section_headers_found']} section headers found, lower bound)")

    # Flags
    if rec["flags"]:
        section("FLAGS")
        for flag in rec["flags"]:
            print(f"  ⚠️   {flag}")

    # Blockers
    if rec["blockers"]:
        section("BLOCKERS")
        for blocker in rec["blockers"]:
            print(f"  ❌  {blocker}")

    # Next steps
    section("NEXT STEPS")
    for step in rec["next_steps"]:
        print(f"  {step}")

    print()
    rule("=")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "DCP Pre-flight Assessment — run before ingesting a new DCP into the compliance engine. "
            "Outputs a human-readable summary and optional JSON report."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/dcp_preflight.py council_dcp_2024.pdf
  python scripts/dcp_preflight.py council_dcp_2024.pdf --lga "Canterbury-Bankstown"
  python scripts/dcp_preflight.py council_dcp_2024.pdf --output report.json
  python scripts/dcp_preflight.py council_dcp_2024.pdf --json-only > report.json
        """,
    )
    parser.add_argument("pdf", help="Path to the DCP PDF file")
    parser.add_argument("--lga",  default=None, help="LGA name (e.g. 'Parramatta')")
    parser.add_argument("--output", default=None, metavar="FILE",
                        help="Write JSON report to this file (in addition to stdout summary)")
    parser.add_argument("--json-only", action="store_true",
                        help="Print JSON to stdout only, suppress human summary")
    args = parser.parse_args()

    try:
        report = run_preflight(args.pdf, lga_name=args.lga)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR during assessment: {e}", file=sys.stderr)
        raise

    if not args.json_only:
        print_summary(report)

    json_str = json.dumps(report, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(json_str, encoding="utf-8")
        print(f"[preflight] JSON report saved → {args.output}", file=sys.stderr)

    if args.json_only:
        print(json_str)


if __name__ == "__main__":
    main()
