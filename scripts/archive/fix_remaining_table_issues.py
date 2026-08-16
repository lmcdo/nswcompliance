#!/usr/bin/env python3
"""
Fix remaining table display issues for specific provisions.
These are tables where Camelot extracted the data but without proper headers or structure.
"""

import os
import sys
import psycopg2
import re
from pathlib import Path

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}


def clean_latex_formatting(text):
    """
    Convert LaTeX math notation to plain text

    Examples:
    $5.4 \\mathsf{m}$ → 5.4 m
    $_{2.4 \\mathrm{~m~}}$ → 2.4 m
    ${500} \\mathsf{m}$ → 500 m
    $200 \\mathsf{m}^{2}$ → 200 m²
    """

    # Pattern: $...content...$
    # Extract the numeric value and unit

    def replace_math(match):
        content = match.group(1)

        # Remove LaTeX commands
        content = re.sub(r'\\mathsf\s*\{([^}]+)\}', r'\1', content)
        content = re.sub(r'\\mathrm\s*\{([^}]+)\}', r'\1', content)
        content = re.sub(r'\\textrm\s*\{([^}]+)\}', r'\1', content)
        content = re.sub(r'\\scriptstyle\s+', '', content)

        # Remove subscript/superscript markers
        content = re.sub(r'[_^]\s*\{([^}]+)\}', r'\1', content)
        content = re.sub(r'[_^]([a-zA-Z0-9])', r'\1', content)

        # Clean up spacing markers
        content = content.replace('~', ' ')
        content = content.replace(r'\,', '')
        content = content.replace(r'\:', ' ')

        # Remove extra spaces and commas
        content = re.sub(r'\s*,\s*', '', content)
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()

        return content

    # Replace all $...$ patterns
    text = re.sub(r'\$([^$]+)\$', replace_math, text)

    return text


def fix_latex_in_database():
    """Clean LaTeX formatting from all provisions"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Find provisions with LaTeX
    query = """
        SELECT id, provision_text
        FROM regulatory_provisions
        WHERE provision_text ~ '\\$.*\\\\math'
        ORDER BY id;
    """

    cur.execute(query)
    provisions = cur.fetchall()

    print(f"Found {len(provisions)} provisions with LaTeX formatting")
    print()

    fixed_count = 0
    for prov_id, text in provisions:
        # Clean LaTeX
        cleaned = clean_latex_formatting(text)

        if cleaned != text:
            # Update database
            update_query = """
                UPDATE regulatory_provisions
                SET provision_text = %s
                WHERE id = %s;
            """
            cur.execute(update_query, (cleaned, prov_id))
            fixed_count += 1

            if fixed_count % 100 == 0:
                print(f"  Cleaned {fixed_count} provisions...")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nSuccessfully cleaned {fixed_count} provisions")
    return fixed_count


def fix_parking_table(conn, provision_id: int):
    """Fix parking rate tables - add proper headers: Land Use | Parking Rate | Notes"""
    cur = conn.cursor()
    cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = %s", (provision_id,))
    result = cur.fetchone()
    if not result:
        return False

    text = result[0]

    # Check if it's a headerless 3-column parking table
    if ('<tr> <td></td> <td></td> <td>' in text or '<tr> <td>Place of Worship' in text):
        # Add proper header row
        fixed_text = text.replace(
            '<table> <tbody>',
            '<table><thead><tr><th>Land Use</th><th>Parking Rate</th><th>Notes</th></tr></thead><tbody>'
        )

        # Remove empty first row if present
        fixed_text = re.sub(r'<tr>\s*<td></td>\s*<td></td>\s*<td>[^<]*</td>\s*</tr>', '', fixed_text)

        cur.execute(
            "UPDATE regulatory_provisions SET provision_text = %s WHERE id = %s",
            (fixed_text, provision_id)
        )
        print(f"[OK] Fixed parking table {provision_id}")
        cur.close()
        return True

    cur.close()
    return False


def fix_pc_ds_table(conn, provision_id: int):
    """Fix Performance Criteria / Design Solution tables - ensure proper header structure"""
    cur = conn.cursor()
    cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = %s", (provision_id,))
    result = cur.fetchone()
    if not result:
        return False

    text = result[0]

    # Check if it's a 4-column PC/DS table with improper headers
    if 'Performance Criteria' in text and 'Design Solution' in text:
        # Check if header row spans incorrectly
        if '<td colspan="2"> Performance Criteria</td><td colspan="2"> Design Solution</td>' in text:
            # Fix: Change to proper 4-column header
            fixed_text = text.replace(
                '<td colspan="2"> Performance Criteria</td><td colspan="2"> Design Solution</td>',
                '<th>PC#</th><th>Performance Criteria</th><th>DS#</th><th>Design Solution</th>'
            )

            # Wrap header in thead
            fixed_text = fixed_text.replace('<table><tr>', '<table><thead><tr>')
            fixed_text = fixed_text.replace('</th></tr>', '</th></tr></thead><tbody>', 1)
            fixed_text = fixed_text.replace('</tbody> </table>', '</tbody></table>')

            cur.execute(
                "UPDATE regulatory_provisions SET provision_text = %s WHERE id = %s",
                (fixed_text, provision_id)
            )
            print(f"[OK] Fixed PC/DS table {provision_id}")
            cur.close()
            return True

    # Check if PC and DS are merged in 2-column format (PC9.1 ... DS9.1 ...)
    if re.search(r'PC\d+\.\d+', text) and re.search(r'DS\d+\.\d+', text):
        # Split merged PC/DS cells into 4 columns
        def split_pc_ds_row(match):
            full_row = match.group(0)
            # Extract PC cell and DS cell
            cells = re.findall(r'<td>(.*?)</td>', full_row, re.DOTALL)
            if len(cells) >= 2:
                pc_cell = cells[0].strip()
                ds_cell = cells[1].strip()

                # Extract PC# and text
                pc_match = re.match(r'(PC\d+\.\d+)\s+(.*)', pc_cell, re.DOTALL)
                # Extract DS# and text
                ds_match = re.match(r'(DS\d+\.\d+)\s+(.*)', ds_cell, re.DOTALL)

                if pc_match and ds_match:
                    pc_num, pc_text = pc_match.groups()
                    ds_num, ds_text = ds_match.groups()
                    return f'<tr><td>{pc_num}</td><td>{pc_text}</td><td>{ds_num}</td><td>{ds_text}</td></tr>'
                elif pc_match and not ds_match:
                    # Only PC in first cell, full DS text in second
                    pc_num, pc_text = pc_match.groups()
                    ds_match_full = re.match(r'(DS\d+\.\d+)\s+(.*)', ds_cell, re.DOTALL)
                    if ds_match_full:
                        ds_num, ds_text = ds_match_full.groups()
                        return f'<tr><td>{pc_num}</td><td>{pc_text}</td><td>{ds_num}</td><td>{ds_text}</td></tr>'
            return full_row

        fixed_text = re.sub(
            r'<tr>\s*<td>.*?PC\d+\.\d+.*?</td>\s*<td>.*?DS\d+\.\d+.*?</td>\s*</tr>',
            split_pc_ds_row,
            text,
            flags=re.DOTALL
        )

        if fixed_text != text:
            # Add proper header
            fixed_text = fixed_text.replace(
                '<table> <tbody>',
                '<table><thead><tr><th>PC#</th><th>Performance Criteria</th><th>DS#</th><th>Design Solution</th></tr></thead><tbody>'
            )

            cur.execute(
                "UPDATE regulatory_provisions SET provision_text = %s WHERE id = %s",
                (fixed_text, provision_id)
            )
            print(f"[OK] Fixed merged PC/DS table {provision_id}")
            cur.close()
            return True

    cur.close()
    return False


def main():
    print("=" * 70)
    print("Fix Remaining Table Structure Issues")
    print("=" * 70)
    print()

    conn = psycopg2.connect(**DB_CONFIG)

    # Problem provisions identified by user
    problem_provisions = [
        58312,  # Parking table - missing headers (page 66)
        58320,  # PC/DS table - wrong header structure (page 75)
        59067,  # PC/DS table - merged cells (page 142)
    ]

    print(f"Fixing {len(problem_provisions)} problematic tables...")
    print()

    fixed_count = 0
    for prov_id in problem_provisions:
        if fix_parking_table(conn, prov_id):
            fixed_count += 1
        elif fix_pc_ds_table(conn, prov_id):
            fixed_count += 1
        else:
            print(f"[WARN] Table {prov_id} needs manual review")

    conn.commit()
    conn.close()

    print()
    print("=" * 70)
    print(f"[DONE] Fixed {fixed_count}/{len(problem_provisions)} table structure issues")
    print("=" * 70)


if __name__ == "__main__":
    main()
