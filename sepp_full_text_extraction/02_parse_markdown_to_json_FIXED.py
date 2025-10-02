"""
STEP 2 FIXED: Parse MinerU markdown to structured JSON with relationships

Extracts:
- Clauses with full text (1.1, 2.1, 3.2, etc.)
- Hierarchical structure (Chapter → Part → Clause)
- Subsections (1), (a), (i)
- Cross-references (to schedules, maps, tables, other clauses, other SEPPs)
- Definitions and their usage
- Relationships between provisions

Exit Codes:
- 0: Success - all markdown parsed
- 1: Failure - parsing errors
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

EXTRACTED_DIR = Path("docs/sepps/extracted")
PARSING_REPORT = EXTRACTED_DIR / "parsing_report.json"

class SEPPMarkdownParser:
    """Parse NSW SEPP markdown into structured provisions with relationships"""

    # Clause patterns: "1.1   Name of Policy"
    CLAUSE_PATTERN = re.compile(r'^(\d+\.\d+(?:\.\d+)?)\s{2,}(.+)$', re.MULTILINE)

    # Chapter/Part/Division patterns
    CHAPTER_PATTERN = re.compile(r'^Chapter\s+(\d+)\s+(.+)$', re.IGNORECASE)
    PART_PATTERN = re.compile(r'^Part\s+(\d+)\s+(.+)$', re.IGNORECASE)
    DIVISION_PATTERN = re.compile(r'^Division\s+(\d+)\s+(.+)$', re.IGNORECASE)

    # Schedule pattern
    SCHEDULE_PATTERN = re.compile(r'^Schedule\s+(\d+)\s+(.+)$', re.IGNORECASE)

    # Subsection patterns
    SUBSECTION_NUMERIC = re.compile(r'^\s*\((\d+)\)\s+(.+)', re.MULTILINE)
    SUBSECTION_LETTER = re.compile(r'^\s*\(([a-z])\)\s+(.+)', re.MULTILINE)
    SUBSECTION_ROMAN = re.compile(r'^\s*\((i+|iv|v|vi+|ix|x)\)\s+(.+)', re.MULTILINE)

    # Cross-reference patterns
    REF_CLAUSE = re.compile(r'\b(?:clause|section)\s+(\d+(?:\.\d+)*(?:\([0-9a-z]+\))?)', re.IGNORECASE)
    REF_SCHEDULE = re.compile(r'\bSchedule\s+(\d+)', re.IGNORECASE)
    REF_TABLE = re.compile(r'\bTable\s+(\d+)', re.IGNORECASE)
    REF_MAP = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Map\b')
    REF_OTHER_SEPP = re.compile(r'State Environmental Planning Policy \([^)]+\) \d{4}(?:, (?:Chapter|section|Schedule) \S+)?')

    # Definition patterns
    DEFINITION_PATTERN = re.compile(r'\bdefined in\b|\bmeans\b|\bDictionary\b', re.IGNORECASE)

    def __init__(self, markdown_file: Path, sepp_name: str):
        self.markdown_file = markdown_file
        self.sepp_name = sepp_name
        self.provisions = []
        self.relationships = []
        self.current_chapter = None
        self.current_part = None
        self.current_division = None

    def parse(self) -> Tuple[List[Dict], List[Dict]]:
        """Parse markdown file into provisions and relationships"""
        print(f"\n[Parsing] {self.sepp_name}")

        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove page headers and metadata
        content = self._clean_content(content)

        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Check for hierarchical markers
            if self._update_hierarchy(line):
                i += 1
                continue

            # Check for clauses
            clause_match = self.CLAUSE_PATTERN.match(lines[i])
            if clause_match:
                clause_num = clause_match.group(1)
                clause_title = clause_match.group(2)

                # Extract full text until next clause
                i += 1
                text_lines = []
                while i < len(lines):
                    next_line = lines[i]
                    # Stop at next clause or hierarchical marker
                    if (self.CLAUSE_PATTERN.match(next_line) or
                        self.CHAPTER_PATTERN.match(next_line.strip()) or
                        self.PART_PATTERN.match(next_line.strip()) or
                        self.SCHEDULE_PATTERN.match(next_line.strip())):
                        break
                    text_lines.append(next_line)
                    i += 1

                full_text = '\n'.join(text_lines).strip()

                # Create provision
                provision = self._create_provision(clause_num, clause_title, full_text)
                self.provisions.append(provision)

                # Extract relationships
                self._extract_relationships(provision)

                continue

            # Check for schedules
            schedule_match = self.SCHEDULE_PATTERN.match(line)
            if schedule_match:
                schedule_num = schedule_match.group(1)
                schedule_title = schedule_match.group(2)

                # Extract schedule content
                i += 1
                text_lines = []
                while i < len(lines):
                    next_line = lines[i]
                    if self.SCHEDULE_PATTERN.match(next_line.strip()):
                        break
                    text_lines.append(next_line)
                    i += 1

                full_text = '\n'.join(text_lines).strip()

                # Create schedule as special provision
                provision = {
                    'ref_number': f'Schedule {schedule_num}',
                    'section_header': schedule_title,
                    'provision_text': full_text[:10000],  # Limit schedule text
                    'provision_type': 'formal_Schedule',
                    'chapter': self.current_chapter,
                    'part': self.current_part,
                    'division': self.current_division,
                    'document_id': self.sepp_name,
                    'text_length': len(full_text),
                    'is_schedule': True,
                    'schedule_number': schedule_num
                }
                self.provisions.append(provision)
                continue

            i += 1

        print(f"  [OK] Extracted {len(self.provisions)} provisions")
        print(f"  [OK] Identified {len(self.relationships)} relationships")

        return self.provisions, self.relationships

    def _clean_content(self, content: str) -> str:
        """Remove PDF metadata and page markers"""
        # Remove "## Page N" markers
        content = re.sub(r'^##\s+Page\s+\d+\s*$', '', content, flags=re.MULTILINE)

        # Remove extraction metadata lines
        content = re.sub(r'^Extracted:\s+\d{4}-\d{2}-\d{2}\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^Total Pages:\s+\d+\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^={40,}\s*$', '', content, flags=re.MULTILINE)

        # Remove "Current version for..." status lines
        content = re.sub(r'^Current version for .+$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^Status information$', '', content, flags=re.MULTILINE)

        # Remove footer timestamps
        content = re.sub(r'^\d+/\d+/\d+,\s+\d+:\d+\s+[AP]M\s*$', '', content, flags=re.MULTILINE)

        # Remove URL lines
        content = re.sub(r'^https?://[^\s]+$', '', content, flags=re.MULTILINE)

        # Remove page numbers like "1/17"
        content = re.sub(r'^\d+/\d+\s*$', '', content, flags=re.MULTILINE)

        return content

    def _update_hierarchy(self, line: str) -> bool:
        """Update current hierarchical position"""
        chapter_match = self.CHAPTER_PATTERN.match(line)
        if chapter_match:
            self.current_chapter = f"Chapter {chapter_match.group(1)}"
            self.current_part = None
            self.current_division = None
            return True

        part_match = self.PART_PATTERN.match(line)
        if part_match:
            self.current_part = f"Part {part_match.group(1)}"
            self.current_division = None
            return True

        division_match = self.DIVISION_PATTERN.match(line)
        if division_match:
            self.current_division = f"Division {division_match.group(1)}"
            return True

        return False

    def _create_provision(self, clause_num: str, clause_title: str, full_text: str) -> Dict:
        """Create structured provision"""
        # Extract subsections
        subsections_numeric = self.SUBSECTION_NUMERIC.findall(full_text)
        subsections_letter = self.SUBSECTION_LETTER.findall(full_text)
        subsections_roman = self.SUBSECTION_ROMAN.findall(full_text)

        all_subsections = []
        if subsections_numeric:
            all_subsections.extend([f"({n})" for n, _ in subsections_numeric])
        if subsections_letter:
            all_subsections.extend([f"({l})" for l, _ in subsections_letter])
        if subsections_roman:
            all_subsections.extend([f"({r})" for r, _ in subsections_roman])

        # Classify provision type
        provision_type = self._classify_provision(clause_title, full_text)

        return {
            'ref_number': clause_num,
            'section_header': clause_title,
            'provision_text': full_text,
            'provision_type': provision_type,
            'chapter': self.current_chapter,
            'part': self.current_part,
            'division': self.current_division,
            'document_id': self.sepp_name,
            'text_length': len(full_text),
            'has_subsections': len(all_subsections) > 0,
            'subsection_count': len(all_subsections),
            'subsections': all_subsections,
            'metadata': {
                'word_count': len(full_text.split()),
                'has_lists': bool(subsections_numeric or subsections_letter),
                'has_numeric_subsections': bool(subsections_numeric),
                'has_letter_subsections': bool(subsections_letter),
                'has_roman_subsections': bool(subsections_roman),
            }
        }

    def _classify_provision(self, title: str, text: str) -> str:
        """Classify provision type based on title and content"""
        title_lower = title.lower()
        text_lower = text[:500].lower()

        if any(word in title_lower for word in ['definition', 'dictionary', 'means']):
            return 'formal_Definitions'
        elif any(word in title_lower for word in ['aim', 'objective', 'purpose']):
            return 'formal_Policy Aims'
        elif any(word in title_lower for word in ['application', 'applies to']):
            return 'formal_applicability'
        elif any(word in title_lower for word in ['exemption', 'does not apply']):
            return 'formal_exemptions'
        elif any(word in title_lower for word in ['standard', 'requirement']):
            return 'formal_mandatory requirement'
        elif any(word in title_lower for word in ['consent', 'approval']):
            return 'formal_assessment criteria'
        elif 'map' in title_lower:
            return 'formal_Maps'
        elif 'basix' in text_lower:
            return 'formal_BASIX Standards'
        elif any(word in text_lower for word in ['climate zone', 'thermal']):
            return 'formal_Energy Use Standard'
        elif any(word in text_lower for word in ['water use', 'potable water']):
            return 'formal_Water Use Standard'
        else:
            return 'formal_provision'

    def _extract_relationships(self, provision: Dict):
        """Extract all relationships from provision text"""
        text = provision['provision_text']
        clause_num = provision['ref_number']

        # Cross-references to other clauses
        clause_refs = self.REF_CLAUSE.findall(text)
        for ref in clause_refs:
            if ref != clause_num:  # Don't self-reference
                self.relationships.append({
                    'source_clause': clause_num,
                    'target_clause': ref,
                    'relationship_type': 'references_clause',
                    'document_id': self.sepp_name
                })

        # References to schedules
        schedule_refs = self.REF_SCHEDULE.findall(text)
        for ref in schedule_refs:
            self.relationships.append({
                'source_clause': clause_num,
                'target_schedule': f'Schedule {ref}',
                'relationship_type': 'references_schedule',
                'document_id': self.sepp_name
            })

        # References to tables
        table_refs = self.REF_TABLE.findall(text)
        for ref in table_refs:
            self.relationships.append({
                'source_clause': clause_num,
                'target_table': f'Table {ref}',
                'relationship_type': 'references_table',
                'document_id': self.sepp_name
            })

        # References to maps
        map_refs = self.REF_MAP.findall(text)
        for ref in map_refs:
            self.relationships.append({
                'source_clause': clause_num,
                'target_map': f'{ref} Map',
                'relationship_type': 'references_map',
                'document_id': self.sepp_name
            })

        # References to other SEPPs
        sepp_refs = self.REF_OTHER_SEPP.findall(text)
        for ref in sepp_refs:
            self.relationships.append({
                'source_clause': clause_num,
                'target_sepp': ref,
                'relationship_type': 'references_other_sepp',
                'document_id': self.sepp_name
            })

        # Definitions
        if self.DEFINITION_PATTERN.search(text):
            self.relationships.append({
                'source_clause': clause_num,
                'relationship_type': 'contains_definitions',
                'document_id': self.sepp_name
            })

def parse_all_markdown_files():
    """Parse all markdown files in extracted directory"""
    print("\n" + "="*80)
    print("PARSING SEPP MARKDOWN FILES TO JSON")
    print("="*80)

    if not EXTRACTED_DIR.exists():
        print(f"[X] Directory not found: {EXTRACTED_DIR}")
        return False

    # Find all markdown files
    md_files = list(EXTRACTED_DIR.glob("*.md"))
    print(f"\nFound {len(md_files)} markdown files")

    results = []
    all_relationships = []
    total_provisions = 0
    total_relationships = 0

    for md_file in md_files:
        sepp_name = md_file.stem

        try:
            parser = SEPPMarkdownParser(md_file, sepp_name)
            provisions, relationships = parser.parse()

            # Save JSON file
            json_file = EXTRACTED_DIR / f"{sepp_name}.json"
            output_data = {
                'sepp_name': sepp_name,
                'extraction_date': datetime.now().isoformat(),
                'source_file': str(md_file),
                'provision_count': len(provisions),
                'relationship_count': len(relationships),
                'provisions': provisions,
                'relationships': relationships
            }

            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            total_provisions += len(provisions)
            total_relationships += len(relationships)
            all_relationships.extend(relationships)

            results.append({
                'sepp_name': sepp_name,
                'md_file': str(md_file),
                'json_file': str(json_file),
                'provision_count': len(provisions),
                'relationship_count': len(relationships),
                'success': True
            })

            print(f"  [OK] Saved: {json_file.name}")

        except Exception as e:
            print(f"  [FAIL] Failed: {sepp_name}")
            print(f"    Error: {e}")
            results.append({
                'sepp_name': sepp_name,
                'md_file': str(md_file),
                'success': False,
                'error': str(e)
            })

    # Save parsing report
    report = {
        'parsing_timestamp': datetime.now().isoformat(),
        'total_markdown_files': len(md_files),
        'successful_parses': sum(1 for r in results if r['success']),
        'failed_parses': sum(1 for r in results if not r['success']),
        'total_provisions': total_provisions,
        'total_relationships': total_relationships,
        'results': results,
        'relationship_summary': _summarize_relationships(all_relationships)
    }

    with open(PARSING_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'='*80}")
    print("PARSING SUMMARY")
    print(f"{'='*80}")
    print(f"Total markdown files: {len(md_files)}")
    print(f"Successful parses:    {report['successful_parses']}")
    print(f"Failed parses:        {report['failed_parses']}")
    print(f"Total provisions:     {total_provisions:,}")
    print(f"Total relationships:  {total_relationships:,}")
    print(f"\nReport saved: {PARSING_REPORT}")

    # Show relationship breakdown
    print(f"\n{'='*80}")
    print("RELATIONSHIP BREAKDOWN")
    print(f"{'='*80}")
    for rel_type, count in report['relationship_summary'].items():
        print(f"  {rel_type:30} {count:>6,}")

    return report['failed_parses'] == 0

def _summarize_relationships(relationships: List[Dict]) -> Dict[str, int]:
    """Summarize relationship types"""
    summary = {}
    for rel in relationships:
        rel_type = rel.get('relationship_type', 'unknown')
        summary[rel_type] = summary.get(rel_type, 0) + 1
    return summary

def main():
    """Main execution"""
    success = parse_all_markdown_files()

    if success:
        print(f"\n[SUCCESS] All markdown files parsed successfully")
        print(f"\nNext step: Run 03_update_database_schema.py")
        return 0
    else:
        print(f"\n[FAILURE] Some markdown files failed to parse")
        print(f"Check parsing_report.json for details")
        return 1

if __name__ == "__main__":
    sys.exit(main())