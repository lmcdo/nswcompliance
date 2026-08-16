"""
Re-extract Marrickville heritage provision text from PDF page images stored on Cloudflare R2

Uses Claude vision API to extract CORRECT provision text from each page,
fixing the systemic extraction error where section headers/intro text was
grabbed instead of actual control text.

Process:
1. Query Marrickville heritage provisions (TEST MODE: 10 provisions)
2. For each provision with a PDF page image:
   - Fetch PNG image from Cloudflare R2
   - Use Claude vision to extract the specific provision text
   - Update provision_text in database (with confirmation)
3. Track successes/failures

CRITICAL: Extract ONLY the provision control text, NOT:
- Section headers (e.g., "8.1.7 Heritage Items")
- Page headers (e.g., "PART 8: HERITAGE")
- Intro paragraphs (e.g., "Heritage items are listed in Schedule 5...")
- General controls that apply to all development
"""

import os
import sys
import base64
import requests
import anthropic
from supabase import create_client

# Setup
os.environ['SUPABASE_URL'] = 'https://egaxshyzelmkevunrfdl.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVnYXhzaHl6ZWxta2V2dW5yZmRsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNTcwMjU0MCwiZXhwIjoyMDUxMjc4NTQwfQ.s3st62Sq5CtUwJkLs5xUuSnJkc4Y9ykhVyhp6c8vtvw'

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
anthropic_client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

# Cloudflare R2 public URL
R2_PUBLIC_URL = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev'

# TEST MODE: Only process 10 provisions
TEST_MODE = True
TEST_LIMIT = 10

print("=" * 100)
print("MARRICKVILLE HERITAGE PROVISION RE-EXTRACTION")
if TEST_MODE:
    print(f"*** TEST MODE: Processing only {TEST_LIMIT} provisions ***")
print("=" * 100)
print()

# Get Marrickville heritage provisions with images
query = sb.table('regulatory_provisions').select(
    'id, pdf_page, pdf_page_image_url, v2_heritage_element, v2_heritage_type, provision_text'
).ilike('document_id', '%Marrickville%').eq('v2_marker', 'heritage').not_.is_('pdf_page_image_url', 'null').order('id')

if TEST_MODE:
    query = query.limit(TEST_LIMIT)

result = query.execute()
provisions = result.data
print(f"Found {len(provisions)} Marrickville heritage provisions with PDF images")
print()

if not TEST_MODE:
    # Confirm before proceeding (skip in test mode)
    print("⚠️  WARNING: This will UPDATE provision_text for all provisions.")
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        sys.exit(0)
else:
    print("ℹ️  Test mode: Will show extraction results WITHOUT updating database")
    print("   Set TEST_MODE = False to actually update provisions")
    print()

print()
print("Starting re-extraction...")
print()

success_count = 0
error_count = 0
skipped_count = 0

for i, prov in enumerate(provisions, 1):
    prov_id = prov['id']
    image_url = prov['pdf_page_image_url']
    elements = prov.get('v2_heritage_element', []) or []
    heritage_type = prov.get('v2_heritage_type', 'unknown')

    print(f"\n[{i}/{len(provisions)}] Processing ID {prov_id} (Page {prov['pdf_page']})")
    print(f"   Elements: {elements}")
    print(f"   Type: {heritage_type}")

    # Construct full R2 URL
    # URL format: /pdf-pages/marr_Marrickville_DCP_2011_-_8.0_Heritage_page_20.png
    # Full URL: https://pub-...r2.dev/pdf-pages/marr_...png
    full_image_url = f"{R2_PUBLIC_URL}{image_url}"
    print(f"   Fetching: {full_image_url[:80]}...")

    # Fetch image from R2
    try:
        response = requests.get(full_image_url, timeout=30)
        response.raise_for_status()
        image_data = base64.standard_b64encode(response.content).decode('utf-8')
    except Exception as e:
        print(f"   ❌ Failed to fetch image: {e}")
        error_count += 1
        continue

    # Extract text using Claude vision
    try:
        # Create targeted prompt based on heritage elements
        element_context = ', '.join(elements) if elements else 'heritage'

        prompt = f"""Extract the SPECIFIC heritage provision control text from this DCP page.

CONTEXT: This provision relates to {element_context} in heritage areas/items.

CRITICAL RULES:
1. Extract ONLY the provision control text - NOT section headers, page headers, or intro paragraphs
2. DO NOT extract:
   - Section headers like "8.1.7 Heritage Items"
   - Page headers like "PART 8: HERITAGE"
   - Intro text like "Heritage items are listed in Schedule 5..."
   - Generic controls that apply to "all development"
3. DO extract:
   - Specific controls related to {element_context}
   - Provisions with "C" numbers (C1, C2, etc.) or subsection numbers (8.1.7.3, etc.)
   - Text that gives specific requirements for {element_context}

If this page contains MULTIPLE provisions related to {element_context}, extract ALL of them separated by double newlines.

If this page contains NO specific controls (only intro/header text), respond with: "NO_SPECIFIC_PROVISION_ON_PAGE"

Output the extracted provision text ONLY, with no commentary."""

        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )

        extracted_text = message.content[0].text.strip()

        if extracted_text == "NO_SPECIFIC_PROVISION_ON_PAGE":
            print(f"   ⚠️  No specific provision found on page")
            if not TEST_MODE:
                # Update to mark as descriptive/non-actionable
                sb.table('regulatory_provisions').update({
                    'v2_is_actionable': False,
                    'v2_heritage_type': 'descriptive'
                }).eq('id', prov_id).execute()
                print(f"      → Marked as descriptive in database")
            skipped_count += 1
        else:
            print(f"   ✅ Extracted {len(extracted_text)} chars")
            print(f"   Preview: {extracted_text[:200]}...")

            if not TEST_MODE:
                # Update provision_text
                sb.table('regulatory_provisions').update({
                    'provision_text': extracted_text
                }).eq('id', prov_id).execute()
                print(f"      → Updated in database")
            else:
                print(f"      → [TEST MODE: Not updating database]")

            success_count += 1

    except Exception as e:
        print(f"   ❌ Error: {e}")
        error_count += 1

    # Progress update every 50
    if i % 50 == 0:
        print(f"\n--- Progress: {i}/{len(provisions)} processed ---")
        print(f"    Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}\n")

# Final summary
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print(f"Total processed: {len(provisions)}")
print(f"Successfully updated: {success_count}")
print(f"Skipped (no specific provision): {skipped_count}")
print(f"Errors: {error_count}")
print()
print("✅ Re-extraction complete!")
