#!/usr/bin/env python3
"""Test markdown table generation for provision 8957"""

import json
from pathlib import Path
from bs4 import BeautifulSoup
from db_safety_wrapper import get_safe_connection

# Read the table from JSON
json_path = Path('output/Marrickville DCP 2011 - 4.1 Low Density Residential Development/auto/Marrickville DCP 2011 - 4.1 Low Density Residential Development_content_list.json')
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

tables = [item for item in data if item.get('type') == 'table']
table_html = tables[0]['table_body']

print("ORIGINAL HTML:")
print(table_html[:500])
print("\n" + "="*80 + "\n")

# Parse with new logic
soup = BeautifulSoup(table_html, 'html.parser')
table = soup.find('table')
rows = table.find_all('tr')

# Extract header
header_cells = rows[0].find_all(['td', 'th'])
header_text = ' '.join([cell.get_text(strip=True) for cell in header_cells])

# Build markdown table
markdown_rows = []
rowspan_tracker = {}

for row_idx, row in enumerate(rows):
    cells = row.find_all(['td', 'th'])
    current_row = []
    cell_idx = 0
    col_position = 0

    while cell_idx < len(cells) or col_position in rowspan_tracker:
        if col_position in rowspan_tracker:
            value, remaining = rowspan_tracker[col_position]
            current_row.append(value)
            if remaining > 1:
                rowspan_tracker[col_position] = (value, remaining - 1)
            else:
                del rowspan_tracker[col_position]
            col_position += 1
        elif cell_idx < len(cells):
            cell = cells[cell_idx]
            cell_text = cell.get_text(strip=True)
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))

            current_row.append(cell_text)
            if rowspan > 1:
                rowspan_tracker[col_position] = (cell_text, rowspan - 1)
            col_position += 1

            for _ in range(colspan - 1):
                current_row.append('')
                col_position += 1

            cell_idx += 1
        else:
            break

    markdown_rows.append(current_row)
    print(f"Row {row_idx}: {current_row}")

# Build output
output_lines = []
output_lines.append(f'**{header_text}**\n')
num_cols = len(markdown_rows[0])
output_lines.append('| ' + ' | '.join(markdown_rows[0]) + ' |')
output_lines.append('| ' + ' | '.join(['---'] * num_cols) + ' |')
for row in markdown_rows[1:]:
    while len(row) < num_cols:
        row.append('')
    output_lines.append('| ' + ' | '.join(row[:num_cols]) + ' |')

result = '\n'.join(output_lines)
print("\n" + "="*80)
print("MARKDOWN TABLE:")
print(result)
print("="*80 + "\n")

# Update database
print('Updating database...')
conn = get_safe_connection()
cursor = conn.cursor()
cursor.execute('UPDATE regulatory_provisions SET provision_text = %s WHERE id = 8957', (result,))
conn.commit()
print('Updated provision 8957')
cursor.close()
conn.close()
