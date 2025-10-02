"""Fix Unicode characters in all scripts"""
from pathlib import Path

scripts = [
    '02_parse_markdown_to_json.py',
    '03_update_database_schema.py',
    '04_import_full_provisions.py',
    '05_verify_completeness.py',
    'run_all.py'
]

for script in scripts:
    script_path = Path(script)
    if not script_path.exists():
        print(f"Skip: {script} (not found)")
        continue

    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace all Unicode symbols
    replacements = [
        ('✓', '[OK]'),
        ('✗', '[X]'),
        ('⚠', '[!]'),
        ('✅', '[SUCCESS]'),
        ('❌', '[FAIL]'),
        ('🔴', '[RED]'),
        ('🟡', '[YELLOW]'),
        ('🟢', '[GREEN]'),
    ]

    for old, new in replacements:
        content = content.replace(old, new)

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Fixed: {script}")

print("\nAll scripts fixed!")