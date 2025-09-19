#!/usr/bin/env python3
"""
Council Validation Service
Provides full citation traceability and regulatory text for council verification
"""

from db_config import get_connection  # Unified PostgreSQL connection
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .database_autoschema_query import DatabaseAutoSchemaQuery

@dataclass
class FullCitation:
    """Complete citation with full regulatory text for council validation"""
    clause_ref: str                    # "Section 4.2.4.3" or "C16"
    document_name: str                 # "Marrickville DCP 2011"
    section_title: str                 # "Building Setbacks"
    full_text: str                     # Complete regulatory paragraph
    text_before: str                   # Preceding text for understanding
    text_before_source: str            # Which clause/section the text before comes from
    text_after: str                    # Following text for understanding  
    text_after_source: str             # Which clause/section the text after comes from
    page_reference: Optional[str]      # Page number if available
    last_amended: Optional[str]        # Amendment date if available
    authority: str                     # "Inner West Council DCP" or "NSW LEP"
    confidence: float                  # Citation accuracy confidence
    
@dataclass
class ValidatedRelationship:
    """Regulatory relationship with full citation traceability"""
    primary_clause: FullCitation
    connected_clause: FullCitation
    relationship_type: str             # "must_comply_with", "in_accordance_with"
    relationship_text: str             # Exact text showing the relationship
    validation_notes: str              # Why this relationship exists
    precedence_order: int              # Which clause takes precedence
    
@dataclass
class CouncilValidationReport:
    """Complete validation report for council review"""
    property_address: str
    zone: str
    applicable_documents: List[str]
    active_citations: List[FullCitation]
    validated_relationships: List[ValidatedRelationship] 
    extracted_values: Dict[str, Any]   # Actual setback distances, heights
    confidence_assessment: str
    validation_timestamp: str
    regulatory_summary: str

class CouncilValidationService:
    """Service for generating council-ready validation reports"""
    
    def __init__(self, db_path: str = "nsw_planning.db"):
        self.db_path = db_path
        self.db_query = DatabaseAutoSchemaQuery(db_path)
        
    def generate_validation_report(self, 
                                 address: str, 
                                 zone: str,
                                 query_terms: List[str]) -> CouncilValidationReport:
        """Generate complete validation report with full citations"""
        
        # Get base regulatory relationships
        relationships = self.db_query.find_regulatory_relationships(query_terms)
        
        # Extract full citations for each relationship
        active_citations = []
        validated_relationships = []
        
        for rel in relationships:
            # Get full citation with complete text
            primary_citation = self._extract_full_citation(
                rel["source"], rel["document"], rel["text"]
            )
            
            # Get connected clause citation if available
            target_citation = self._extract_full_citation(
                rel["target"], rel["document"], ""
            )
            
            # Only add real citations to active_citations, not concepts
            # Avoid duplicates by checking if citation already exists
            citation_key = f"{primary_citation.clause_ref}|{primary_citation.document_name}"
            if not any(f"{c.clause_ref}|{c.document_name}" == citation_key for c in active_citations):
                active_citations.append(primary_citation)
            
            if target_citation.authority != "NSW Planning Concepts":
                target_key = f"{target_citation.clause_ref}|{target_citation.document_name}"
                if not any(f"{c.clause_ref}|{c.document_name}" == target_key for c in active_citations):
                    active_citations.append(target_citation)
            
            # Create validated relationship
            validated_relationships.append(ValidatedRelationship(
                primary_clause=primary_citation,
                connected_clause=target_citation,
                relationship_type=rel["relation"],
                relationship_text=rel["text"][:300] + "..." if len(rel["text"]) > 300 else rel["text"],
                validation_notes=f"Relationship identified through {rel['relation']} pattern in regulatory text",
                precedence_order=self._determine_precedence(primary_citation.clause_ref)
            ))
        
        # Extract actual regulatory values
        extracted_values = self._extract_regulatory_values(active_citations, zone)
        
        # Create comprehensive report
        return CouncilValidationReport(
            property_address=address,
            zone=zone,
            applicable_documents=list(set(rel["document"] for rel in relationships)),
            active_citations=active_citations,
            validated_relationships=validated_relationships,
            extracted_values=extracted_values,
            confidence_assessment=self._assess_confidence(active_citations),
            validation_timestamp=self._get_timestamp(),
            regulatory_summary=self._generate_summary(validated_relationships, extracted_values)
        )
    
    def _extract_full_citation(self, clause_ref: str, document: str, excerpt: str) -> FullCitation:
        """Extract complete citation with full regulatory text from database"""
        
        # Check if this is a concept target (not a real clause)
        concept_targets = ['building_setback', 'building_height', 'floor_space_ratio', 'site_coverage']
        if clause_ref in concept_targets:
            # Return a concept citation without trying to find it in DB
            return FullCitation(
                clause_ref=clause_ref,
                document_name=document,
                section_title=f"Regulatory Concept: {clause_ref.replace('_', ' ').title()}",
                full_text=excerpt if excerpt else f"This clause regulates {clause_ref.replace('_', ' ')}",
                text_before="",
                text_before_source="",
                text_after="",
                text_after_source="",
                page_reference=None,
                last_amended=None,
                authority="NSW Planning Concepts",
                confidence=0.3
            )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Try to parse the clause reference for better matching
            parts = clause_ref.split()
            ref_type = parts[0] if len(parts) > 1 else None
            ref_number = parts[-1] if parts else clause_ref
            
            # First try exact match with type and number
            if ref_type and ref_number:
                cursor.execute("""
                    SELECT 
                        r.ref_number,
                        r.ref_type,
                        r.ref_context,
                        d.pdf_name,
                        d.full_text,
                        d.document_area
                    FROM regulatory_refs r
                    JOIN documents d ON r.document_id = d.id
                    WHERE r.ref_number = ? AND r.ref_type = ?
                      AND d.pdf_name LIKE ?
                    LIMIT 1
                """, (ref_number, ref_type, f'%{document.split()[0]}%'))
                
                result = cursor.fetchone()
                
                # If no exact match, try broader search
                if not result:
                    cursor.execute("""
                        SELECT 
                            r.ref_number,
                            r.ref_type,
                            r.ref_context,
                            d.pdf_name,
                            d.full_text,
                            d.document_area
                        FROM regulatory_refs r
                        JOIN documents d ON r.document_id = d.id
                        WHERE r.ref_number LIKE ?
                          AND d.pdf_name LIKE ?
                        ORDER BY 
                            CASE WHEN r.ref_type = ? THEN 0 ELSE 1 END,
                            LENGTH(r.ref_number)
                        LIMIT 1
                    """, (f'%{ref_number}%', f'%{document.split()[0]}%', ref_type or 'sections'))
                    
                    result = cursor.fetchone()
            else:
                # Fallback to original query
                cursor.execute("""
                    SELECT 
                        r.ref_number,
                        r.ref_type,
                        r.ref_context,
                        d.pdf_name,
                        d.full_text,
                        d.document_area
                    FROM regulatory_refs r
                    JOIN documents d ON r.document_id = d.id
                    WHERE (r.ref_number LIKE ? OR ? LIKE '%' || r.ref_number || '%')
                      AND d.pdf_name LIKE ?
                    LIMIT 1
                """, (clause_ref.split()[-1], clause_ref, f'%{document.split(" ")[0]}%'))
                
                result = cursor.fetchone()
            
            if result:
                # Extract full paragraph containing the clause
                full_text = result['full_text'] or ''
                clause_pattern = re.escape(result['ref_number'])
                
                # Find the clause and extract surrounding context
                full_paragraph, text_before, text_after, text_before_source, text_after_source = self._extract_full_paragraph(
                    full_text, clause_pattern
                )
                
                return FullCitation(
                    clause_ref=f"{result['ref_type']} {result['ref_number']}",
                    document_name=result['pdf_name'],
                    section_title=self._extract_section_title(full_paragraph),
                    full_text=full_paragraph,
                    text_before=text_before,
                    text_before_source=text_before_source,
                    text_after=text_after,
                    text_after_source=text_after_source,
                    page_reference=None,  # Could extract from document if needed
                    last_amended=None,    # Could extract from document metadata
                    authority=f"{result['document_area'].title()} Council DCP",
                    confidence=0.9 if full_paragraph else 0.6
                )
            else:
                # Return partial citation based on available information
                return FullCitation(
                    clause_ref=clause_ref,
                    document_name=document,
                    section_title="Referenced Clause",
                    full_text=excerpt,
                    text_before="",
                    text_before_source="",
                    text_after="",
                    text_after_source="", 
                    page_reference=None,
                    last_amended=None,
                    authority="NSW Planning Documents",
                    confidence=0.5
                )
    
    def _extract_full_paragraph(self, full_text: str, clause_pattern: str) -> tuple:
        """Extract full paragraph containing the clause with before/after context"""
        
        # Find clause location
        pattern = re.compile(clause_pattern, re.IGNORECASE)
        match = pattern.search(full_text)
        
        if not match:
            return full_text[:500], "", ""
        
        start_pos = match.start()
        
        # Find paragraph boundaries - look for section breaks or natural breaks
        para_start = full_text.rfind('\n\n', 0, start_pos)
        para_end = full_text.find('\n\n', start_pos)
        
        # If no clear paragraph breaks, find the start of a complete sentence
        if para_start == -1:
            # Look for sentence beginnings within a reasonable range before the target
            search_start = max(0, start_pos - 1200)
            
            # Common sentence starters in regulatory text
            sentence_starters = [
                '. The ', '. A ', '. An ', '. For ', '. In ', '. Where ', '. When ', '. If ',
                '. All ', '. Any ', '. No ', '. This ', '. That ', '. Such ', '. Each ',
                '. Development ', '. Building ', '. Construction ', '. Applications ',
                '. Council ', '. Setbacks ', '. Height ', '. Floor ', '. Site '
            ]
            
            # Look for proper sentence or section beginnings - work backwards from target
            best_start = search_start
            
            # First, try to find the most recent complete sentence start
            for i in range(start_pos - 1, search_start, -1):  # Work backwards from target
                # Check for sentence endings with proper capitalization
                if full_text[i:i+2] == '. ':
                    next_char_pos = i + 2
                    if next_char_pos < len(full_text):
                        # Check if it's followed by a capital letter (new sentence)
                        if full_text[next_char_pos].isupper():
                            # Verify it's not an abbreviation by checking common patterns
                            prev_word = full_text[max(0, i-10):i].split()[-1] if i > 10 else ""
                            if prev_word.lower() not in ['mr', 'mrs', 'dr', 'st', 'ave', 'ltd', 'etc', 'inc']:
                                best_start = next_char_pos
                                break
                
                # Check for paragraph breaks (working backwards, so check i-2 to i)
                elif i >= 2 and full_text[i-2:i] == '\n\n':
                    # Skip any leading whitespace after paragraph break  
                    next_pos = i
                    while next_pos < len(full_text) and full_text[next_pos] in [' ', '\n', '\t']:
                        next_pos += 1
                    if next_pos < len(full_text):
                        best_start = next_pos
                        break
                
                # Check for section/clause numbers at start of line (working backwards)
                elif (i > 0 and full_text[i-1] == '\n' and 
                      full_text[i:i+1].isdigit()):  # Line starting with number
                    # Look ahead to see if it's a section number pattern like "2.1.2.5"
                    section_end = i
                    while (section_end < len(full_text) and 
                           section_end < i + 20 and
                           full_text[section_end] in '0123456789.'):
                        section_end += 1
                    
                    # If followed by space and content, this is a good section start
                    if (section_end < len(full_text) and 
                        full_text[section_end] == ' ' and
                        section_end + 1 < len(full_text)):
                        best_start = i
                        break
                
                # Check for numbered lists (working backwards, so check i-3 to i)
                elif i >= 3 and full_text[i-3:i] in ['\n1.', '\n2.', '\n3.', '\n4.', '\n5.']:
                    best_start = i
                    break
                
                # Check for lettered lists (working backwards)
                elif i >= 3 and full_text[i-3:i] in ['\na)', '\nb)', '\nc)', '\nd)']:
                    best_start = i
                    break
            
            para_start = best_start
            
        if para_end == -1:
            # Look for sentence endings or section breaks within a larger range
            search_end = min(len(full_text), start_pos + 2500)  # Much larger range
            
            # Try to find a natural break point - complete sentence endings
            best_end = search_end
            
            # First try to find a complete sentence ending within reasonable range
            for i in range(start_pos + 1200, search_end):  # Start closer to target
                # Look for sentence endings that aren't abbreviations
                if full_text[i] == '.':
                    next_pos = i + 1
                    
                    # Check if it's followed by space and capital letter (new sentence)
                    if (next_pos < len(full_text) and 
                        full_text[next_pos] == ' ' and 
                        next_pos + 1 < len(full_text) and 
                        full_text[next_pos + 1].isupper()):
                        
                        # Verify it's not an abbreviation
                        prev_word = full_text[max(0, i-10):i].split()[-1] if i > 10 else ""
                        if prev_word.lower() not in ['mr', 'mrs', 'dr', 'st', 'ave', 'ltd', 'etc', 'inc', 'vs']:
                            best_end = i + 1  # Include the period
                            break
                    
                    # Also check for end of document or major section break after period
                    elif (next_pos >= len(full_text) or 
                          full_text[next_pos:next_pos+2] == '\n\n'):
                        best_end = i + 1
                        break
                        
                    # Check for period followed by line break and new section/content
                    elif (next_pos < len(full_text) and 
                          full_text[next_pos] == '\n' and
                          next_pos + 1 < len(full_text)):
                        # Look ahead for new section indicators
                        next_line_start = next_pos + 1
                        while (next_line_start < len(full_text) and 
                               full_text[next_line_start] in [' ', '\t']):
                            next_line_start += 1
                            
                        if (next_line_start < len(full_text) and
                            (full_text[next_line_start].isdigit() or  # New section number
                             full_text[next_line_start].isupper() or  # New paragraph
                             full_text[next_line_start:next_line_start+4] in ['Part', 'Sect'])):
                            best_end = i + 1
                            break
                
                # Check for numbered items starting new sections
                elif full_text[i:i+4] in ['\n1. ', '\n2. ', '\n3. ', '\n4. ', '\n5. ']:
                    best_end = i
                    break
                
                # Check for lettered list items
                elif full_text[i:i+4] in ['\na) ', '\nb) ', '\nc) ', '\nd) ']:
                    best_end = i
                    break
                    
                # Check for bullet points or dashes
                elif full_text[i:i+3] in ['\n• ', '\n- ', '\n* ']:
                    best_end = i
                    break
                
                # Check for new parts or sections
                elif (i > 0 and full_text[i-1] == '\n' and 
                      ('Part ' in full_text[i:i+8] or 'Section' in full_text[i:i+10])):
                    best_end = i
                    break
            
            para_end = best_end
            
            if para_end == -1:  # Still no break found
                # Look for any sentence ending within reasonable range
                for i in range(start_pos + 1800, search_end):
                    if full_text[i] == '.':
                        para_end = i + 1
                        break
                        
                if para_end == -1:  # Still no period found
                    # Find a word boundary before the end position
                    temp_end = search_end
                    while temp_end < len(full_text) and full_text[temp_end] not in [' ', '\n', '.']:
                        temp_end += 1
                    para_end = temp_end
        
        # Extract the main paragraph
        main_paragraph = full_text[para_start:para_end].strip()
        
        # Get context before and after, ensuring sentence boundaries
        context_start = max(0, para_start - 500)
        
        # Find sentence start in context before - look for ". [Capital]" pattern
        best_context_start = context_start
        text_segment = full_text[context_start:para_start]
        
        # Find all ". [Capital]" patterns in the text
        import re
        sentence_starts = []
        for match in re.finditer(r'\. ([A-Z])', text_segment):
            sentence_starts.append(context_start + match.start() + 2)  # +2 to skip ". "
        
        # Use the last complete sentence start found
        if sentence_starts:
            best_context_start = sentence_starts[-1]
        
        text_before = full_text[best_context_start:para_start].strip()
        
        context_end = min(len(full_text), para_end + 500)
        
        # Find sentence end in context after - look for ". [Capital]" or end of text
        text_after_segment = full_text[para_end:context_end]
        sentence_end = context_end
        
        # Find first ". [Capital]" pattern to end at complete sentence
        match = re.search(r'\. ([A-Z])', text_after_segment)
        if match:
            sentence_end = para_end + match.start() + 1  # +1 to include the period
        
        text_after = full_text[para_end:sentence_end].strip()
        
        # Extract source clause references for validation
        text_before_source = self._extract_clause_source(text_before, best_context_start)
        text_after_source = self._extract_clause_source(text_after, para_end)
        
        return main_paragraph, text_before, text_after, text_before_source, text_after_source
    
    def _extract_clause_source(self, text: str, start_position: int) -> str:
        """Extract the source clause/section number that the text belongs to"""
        if not text:
            return ""
        
        # Common patterns for section/clause references in NSW planning documents
        clause_patterns = [
            r'(\d+\.\d+\.\d+\.\d+)\s+',  # "2.1.2.5 "
            r'(\d+\.\d+\.\d+)\s+',       # "4.2.1 "  
            r'(\d+\.\d+)\s+',            # "1.7 "
            r'(\d+\.)\s+',               # "5. "
            r'Part\s+(\d+)',             # "Part 8"
            r'Section\s+(\d+\.\d+)',     # "Section 4.2"
            r'Clause\s+(\d+\.\d+)',      # "Clause 6.1"
        ]
        
        # Look for clause numbers at the start of the text
        for pattern in clause_patterns:
            match = re.match(pattern, text.strip())
            if match:
                clause_num = match.group(1)
                if 'part' in pattern.lower():
                    return f"Part {clause_num}"
                elif 'section' in pattern.lower():
                    return f"Section {clause_num}"
                elif 'clause' in pattern.lower():
                    return f"Clause {clause_num}"
                else:
                    return f"Section {clause_num}"
        
        # If no clear section at start, look for references within the text
        reference_patterns = [
            r'(?:Section|Clause)\s+(\d+\.\d+(?:\.\d+)?)',
            r'Part\s+(\d+)',
            r'(\d+\.\d+\.\d+)\s+[A-Z]',  # Section number followed by title
        ]
        
        for pattern in reference_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return "Regulatory Text"  # Generic fallback
    
    def _extract_section_title(self, text: str) -> str:
        """Extract section title from regulatory text"""
        lines = text.split('\n')
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if len(line) < 100 and any(word in line.lower() for word in ['setback', 'height', 'control', 'requirement']):
                return line
        return "Regulatory Requirement"
    
    def _extract_regulatory_values(self, citations: List[FullCitation], zone: str) -> Dict[str, Any]:
        """Extract actual numerical values from regulatory text"""
        values = {
            "setbacks": {},
            "heights": {},
            "floor_space_ratio": None,
            "site_coverage": None
        }
        
        for citation in citations:
            text = citation.full_text.lower()
            
            # Extract setback values
            setback_patterns = [
                r'front.*?(\d+(?:\.\d+)?)\s*(?:m|metres?)',
                r'side.*?(\d+(?:\.\d+)?)\s*(?:m|metres?|mm)',
                r'rear.*?(\d+(?:\.\d+)?)\s*(?:m|metres?)',
                r'setback.*?(\d+(?:\.\d+)?)\s*(?:m|metres?|mm)'
            ]
            
            for pattern in setback_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    setback_type = "setback"
                    if "front" in pattern:
                        setback_type = "front_setback"
                    elif "side" in pattern:
                        setback_type = "side_setback"
                    elif "rear" in pattern:
                        setback_type = "rear_setback"
                    
                    values["setbacks"][setback_type] = {
                        "value": matches[0],
                        "unit": "metres" if "mm" not in pattern else "mm",
                        "source": citation.clause_ref
                    }
            
            # Extract height values
            height_patterns = [
                r'height.*?(\d+(?:\.\d+)?)\s*(?:m|metres?)',
                r'(\d+(?:\.\d+)?)\s*(?:m|metres?).*?height'
            ]
            
            for pattern in height_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    values["heights"]["building_height"] = {
                        "value": matches[0],
                        "unit": "metres",
                        "source": citation.clause_ref
                    }
        
        return values
    
    def _determine_precedence(self, clause_ref: str) -> int:
        """Determine precedence order for regulatory clauses"""
        if "LEP" in clause_ref or "clause 4." in clause_ref.lower():
            return 1  # LEP clauses have highest precedence
        elif "SEPP" in clause_ref:
            return 2  # SEPP clauses
        elif "DCP" in clause_ref or "section" in clause_ref.lower():
            return 3  # DCP clauses
        else:
            return 4  # Other clauses
    
    def _assess_confidence(self, citations: List[FullCitation]) -> str:
        """Assess overall confidence in the validation"""
        avg_confidence = sum(c.confidence for c in citations) / len(citations) if citations else 0
        
        if avg_confidence >= 0.9:
            return "HIGH - All clauses verified against source documents"
        elif avg_confidence >= 0.7:
            return "MEDIUM - Most clauses verified, some inferred from context"
        else:
            return "LOW - Limited verification, manual review recommended"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for validation report"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _generate_summary(self, relationships: List[ValidatedRelationship], values: Dict) -> str:
        """Generate executive summary of regulatory requirements"""
        summary_parts = []
        
        # Count relationships by type
        compliance_rels = [r for r in relationships if "comply" in r.relationship_type]
        accordance_rels = [r for r in relationships if "accordance" in r.relationship_type]
        
        summary_parts.append(f"Found {len(relationships)} validated regulatory relationships")
        
        if compliance_rels:
            summary_parts.append(f"- {len(compliance_rels)} mandatory compliance requirements")
        
        if accordance_rels:
            summary_parts.append(f"- {len(accordance_rels)} 'in accordance with' references")
        
        # Summarize extracted values
        if values.get("setbacks"):
            summary_parts.append(f"- {len(values['setbacks'])} setback requirements identified")
        
        if values.get("heights"):
            summary_parts.append(f"- {len(values['heights'])} height controls identified")
        
        return ". ".join(summary_parts)

# Test the council validation service
if __name__ == "__main__":
    print("Testing Council Validation Service...")
    
    service = CouncilValidationService()
    report = service.generate_validation_report(
        address="34 Pile St, Dulwich Hill",
        zone="R2",
        query_terms=["setback", "height", "building"]
    )
    
    print(f"Generated report with {len(report.active_citations)} citations")
    print(f"Confidence: {report.confidence_assessment}")
    print(f"Summary: {report.regulatory_summary}")
    
    if report.active_citations:
        first_citation = report.active_citations[0]
        print(f"\nSample citation: {first_citation.clause_ref}")
        print(f"Full text: {first_citation.full_text[:200]}...")