"""
Week 2: Process Precinct Provisions with LLM Categorization
Goal: Extract structured requirements from 47 precinct documents
Output: Categorized requirements in dcp_precinct_requirements table
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from db_safety_wrapper import get_safe_connection
from openai import OpenAI

load_dotenv()

# Configure OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Categorization prompt template
CATEGORIZATION_PROMPT = """You are a planning regulation expert. Analyze the following precinct provisions and extract structured requirements.

Precinct: {precinct_name}
LGA: {lga}

Provisions:
{provisions_text}

Extract requirements and categorize them into these categories:
- setback_front: Front setback requirements
- setback_side: Side setback requirements
- setback_rear: Rear setback requirements
- parking: Parking requirements
- landscaping: Landscaping/garden requirements
- building_height: Height/storey requirements
- site_coverage: Site coverage requirements
- character: Character/heritage requirements
- privacy: Privacy/overlooking requirements
- fencing: Fence requirements
- other: Any other requirements

For each requirement, extract:
1. category: One of the categories above
2. subcategory: Optional sub-classification
3. requirement_text: Clear, concise statement (e.g., "Front setback: 5.5m")
4. value_numeric: Numeric value if applicable (e.g., 5.5)
5. unit: Unit of measurement if applicable (e.g., "m", "%", "spaces")
6. has_conditionals: true if the requirement contains "except", "however", "unless", "where"
7. conditional_text: The conditional clause if present
8. confidence: "high", "medium", or "low" based on clarity
9. reasoning: Brief explanation of why you categorized it this way

Return ONLY a JSON array of requirements. Example:
[
  {{
    "category": "setback_front",
    "subcategory": null,
    "requirement_text": "Minimum front setback: 5.5m",
    "value_numeric": 5.5,
    "unit": "m",
    "has_conditionals": false,
    "conditional_text": null,
    "confidence": "high",
    "reasoning": "Clear numeric setback requirement for front boundary"
  }}
]

Return empty array [] if no clear requirements found.
"""

class PrecinctProcessor:
    def __init__(self):
        self.conn = None
        self.processed_count = 0
        self.failed_count = 0
        self.total_requirements = 0

    def connect_db(self):
        """Connect to database using safe wrapper"""
        self.conn = get_safe_connection(
            host=os.getenv('PGHOST'),
            database=os.getenv('PGDATABASE'),
            user=os.getenv('PGUSER'),
            port=int(os.getenv('PGPORT', 5432))
        )
        self.conn.connect()

    def get_precincts_to_process(self):
        """Get all precincts that need processing"""
        cur = self.conn.cursor()

        # Get all precincts from dcp_precinct_provisions
        cur.execute("""
            SELECT DISTINCT
                precinct_id,
                precinct_name,
                lga,
                COUNT(*) as provision_count
            FROM dcp_precinct_provisions
            GROUP BY precinct_id, precinct_name, lga
            ORDER BY lga, precinct_name
        """)

        precincts = cur.fetchall()
        print(f"\nFound {len(precincts)} precincts to process:")
        for precinct_id, precinct_name, lga, count in precincts[:10]:
            print(f"  {lga}: {precinct_name} ({count} provisions)")
        if len(precincts) > 10:
            print(f"  ... and {len(precincts) - 10} more")

        return precincts

    def get_precinct_provisions(self, precinct_id):
        """Get all provisions for a specific precinct"""
        cur = self.conn.cursor()

        cur.execute("""
            SELECT
                id,
                provision_text,
                parent_provision_id
            FROM dcp_precinct_provisions
            WHERE precinct_id = %s
            ORDER BY id
        """, (precinct_id,))

        provisions = cur.fetchall()
        return provisions

    def call_llm_categorization(self, precinct_name, lga, provisions_text):
        """Call OpenAI to categorize provisions"""
        try:
            prompt = CATEGORIZATION_PROMPT.format(
                precinct_name=precinct_name,
                lga=lga,
                provisions_text=provisions_text
            )

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a planning regulation expert who extracts structured requirements from regulatory text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=4000
            )

            # Parse response
            content = response.choices[0].message.content.strip()

            # Try to extract JSON from response
            if content.startswith('['):
                requirements = json.loads(content)
            else:
                # Try to find JSON in the response
                start = content.find('[')
                end = content.rfind(']') + 1
                if start != -1 and end > start:
                    requirements = json.loads(content[start:end])
                else:
                    print(f"  WARNING: Could not parse JSON from response")
                    return []

            return requirements

        except Exception as e:
            print(f"  ERROR: LLM call failed: {str(e)}")
            return None

    def store_requirements(self, precinct_id, precinct_name, lga, requirements, source_provision_ids, document_id):
        """Store extracted requirements in database"""
        cur = self.conn.cursor()

        stored_count = 0
        for req in requirements:
            try:
                cur.execute("""
                    INSERT INTO dcp_precinct_requirements (
                        precinct_id,
                        precinct_name,
                        lga,
                        category,
                        subcategory,
                        requirement_text,
                        value_numeric,
                        unit,
                        source_provision_ids,
                        source_document_ids,
                        extraction_context,
                        confidence,
                        has_conditionals,
                        conditional_text,
                        validated,
                        processing_version
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (precinct_id, category, subcategory, requirement_text) DO NOTHING
                """, (
                    precinct_id,
                    precinct_name,
                    lga,
                    req.get('category'),
                    req.get('subcategory'),
                    req.get('requirement_text'),
                    req.get('value_numeric'),
                    req.get('unit'),
                    source_provision_ids,
                    [document_id],
                    json.dumps({'reasoning': req.get('reasoning')}),
                    req.get('confidence', 'medium'),
                    req.get('has_conditionals', False),
                    req.get('conditional_text'),
                    False,  # Not validated yet
                    'week2_v1'
                ))
                stored_count += 1
            except Exception as e:
                print(f"  WARNING: Failed to store requirement: {str(e)}")
                continue

        self.conn.commit()
        return stored_count

    def process_precinct(self, precinct_id, precinct_name, lga):
        """Process a single precinct"""
        print(f"\nProcessing: {precinct_name} ({lga})")

        # Get provisions
        provisions = self.get_precinct_provisions(precinct_id)
        print(f"  Provisions: {len(provisions)}")

        if not provisions:
            print("  SKIP: No provisions found")
            return False

        # Combine provision texts
        provisions_text = "\n\n".join([
            f"[{i+1}] {prov[1]}"
            for i, prov in enumerate(provisions)
        ])

        # Truncate if too long (GPT-4o-mini has token limits)
        if len(provisions_text) > 10000:
            provisions_text = provisions_text[:10000] + "\n... (truncated)"
            print(f"  NOTE: Provisions text truncated to 10000 chars")

        # Call LLM
        print(f"  Calling LLM for categorization...")
        requirements = self.call_llm_categorization(precinct_name, lga, provisions_text)

        if requirements is None:
            print(f"  FAILED: LLM call failed")
            self.failed_count += 1
            return False

        if not requirements:
            print(f"  RESULT: No requirements extracted")
            self.processed_count += 1
            return True

        print(f"  RESULT: Extracted {len(requirements)} requirements")

        # Get document_id from first provision
        cur = self.conn.cursor()
        cur.execute("""
            SELECT document_id
            FROM dcp_precinct_provisions
            WHERE precinct_id = %s
            LIMIT 1
        """, (precinct_id,))
        document_id = cur.fetchone()[0]

        # Store requirements
        source_provision_ids = [prov[0] for prov in provisions]
        stored_count = self.store_requirements(
            precinct_id,
            precinct_name,
            lga,
            requirements,
            source_provision_ids,
            document_id
        )

        print(f"  STORED: {stored_count} requirements")
        self.total_requirements += stored_count
        self.processed_count += 1
        return True

    def run(self, limit=None):
        """Run the full processing pipeline"""
        print("=" * 80)
        print("WEEK 2: PRECINCT PROVISIONS PROCESSING")
        print("=" * 80)

        # Connect to database
        print("\nConnecting to database...")
        self.connect_db()

        # Get precincts
        precincts = self.get_precincts_to_process()

        if limit:
            precincts = precincts[:limit]
            print(f"\nLIMIT: Processing first {limit} precincts only")

        # Process each precinct
        print(f"\nProcessing {len(precincts)} precincts...")
        print("=" * 80)

        for precinct_id, precinct_name, lga, provision_count in precincts:
            try:
                self.process_precinct(precinct_id, precinct_name, lga)
            except Exception as e:
                print(f"\nERROR processing {precinct_name}: {str(e)}")
                self.failed_count += 1
                continue

        # Summary
        print("\n" + "=" * 80)
        print("PROCESSING COMPLETE")
        print("=" * 80)
        print(f"Precincts processed: {self.processed_count}/{len(precincts)}")
        print(f"Failed: {self.failed_count}")
        print(f"Total requirements extracted: {self.total_requirements}")
        print(f"Average per precinct: {self.total_requirements/max(self.processed_count, 1):.1f}")

        # Close connection
        self.conn.close()

if __name__ == "__main__":
    import sys

    # Parse command line args
    limit = None
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            limit = 3  # Test with first 3 precincts
            print("TEST MODE: Processing first 3 precincts only")
        elif sys.argv[1].isdigit():
            limit = int(sys.argv[1])

    processor = PrecinctProcessor()
    processor.run(limit=limit)
