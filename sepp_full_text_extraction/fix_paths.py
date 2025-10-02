from pathlib import Path

files = ['03_update_database_schema.py', '04_import_full_provisions.py', '05_verify_completeness.py']

for filename in files:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace path patterns
    content = content.replace('Path("docs/sepps', 'Path("../docs/sepps')
    content = content.replace('VERIFICATION_DIR = Path("docs/sepps', 'VERIFICATION_DIR = Path("../docs/sepps')

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'Fixed paths in {filename}')