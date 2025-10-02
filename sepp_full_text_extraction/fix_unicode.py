import re

with open('01_extract_sepps_mineru.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all checkmarks and x marks
content = content.replace('✓', '[OK]')
content = content.replace('✗', '[X]')
content = content.replace('⚠', '[!]')
content = content.replace('✅', '[SUCCESS]')

with open('01_extract_sepps_mineru.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Unicode characters replaced in 01_extract_sepps_mineru.py')