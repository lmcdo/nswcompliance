import json

print("=== EXTRACTING COMPLETE CLAUSE 4.3 AND 4.4 TEXT ===")

file_path = "validated_outputs/A2_LEP_extracted_contentLEP.json"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("Found complete LEP extraction data")

    # Extract clause 4.3 components
    clause_43_parts = []
    clause_44_parts = []

    for item in data[0]:  # First document in the array
        text = item.get('text', '')

        # Clause 4.3 - Height of buildings
        if text.strip() == "4.3 Height of buildings":
            print("\n*** CLAUSE 4.3 - HEIGHT OF BUILDINGS ***")
            print("Title:", text)
            clause_43_parts.append(("title", text))
        elif "height of buildings is compatible with the character" in text:
            print("Objectives:", text)
            clause_43_parts.append(("objectives", text))
        elif "height of a building on any land is not to exceed the maximum height shown" in text:
            print("Main provision:", text)
            clause_43_parts.append(("main_provision", text))

        # Clause 4.4 - Floor space ratio
        if text.strip() == "4.4 Floor space ratio":
            print("\n*** CLAUSE 4.4 - FLOOR SPACE RATIO ***")
            print("Title:", text)
            clause_44_parts.append(("title", text))
        elif "establish a maximum floor space ratio to enable appropriate development density" in text:
            print("Objectives:", text)
            clause_44_parts.append(("objectives", text))
        elif "maximum floor space ratio for a building on any land is not to exceed the floor space ratio shown" in text:
            print("Main provision:", text)
            clause_44_parts.append(("main_provision", text))

    # Reconstruct complete clauses
    print("\n" + "="*80)
    print("COMPLETE CLAUSE 4.3 - HEIGHT OF BUILDINGS")
    print("="*80)
    for part_type, part_text in clause_43_parts:
        if part_type == "title":
            print(f"{part_text}\n")
        elif part_type == "objectives":
            print(f"(1) The objectives of this clause are as follows— {part_text}")
        elif part_type == "main_provision":
            print(f"{part_text}")

    print("\n" + "="*80)
    print("COMPLETE CLAUSE 4.4 - FLOOR SPACE RATIO")
    print("="*80)
    for part_type, part_text in clause_44_parts:
        if part_type == "title":
            print(f"{part_text}\n")
        elif part_type == "objectives":
            print(f"(1) The objectives of this clause are as follows— {part_text}")
        elif part_type == "main_provision":
            print(f"{part_text}")

    # Compare with database content
    print("\n" + "="*80)
    print("COMPARISON WITH DATABASE CONTENT")
    print("="*80)

    # Reconstruct clause 4.4 as it should be
    complete_44 = ""
    for part_type, part_text in clause_44_parts:
        if part_type == "title":
            complete_44 += f"{part_text} "
        elif part_type == "objectives":
            complete_44 += f"(1) The objectives of this clause are as follows— {part_text} "
        elif part_type == "main_provision":
            complete_44 += part_text

    print(f"Complete clause 4.4 length: {len(complete_44)} characters")
    print(f"Database truncated at: 500 characters")
    print(f"Missing text: {complete_44[500:] if len(complete_44) > 500 else 'None'}")

except Exception as e:
    print(f"Error: {e}")

print("\nExtraction completed.")