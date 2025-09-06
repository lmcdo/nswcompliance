#!/usr/bin/env python3
"""
Clause Number Cleaner - Fix PDF extraction artifacts and invalid clause numbering

Addresses CNFS-001: Systematic clause numbering errors in extracted regulatory data
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class ClauseNumberCleaner:
    """Clean and standardize clause numbers from PDF extraction artifacts"""
    
    def __init__(self):
        # PDF page number contamination patterns
        self.page_number_patterns = [
            r'\.+\s*\d+$',        # ". 5", ".. 5" 
            r'\.+\s*/\d+$',       # ". /4"
            r'\.{2,}\s*\d+$',     # ".. 5", "... 10"
            r'\s*\.\s*\d+$',      # " . 5"
        ]
        
        # Invalid clause numbering patterns  
        self.invalid_clause_patterns = {
            # 4.2.4.2 -> 4.2.4(b), 4.2.4.3 -> 4.2.4(c)
            r'^(\d+\.\d+\.\d+)\.(\d+)$': self._convert_to_subsection,
        }
        
        # Known valid clause number patterns
        self.valid_patterns = [
            r'^\d+\.\d+$',                    # 4.2
            r'^\d+\.\d+\.\d+$',              # 4.2.4  
            r'^\d+\.\d+\.\d+\([a-z]\)$',     # 4.2.4(a)
            r'^[A-Z]\d+$',                    # C1, C2 (control clauses)
        ]
    
    def _convert_to_subsection(self, match) -> str:
        """Convert 4.2.4.2 format to 4.2.4(b) format"""
        base_clause = match.group(1)  # 4.2.4
        sub_number = int(match.group(2))  # 2
        
        # Convert number to letter (1->a, 2->b, 3->c, etc.)
        if sub_number <= 26:
            sub_letter = chr(ord('a') + sub_number - 1)
            return f"{base_clause}({sub_letter})"
        else:
            # For numbers > 26, use the number in parentheses
            return f"{base_clause}({sub_number})"
    
    def clean_clause_title(self, raw_title: str) -> str:
        """Remove PDF page number artifacts from clause titles"""
        if not raw_title:
            return raw_title
            
        cleaned = raw_title.strip()
        
        # Remove PDF page number patterns
        for pattern in self.page_number_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        # Remove trailing dots and whitespace
        cleaned = re.sub(r'[\.\s]+$', '', cleaned)
        
        # Standardize internal spacing
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def standardize_clause_number(self, clause_num: str) -> str:
        """Convert invalid clause numbers to valid DCP structure"""
        if not clause_num:
            return clause_num
            
        cleaned_num = clause_num.strip()
        
        # Apply invalid pattern fixes
        for pattern, fix_func in self.invalid_clause_patterns.items():
            match = re.match(pattern, cleaned_num)
            if match:
                return fix_func(match)
        
        return cleaned_num
    
    def is_valid_clause_number(self, clause_num: str) -> bool:
        """Check if clause number follows valid DCP patterns"""
        if not clause_num:
            return False
            
        return any(re.match(pattern, clause_num.strip()) for pattern in self.valid_patterns)
    
    def process_clause_entry(self, clause_text: str) -> Dict[str, str]:
        """Process a complete clause entry and return cleaned components"""
        
        # Extract clause number and title from patterns like:
        # "Clause 4.2.4.2 - height_limit (development_control): 4.2.4.2 Building heights . 5"
        
        result = {
            'original': clause_text,
            'cleaned': clause_text,
            'clause_number': '',
            'clause_title': '',
            'issues_found': []
        }
        
        # Pattern to extract clause components
        clause_pattern = r'Clause\s+([0-9.]+)\s*-\s*(\w+)\s*\([^)]+\):\s*(.+)'
        match = re.match(clause_pattern, clause_text)
        
        if match:
            raw_number = match.group(1)  # 4.2.4.2
            control_type = match.group(2)  # height_limit
            raw_content = match.group(3)  # 4.2.4.2 Building heights . 5
            
            # Clean clause number
            clean_number = self.standardize_clause_number(raw_number)
            if clean_number != raw_number:
                result['issues_found'].append(f"Invalid clause number: {raw_number} -> {clean_number}")
            
            # Clean clause title (extract from content)
            # First remove any leading clause numbers that match the clause number pattern
            content_without_leading_number = re.sub(r'^[0-9.]+\s+', '', raw_content)
            
            # Then check for page number artifacts at the end
            title_match = re.search(r'^(.+?)\.+\s*[/]?\d+$', content_without_leading_number)
            if title_match:
                clean_title = self.clean_clause_title(title_match.group(1))
                result['issues_found'].append(f"Page number artifact removed from title")
            else:
                clean_title = self.clean_clause_title(content_without_leading_number)
            
            # Reconstruct cleaned clause entry
            result.update({
                'cleaned': f"Clause {clean_number} - {control_type}: {clean_title}",
                'clause_number': clean_number,
                'clause_title': clean_title
            })
        
        return result
    
    def process_json_file(self, file_path: Path) -> Dict:
        """Process an AutoSchemaKG JSON file and return cleanup results"""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = {
            'file_path': str(file_path),
            'original_text': data.get('text', ''),
            'cleaned_entries': [],
            'total_issues': 0
        }
        
        # Process each line in the text
        lines = data.get('text', '').split('\n')
        cleaned_lines = []
        
        for line in lines:
            if line.strip().startswith('Clause'):
                processed = self.process_clause_entry(line.strip())
                cleaned_lines.append(processed['cleaned'])
                results['cleaned_entries'].append(processed)
                results['total_issues'] += len(processed['issues_found'])
            else:
                cleaned_lines.append(line)
        
        # Update the data with cleaned text
        data['text'] = '\n'.join(cleaned_lines)
        results['cleaned_data'] = data
        
        return results

def main():
    """Main function for testing clause number cleaner"""
    cleaner = ClauseNumberCleaner()
    
    # Test cases from the user's reported issue
    test_cases = [
        "Clause 4.2.4.2 - height_limit (development_control): 4.2.4.2 Building heights . 5",
        "Clause 4.2.4.3 - setback (development_control): 4.2.4.3 Building setbacks.. 5", 
        "Clause 4.2.4.1 - fsr_control (development_control): 4.2.4.1 Floor space ratio and site coverage . /4",
    ]
    
    print("Testing Clause Number Cleaner")
    print("=" * 60)
    
    for test_case in test_cases:
        print(f"\nOriginal: {test_case}")
        result = cleaner.process_clause_entry(test_case)
        print(f"Cleaned:  {result['cleaned']}")
        print(f"Number:   {result['clause_number']}")
        print(f"Title:    {result['clause_title']}")
        print(f"Issues:   {', '.join(result['issues_found'])}")
        print(f"Valid:    {cleaner.is_valid_clause_number(result['clause_number'])}")

if __name__ == "__main__":
    main()