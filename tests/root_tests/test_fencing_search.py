import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

# Find fencing document
cursor.execute("SELECT pdf_name FROM documents WHERE pdf_name LIKE '%Fencing%'")
result = cursor.fetchone()
print(f"Fencing document: {result[0] if result else 'Not found'}")

if result:
    cursor.execute("SELECT full_text FROM documents WHERE pdf_name = ?", (result[0],))
    text = cursor.fetchone()[0]
    
    # Search for "High solid" 
    pos = text.find('High solid')
    if pos >= 0:
        print(f'Found "High solid" at position {pos}')
        section = text[max(0, pos-200):pos+300]
        print(f'Context:\n{section}')
        
        # Look for clause numbers near this text
        before_text = text[max(0, pos-1000):pos]
        after_text = text[pos:pos+1000]
        
        import re
        clauses_before = re.findall(r'[C]\d+', before_text)
        clauses_after = re.findall(r'[C]\d+', after_text) 
        
        print(f"\nClauses before: {clauses_before[-3:] if clauses_before else 'None'}")
        print(f"Clauses after: {clauses_after[:3] if clauses_after else 'None'}")
        
    else:
        print('"High solid" not found')
        
        # Try searching for variations
        variations = ['High front', 'solid walls', 'solid fences']
        for variant in variations:
            if variant in text:
                pos = text.find(variant)
                section = text[max(0, pos-100):pos+200]
                print(f'\nFound "{variant}" at position {pos}:')
                print(section)
                break

conn.close()