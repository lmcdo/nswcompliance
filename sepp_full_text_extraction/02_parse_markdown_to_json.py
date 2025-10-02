"""
STEP 2: Parse MinerU markdown output into structured JSON provisions

Takes markdown files from Step 1 and creates structured JSON with:
- Individual provisions (clauses, sections, schedules)
- Full text for each provision
- Metadata (ref numbers, types, hierarchy)
- Cross-references

Output: JSON files in docs/sepps/extracted/ alongside markdown files

Exit Codes:
- 0: Success - all markdown files parsed
- 1: Failure - parsing errors
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Configuration
EXTRACTED_DIR = Path("../docs/sepps/extracted")
METADATA_FILE = EXTRACTED_DIR / "extraction_metadata.json"
PARSING_REPORT = EXTRACTED_DIR / "parsing_report.json"

class ProvisionParser:
    """Parse SEPP markdown into structured provisions"""

    # Regex patterns for different provision types
    PATTERNS = {
        'chapter': re.compile(r'^#+\s+(Chapter\s+\d+[A-Z]?.*)', re.MULTILINE | re.IGNORECASE),
        'part': re.compile(r'^#+\s+(Part\s+\d+[A-Z]?.*)', re.MULTILINE | re.IGNORECASE),
        'division': re.compile(r'^#+\s+(Division\s+\d+[A-Z]?.*)', re.MULTILINE | re.IGNORECASE),
        'clause': re.compile(r'^#+\s*(\d+[A-Z]?)\s+(.+?)$', re.MULTILINE),
        'section': re.compile(r'^#+\s*(Section\s+\d+[A-Z]?.*)', re.MULTILINE | re.IGNORECASE),
        'schedule': re.compile(r'^#+\s*(Schedule\s+\d+[A-Z]?.*)', re.MULTILINE | re.IGNORECASE),
    }

    def __init__(self, markdown_text: str, sepp_name: str):
        self.markdown = markdown_text
        self.sepp_name = sepp_name
        self.provisions = []

    def parse(self) -> List[Dict[str, Any]]:
        """Parse markdown into provisions"""

        # Split by major headings (##, ###, etc.)
        lines = self.markdown.split('\n')
        current_provision = None
        current_text = []
        current_hierarchy = {
            'chapter': None,
            'part': None,
            'division': None,
        }

        for i, line in enumerate(lines):
            # Check if line is a heading
            if line.startswith('#'):
                # Save previous provision if exists
                if current_provision:
                    current_provision['provision_text'] = '\n'.join(current_text).strip()
                    current_provision['text_length'] = len(current_provision['provision_text'])
                    self.provisions.append(current_provision)
                    current_text = []

                # Parse new heading
                heading_info = self._parse_heading(line)

                if heading_info:
                    # Update hierarchy
                    if heading_info['type'] == 'chapter':
                        current_hierarchy['chapter'] = heading_info['title']
                        current_hierarchy['part'] = None
                        current_hierarchy['division'] = None
                    elif heading_info['type'] == 'part':
                        current_hierarchy['part'] = heading_info['title']
                        current_hierarchy['division'] = None
                    elif heading_info['type'] == 'division':
                        current_hierarchy['division'] = heading_info['title']

                    # Create new provision
                    current_provision = {
                        'ref_number': heading_info.get('ref_number', heading_info['title']),
                        'provision_type': self._classify_provision_type(heading_info),
                        'section_header': heading_info.get('title'),
                        'chapter': current_hierarchy['chapter'],
                        'part': current_hierarchy['part'],
                        'division': current_hierarchy['division'],
                        'document_id': self.sepp_name,
                        'line_number': i + 1,
                    }
            else:
                # Accumulate text for current provision
                if line.strip():
                    current_text.append(line)

        # Save last provision
        if current_provision:
            current_provision['provision_text'] = '\n'.join(current_text).strip()
            current_provision['text_length'] = len(current_provision['provision_text'])
            self.provisions.append(current_provision)

        # Post-process provisions
        self._extract_subsections()
        self._identify_cross_references()
        self._calculate_metadata()

        return self.provisions

    def _parse_heading(self, line: str) -> Dict[str, Any]:
        """Parse heading line into structured info"""
        # Count heading level
        level = len(re.match(r'^#+', line).group())
        text = line.lstrip('#').strip()

        # Try to match different provision types
        for prov_type, pattern in self.PATTERNS.items():
            match = pattern.search(line)
            if match:
                if prov_type == 'clause':
                    return {
                        'type': 'clause',
                        'ref_number': match.group(1),
                        'title': match.group(2),
                        'heading_level': level
                    }
                else:
                    return {
                        'type': prov_type,
                        'title': match.group(1),
                        'ref_number': match.group(1),
                        'heading_level': level
                    }

        # Generic provision
        return {
            'type': 'provision',
            'title': text,
            'ref_number': text[:50],  # Use first 50 chars as ref
            'heading_level': level
        }

    def _classify_provision_type(self, heading_info: Dict) -> str:
        """Classify provision into formal types"""
        title = heading_info.get('title', '').lower()
        prov_type = heading_info.get('type', '')

        # Map to formal types used in database
        if prov_type in ['chapter', 'part', 'division']:
            return f'context_{prov_type}'

        if any(word in title for word in ['definition', 'means', 'dictionary']):
            return 'formal_Definitions'
        elif any(word in title for word in ['aim', 'objective', 'purpose']):
            return 'formal_Policy Aims'
        elif any(word in title for word in ['application', 'applies to']):
            return 'formal_applicability'
        elif any(word in title for word in ['exemption', 'does not apply']):
            return 'formal_exemptions'
        elif any(word in title for word in ['standard', 'requirement']):
            return 'formal_mandatory requirement'
        elif any(word in title for word in ['development consent', 'consent authority']):
            return 'formal_assessment criteria'
        elif 'schedule' in title.lower():
            return 'formal_Schedule'
        else:
            return 'formal_provision'

    def _extract_subsections(self):
        """Extract subsections (1), (a), (i) from provision text"""
        for provision in self.provisions:
            text = provision.get('provision_text', '')

            # Find subsections: (1), (2), (a), (b), (i), (ii)
            subsection_pattern = r'\((\d+|[a-z]+|[ivx]+)\)'
            subsections = re.findall(subsection_pattern, text)

            provision['subsections'] = subsections
            provision['has_subsections'] = len(subsections) > 0
            provision['subsection_count'] = len(subsections)

    def _identify_cross_references(self):
        """Identify cross-references to other provisions"""
        for provision in self.provisions:
            text = provision.get('provision_text', '')

            # Find references to clauses, sections, schedules
            refs = []

            # Clause references: "clause 5.2", "Clause 12"
            clause_refs = re.findall(r'[Cc]lause\s+(\d+(?:\.\d+)?)', text)
            refs.extend([f"Clause {ref}" for ref in clause_refs])

            # Section references: "section 31", "Section 4.1"
            section_refs = re.findall(r'[Ss]ection\s+(\d+(?:\.\d+)?)', text)
            refs.extend([f"Section {ref}" for ref in section_refs])

            # Schedule references: "Schedule 1", "schedule 3"
            schedule_refs = re.findall(r'[Ss]chedule\s+(\d+)', text)
            refs.extend([f"Schedule {ref}" for ref in schedule_refs])

            provision['cross_references'] = list(set(refs))  # Unique refs
            provision['cross_reference_count'] = len(provision['cross_references'])

    def _calculate_metadata(self):
        """Calculate metadata for each provision"""
        for provision in self.provisions:
            text = provision.get('provision_text', '')

            provision['metadata'] = {
                'char_count': len(text),
                'word_count': len(text.split()),
                'line_count': text.count('\n') + 1,
                'has_tables': '|' in text and text.count('|') > 5,
                'has_lists': text.count('-') > 3 or text.count('•') > 3,
                'has_numbers': bool(re.search(r'\$[\d,]+', text)),
                'contains_must': 'must' in text.lower(),
                'contains_may': 'may' in text.lower(),
            }

def parse_single_sepp(markdown_file: Path) -> Dict[str, Any]:
    """Parse single SEPP markdown file"""
    sepp_name = markdown_file.stem  # Get filename without .md extension
    print(f"\n{'='*80}")
    print(f"PARSING: {sepp_name}")
    print(f"{'='*80}")

    result = {
        "sepp_name": sepp_name,
        "markdown_file": str(markdown_file),
        "success": False,
        "error": None,
    }

    try:
        # Read markdown
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_text = f.read()

        result['markdown_size'] = len(markdown_text)

        # Parse provisions
        parser = ProvisionParser(markdown_text, sepp_name)
        provisions = parser.parse()

        result['provision_count'] = len(provisions)
        result['provisions'] = provisions

        # Calculate statistics
        total_text_length = sum(p.get('text_length', 0) for p in provisions)
        avg_text_length = total_text_length / len(provisions) if provisions else 0

        result['statistics'] = {
            'total_provisions': len(provisions),
            'total_text_length': total_text_length,
            'average_text_length': int(avg_text_length),
            'shortest_provision': min((p.get('text_length', 0) for p in provisions), default=0),
            'longest_provision': max((p.get('text_length', 0) for p in provisions), default=0),
            'provisions_with_subsections': sum(1 for p in provisions if p.get('has_subsections')),
            'provisions_with_cross_refs': sum(1 for p in provisions if p.get('cross_reference_count', 0) > 0),
        }

        # Save JSON output
        json_file = markdown_file.parent / f"{sepp_name}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'sepp_name': sepp_name,
                'extraction_timestamp': datetime.now().isoformat(),
                'markdown_source': str(markdown_file),
                'statistics': result['statistics'],
                'provisions': provisions
            }, f, indent=2)

        result['json_file'] = str(json_file)
        result['success'] = True

        # Print summary
        print(f"\nParsing Summary:")
        print(f"  Markdown Size:     {result['markdown_size']:>12,} bytes")
        print(f"  Provisions Found:  {result['provision_count']:>12,}")
        print(f"  Total Text:        {total_text_length:>12,} chars")
        print(f"  Avg Provision:     {avg_text_length:>12,.0f} chars")
        print(f"  JSON Output:       {json_file}")
        print(f"  Status:            [OK] SUCCESS")

        return result

    except Exception as e:
        result['error'] = str(e)
        print(f"[X] Parsing failed: {e}")
        return result

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("SEPP MARKDOWN TO JSON PARSER - STEP 2")
    print("="*80 + "\n")

    # Load extraction metadata
    if not METADATA_FILE.exists():
        print(f"[X] Extraction metadata not found: {METADATA_FILE}")
        print("Run 01_extract_sepps_mineru.py first")
        return 1

    with open(METADATA_FILE, 'r') as f:
        extraction_metadata = json.load(f)

    successful_extractions = [r for r in extraction_metadata['results'] if r['success']]

    if not successful_extractions:
        print("[X] No successful extractions found")
        return 1

    print(f"Found {len(successful_extractions)} successful extractions\n")

    # Parse each SEPP
    parsing_results = []
    for extraction in successful_extractions:
        md_file = Path(extraction['output_file'])
        if md_file.exists():
            result = parse_single_sepp(md_file)
            parsing_results.append(result)
        else:
            print(f"[X] Markdown file not found: {md_file}")

    # Generate report
    total = len(parsing_results)
    successful = sum(1 for r in parsing_results if r['success'])
    failed = total - successful

    print(f"\n{'='*80}")
    print("PARSING VERIFICATION REPORT")
    print(f"{'='*80}\n")
    print(f"Total SEPPs:       {total}")
    print(f"Successful:        {successful} [OK]")
    print(f"Failed:            {failed} {'[X]' if failed > 0 else ''}\n")

    # Detailed statistics
    if successful > 0:
        total_provisions = sum(r.get('provision_count', 0) for r in parsing_results if r['success'])
        total_text = sum(r.get('statistics', {}).get('total_text_length', 0)
                        for r in parsing_results if r['success'])

        print(f"Total Provisions:  {total_provisions:,}")
        print(f"Total Text:        {total_text:,} characters ({total_text/1_000_000:.2f} MB)")
        print(f"Avg per SEPP:      {total_provisions/successful:.0f} provisions")
        print()

    # Save parsing report
    parsing_report = {
        'parsing_timestamp': datetime.now().isoformat(),
        'total_sepps': total,
        'successful_parsings': successful,
        'failed_parsings': failed,
        'results': parsing_results
    }

    with open(PARSING_REPORT, 'w') as f:
        json.dump(parsing_report, f, indent=2)

    print(f"Parsing report saved: {PARSING_REPORT}")

    if successful == total:
        print("\n[SUCCESS] ALL PARSINGS SUCCESSFUL")
        print(f"\nNext step: Run 03_update_database_schema.py")
        return 0
    else:
        print("\n[X] SOME PARSINGS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())