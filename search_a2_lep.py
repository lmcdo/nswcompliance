import json
import re

print("=== SEARCHING A2_LEP_EXTRACTED_CONTENT FOR CLAUSE 4.3 AND 4.4 ===")

file_path = "validated_outputs/A2_LEP_extracted_contentLEP.json"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"File loaded successfully. Type: {type(data)}")

    if isinstance(data, dict):
        print(f"Top-level keys: {list(data.keys())}")
    elif isinstance(data, list):
        print(f"List with {len(data)} items")

    # Search for clause 4.3 and 4.4 in various ways
    clauses_found = []

    def search_recursive(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key

                # Check if this entry relates to clause 4.3 or 4.4
                if (isinstance(key, str) and
                    ('4.3' in key or '4.4' in key or
                     'floor space' in key.lower() or
                     'height' in key.lower())):

                    clauses_found.append({
                        'path': new_path,
                        'key': key,
                        'value': value,
                        'type': type(value).__name__
                    })

                # Check if value contains clause references
                if isinstance(value, str):
                    if ('4.3' in value or '4.4' in value or
                        'floor space ratio' in value.lower() or
                        'height of buildings' in value.lower()):

                        clauses_found.append({
                            'path': new_path,
                            'key': key,
                            'value': value[:500] + ('...' if len(value) > 500 else ''),
                            'full_length': len(value),
                            'type': 'text_content'
                        })

                search_recursive(value, new_path)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search_recursive(item, f"{path}[{i}]")

    search_recursive(data)

    print(f"\n=== FOUND {len(clauses_found)} REFERENCES TO CLAUSE 4.3/4.4 ===")

    for i, clause in enumerate(clauses_found):
        print(f"\n--- Reference {i+1} ---")
        print(f"Path: {clause['path']}")
        print(f"Key: {clause['key']}")
        print(f"Type: {clause['type']}")
        if 'full_length' in clause:
            print(f"Text length: {clause['full_length']} characters")
        print(f"Value: {clause['value']}")
        print("-" * 80)

except Exception as e:
    print(f"Error reading file: {e}")

print("\nSearch completed.")