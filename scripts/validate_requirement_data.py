#!/usr/bin/env python3
"""Validate SEPP requirement_data JSON."""

import sys
import json
import re


class RequirementDataValidator:
    COST_PATTERNS = [r'\$[\d,]+', r'\d+k', r'cost.*\d+']
    TIMELINE_PATTERNS = [r'\d+[-–]\d+\s*(weeks?|months?|days?)', r'\d+\s*(weeks?|months?|days?)']
    R2_URL_PATTERN = r'^https://pub-[a-f0-9]+\.r2\.dev/'

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate(self, data: dict):
        self.errors = []
        self.warnings = []
        self._check_required_fields(data)
        if 'categories' in data:
            self._validate_categories(data['categories'])
        if 'pdf_references' in data:
            self._validate_pdf_references(data['pdf_references'])
        if 'feasibility_note' in data:
            self._validate_feasibility_note(data['feasibility_note'])
        return len(self.errors) == 0, self.errors, self.warnings

    def _check_required_fields(self, data):
        for field in ['title', 'categories']:
            if field not in data or not data[field]:
                self.errors.append(f"Missing or empty: {field}")

    def _validate_categories(self, categories):
        if not isinstance(categories, list) or len(categories) == 0:
            self.errors.append("categories must be non-empty array")
            return
        for i, cat in enumerate(categories):
            path = f"categories[{i}]"
            for field in ['name', 'reference', 'requirements']:
                if field not in cat:
                    self.errors.append(f"{path}: Missing {field}")
            if 'requirements' in cat:
                if not isinstance(cat['requirements'], list) or len(cat['requirements']) == 0:
                    self.errors.append(f"{path}.requirements must be non-empty array")
                else:
                    for j, req in enumerate(cat['requirements']):
                        self._check_brand_safety(req, f"{path}.requirements[{j}]")

    def _check_brand_safety(self, req, path):
        req_str = json.dumps(req, ensure_ascii=False).lower()
        for pattern in self.COST_PATTERNS:
            if re.search(pattern, req_str, re.IGNORECASE):
                self.errors.append(f"BRAND SAFETY: {path} has cost estimate")
                break
        for pattern in self.TIMELINE_PATTERNS:
            if re.search(pattern, req_str, re.IGNORECASE):
                self.errors.append(f"BRAND SAFETY: {path} has timeline estimate")
                break

    def _validate_pdf_references(self, refs):
        if not isinstance(refs, list):
            self.errors.append("pdf_references must be array")
            return
        for i, ref in enumerate(refs):
            path = f"pdf_references[{i}]"
            for field in ['page', 'section', 'description', 'url']:
                if field not in ref:
                    self.errors.append(f"{path}: Missing {field}")
            if 'url' in ref and not re.match(self.R2_URL_PATTERN, ref['url']):
                self.errors.append(f"{path}.url must be absolute R2 URL")
        if len(refs) > 1:
            pages = [ref.get('page', 0) for ref in refs]
            if pages != sorted(pages):
                self.warnings.append(f"pdf_references not sorted by page")

    def _validate_feasibility_note(self, note):
        if not isinstance(note, dict):
            self.errors.append("feasibility_note must be object")
            return
        for field in ['heading', 'content', 'resources']:
            if field not in note:
                self.errors.append(f"feasibility_note: Missing {field}")
        if 'resources' in note and isinstance(note['resources'], list):
            for i, res in enumerate(note['resources']):
                path = f"feasibility_note.resources[{i}]"
                for field in ['label', 'url', 'description']:
                    if field not in res:
                        self.errors.append(f"{path}: Missing {field}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_requirement_data.py data.json")
        sys.exit(1)

    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    validator = RequirementDataValidator()
    is_valid, errors, warnings = validator.validate(data)

    print(f"\nValidating: {sys.argv[1]}")
    print("=" * 60)

    if errors:
        print(f"\nERROR ERRORS ({len(errors)}):")
        for error in errors:
            print(f"  • {error}")

    if warnings:
        print(f"\nWARNING WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  • {warning}")

    if is_valid and not warnings:
        print("\nOK Validation passed!")
    elif is_valid:
        print(f"\nOK Passed with {len(warnings)} warnings")
    else:
        print(f"\nERROR Failed with {len(errors)} errors")

    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
