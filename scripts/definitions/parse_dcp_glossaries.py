#!/usr/bin/env python3
"""
Parse DCP glossaries from Marrickville, Leichhardt, and Ashfield DCPs.

Extracts definitions from the already-extracted markdown files and outputs
structured JSON for database import.

Sources:
- Marrickville DCP 2011 - 10.0 Definitions (prose format: "Term means definition.")
- Leichhardt DCP 2013 - Appendix A Glossary (prose format: "Term means definition.")
- Ashfield DCP 2016 - Chapter G Definitions (HTML table format)
"""

import json
import re
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DEFINITIONS_OUTPUT = PROJECT_ROOT / "scripts" / "definitions" / "extracted"

# DCP source files
DCP_SOURCES = {
    "marrickville": {
        "path": OUTPUT_DIR / "Marrickville DCP 2011 - 10.0 Definitions" / "auto" / "Marrickville DCP 2011 - 10.0 Definitions.md",
        "source_document": "Marrickville DCP 2011",
        "source_clause": "Part 10.0 Definitions",
        "former_council": "Marrickville",
        "lga": "Inner West",
        "format": "prose",
        "pdf_source": OUTPUT_DIR / "Marrickville DCP 2011 - 10.0 Definitions" / "Marrickville DCP 2011 - 10.0 Definitions_origin.pdf",
    },
    "leichhardt": {
        "path": OUTPUT_DIR / "Leichhardt DCP 2013 - 13 - Appendix A Glossary - with IWLEP 2022 amendments" / "auto" / "Leichhardt DCP 2013 - 13 - Appendix A Glossary - with IWLEP 2022 amendments.md",
        "source_document": "Leichhardt DCP 2013",
        "source_clause": "Appendix A Glossary",
        "former_council": "Leichhardt",
        "lga": "Inner West",
        "format": "prose",
        "pdf_source": OUTPUT_DIR / "Leichhardt DCP 2013 - 13 - Appendix A Glossary - with IWLEP 2022 amendments" / "Leichhardt DCP 2013 - 13 - Appendix A Glossary - with IWLEP 2022 amendments_origin.pdf",
    },
    "ashfield": {
        "path": OUTPUT_DIR / "Inner West Ashfield DCP 2016 - Chapter G - Definitions - with IWLEP 2022 amendments" / "auto" / "Inner West Ashfield DCP 2016 - Chapter G - Definitions - with IWLEP 2022 amendments.md",
        "source_document": "Ashfield DCP 2016",
        "source_clause": "Chapter G Definitions",
        "former_council": "Ashfield",
        "lga": "Inner West",
        "format": "html_table",
        "pdf_source": OUTPUT_DIR / "Inner West Ashfield DCP 2016 - Chapter G - Definitions - with IWLEP 2022 amendments" / "Inner West Ashfield DCP 2016 - Chapter G - Definitions - with IWLEP 2022 amendments_origin.pdf",
    },
}


@dataclass
class Definition:
    """Represents a single definition extracted from a DCP."""
    term: str
    term_normalized: str
    definition_text: str
    source_document: str
    source_clause: str
    legislation_type: str
    lga: str
    former_council: str
    pdf_page: Optional[int] = None
    pdf_source_file: Optional[str] = None
    domain_tags: list = None
    extraction_confidence: float = 1.0

    def __post_init__(self):
        if self.domain_tags is None:
            self.domain_tags = []


def normalize_term(term: str) -> str:
    """Normalize a term for matching: lowercase, strip, normalize spaces."""
    normalized = term.lower().strip()
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    # Remove common artifacts
    normalized = normalized.strip('.')
    return normalized


def clean_definition_text(text: str) -> str:
    """Clean up definition text from OCR/extraction artifacts."""
    # Fix LaTeX-style percentage notation
    text = re.sub(r'\$(\d+)\s*\\%\s*(\d*)\$', r'\1%', text)
    # Fix other LaTeX artifacts
    text = re.sub(r'\$[^$]+\$', lambda m: m.group(0).replace('$', '').replace('\\', ''), text)
    # Fix mojibake
    text = text.replace('â€™', "'").replace('â€"', "-").replace('â€œ', '"').replace('â€', '"')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def infer_domain_tags(term: str, definition: str) -> list:
    """Infer domain tags based on term and definition content."""
    tags = []
    combined = (term + " " + definition).lower()

    # Heritage
    if any(w in combined for w in ['heritage', 'conservation area', 'historic', 'cultural significance', 'burra charter']):
        tags.append('heritage')

    # Parking
    if any(w in combined for w in ['parking', 'car space', 'vehicle', 'tandem', 'stacked', 'car stacker']):
        tags.append('parking')

    # Setback
    if any(w in combined for w in ['setback', 'build to line', 'street frontage', 'boundary']):
        tags.append('setback')

    # Flood
    if any(w in combined for w in ['flood', 'inundation', 'floodplain', 'floodway', 'probable maximum flood', 'pmf']):
        tags.append('flood')

    # Tree
    if any(w in combined for w in ['tree', 'arborist', 'pruning', 'trunk', 'canopy', 'root']):
        tags.append('tree')

    # Stormwater/drainage
    if any(w in combined for w in ['stormwater', 'drainage', 'runoff', 'detention', 'catchment', 'osd']):
        tags.append('stormwater')

    # Waste
    if any(w in combined for w in ['waste', 'garbage', 'recyclable', 'compost']):
        tags.append('waste')

    # Building/construction
    if any(w in combined for w in ['building', 'construction', 'structural', 'floor', 'ceiling', 'wall']):
        tags.append('building')

    # Access/disability
    if any(w in combined for w in ['accessible', 'disability', 'wheelchair', 'universal design', 'adaptable']):
        tags.append('accessibility')

    # Landscaping
    if any(w in combined for w in ['landscap', 'planting', 'deep soil', 'soft landscape']):
        tags.append('landscaping')

    return tags


def parse_prose_definitions(content: str, source_config: dict) -> list[Definition]:
    """
    Parse definitions from prose format (Marrickville/Leichhardt).
    Format: "Term means definition text."
    """
    definitions = []

    # Split into paragraphs
    paragraphs = re.split(r'\n\n+', content)

    for para in paragraphs:
        para = para.strip()
        if not para or para.startswith('#') or para.startswith('KEY TERMS'):
            continue

        # Match pattern: "Term means definition" or "Term is definition"
        # Term starts with capital letter, followed by "means" or "is"
        match = re.match(
            r'^([A-Z][A-Za-z\s&\(\)/-]+?)\s+(?:means|is|–)\s+(.+)',
            para,
            re.DOTALL
        )

        if match:
            term = match.group(1).strip()
            definition = match.group(2).strip()

            # Skip if term is too long (probably not a definition)
            if len(term) > 100:
                continue

            # Clean up
            definition = clean_definition_text(definition)

            defn = Definition(
                term=term,
                term_normalized=normalize_term(term),
                definition_text=definition,
                source_document=source_config["source_document"],
                source_clause=source_config["source_clause"],
                legislation_type="DCP",
                lga=source_config["lga"],
                former_council=source_config["former_council"],
                pdf_source_file=str(source_config.get("pdf_source", "")),
                domain_tags=infer_domain_tags(term, definition),
            )
            definitions.append(defn)

    return definitions


def parse_html_table_definitions(content: str, source_config: dict) -> list[Definition]:
    """
    Parse definitions from HTML table format (Ashfield).
    Format: <table><tr><td>Term</td><td>Definition</td></tr>
    """
    definitions = []

    soup = BeautifulSoup(content, 'html.parser')
    tables = soup.find_all('table')

    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')

            # Skip rows without exactly 2 meaningful cells
            if len(cells) < 2:
                continue

            term_cell = cells[0].get_text(strip=True)
            definition_cell = cells[1].get_text(separator=' ', strip=True)

            # Skip empty cells or header rows
            if not term_cell or not definition_cell:
                continue

            # Skip if looks like a header
            if term_cell.lower() in ['definitions', 'term', 'meaning']:
                continue

            # Clean up term (remove numbering artifacts, fix OCR issues)
            term = term_cell.strip()
            term = re.sub(r'^\d+[\.\)]\s*', '', term)  # Remove numbering

            # Skip if term is too short or too long
            if len(term) < 2 or len(term) > 100:
                continue

            # Clean up definition
            definition = clean_definition_text(definition_cell)

            # Skip if definition is too short
            if len(definition) < 10:
                continue

            defn = Definition(
                term=term,
                term_normalized=normalize_term(term),
                definition_text=definition,
                source_document=source_config["source_document"],
                source_clause=source_config["source_clause"],
                legislation_type="DCP",
                lga=source_config["lga"],
                former_council=source_config["former_council"],
                pdf_source_file=str(source_config.get("pdf_source", "")),
                domain_tags=infer_domain_tags(term, definition),
                extraction_confidence=0.9,  # Lower confidence for OCR-extracted tables
            )
            definitions.append(defn)

    return definitions


def parse_dcp_glossary(dcp_key: str) -> list[Definition]:
    """Parse a single DCP glossary and return definitions."""
    config = DCP_SOURCES[dcp_key]
    md_path = config["path"]

    if not md_path.exists():
        print(f"  [SKIP] File not found: {md_path}")
        return []

    content = md_path.read_text(encoding='utf-8')

    if config["format"] == "prose":
        definitions = parse_prose_definitions(content, config)
    elif config["format"] == "html_table":
        definitions = parse_html_table_definitions(content, config)
    else:
        print(f"  [SKIP] Unknown format: {config['format']}")
        return []

    return definitions


def main():
    """Parse all DCP glossaries and output to JSON."""
    print("=" * 70)
    print("PARSE DCP GLOSSARIES")
    print("=" * 70)
    print()

    # Create output directory
    DEFINITIONS_OUTPUT.mkdir(parents=True, exist_ok=True)

    all_definitions = []

    for dcp_key, config in DCP_SOURCES.items():
        print(f"Processing: {config['source_document']}")
        print(f"  Source: {config['path'].name}")

        definitions = parse_dcp_glossary(dcp_key)
        print(f"  Extracted: {len(definitions)} definitions")

        # Show sample
        if definitions:
            sample = definitions[0]
            print(f"  Sample: '{sample.term}' => {sample.definition_text[:60]}...")

        all_definitions.extend(definitions)
        print()

    # Output to JSON
    output_path = DEFINITIONS_OUTPUT / "dcp_definitions.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(
            [asdict(d) for d in all_definitions],
            f,
            indent=2,
            ensure_ascii=False
        )

    print("=" * 70)
    print(f"Total definitions extracted: {len(all_definitions)}")
    print(f"Output: {output_path}")
    print("=" * 70)

    # Summary by source
    print()
    print("By source:")
    by_source = {}
    for d in all_definitions:
        key = d.former_council
        by_source[key] = by_source.get(key, 0) + 1
    for source, count in sorted(by_source.items()):
        print(f"  {source}: {count}")

    return all_definitions


if __name__ == "__main__":
    main()
