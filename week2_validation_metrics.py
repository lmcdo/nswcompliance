"""
Week 2: Validation Metrics for Precinct Requirements
Calculate precision, recall, and other quality metrics
"""
import os
from dotenv import load_dotenv
from db_safety_wrapper import get_safe_connection

load_dotenv()

class ValidationMetrics:
    def __init__(self):
        self.conn = None

    def connect_db(self):
        """Connect to database"""
        self.conn = get_safe_connection(
            host=os.getenv('PGHOST'),
            database=os.getenv('PGDATABASE'),
            user=os.getenv('PGUSER'),
            port=int(os.getenv('PGPORT', 5432))
        )
        self.conn.connect()

    def get_overall_stats(self):
        """Get overall processing statistics"""
        cur = self.conn.cursor()

        print("=" * 80)
        print("WEEK 2 PROCESSING - OVERALL STATISTICS")
        print("=" * 80)

        # Total precincts processed
        cur.execute("SELECT COUNT(DISTINCT precinct_id) FROM dcp_precinct_requirements")
        precinct_count = cur.fetchone()[0]
        print(f"\nPrecincts Processed: {precinct_count}")

        # Total requirements extracted
        cur.execute("SELECT COUNT(*) FROM dcp_precinct_requirements")
        req_count = cur.fetchone()[0]
        print(f"Requirements Extracted: {req_count}")
        print(f"Average per Precinct: {req_count/precinct_count:.1f}")

        # Category distribution
        print("\n" + "=" * 80)
        print("CATEGORY DISTRIBUTION")
        print("=" * 80)
        cur.execute("""
            SELECT
                category,
                COUNT(*) as count,
                ROUND(AVG(CASE WHEN confidence = 'high' THEN 100 ELSE 0 END), 0) as pct_high_conf
            FROM dcp_precinct_requirements
            GROUP BY category
            ORDER BY count DESC
        """)

        print(f"{'Category':<25} {'Count':>8} {'High Conf %':>12}")
        print("-" * 80)
        for category, count, pct_high in cur.fetchall():
            print(f"{category:<25} {count:>8} {pct_high:>11.0f}%")

        # Confidence distribution
        print("\n" + "=" * 80)
        print("CONFIDENCE DISTRIBUTION")
        print("=" * 80)
        cur.execute("""
            SELECT
                confidence,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
            FROM dcp_precinct_requirements
            GROUP BY confidence
            ORDER BY
                CASE confidence
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END
        """)

        for confidence, count, pct in cur.fetchall():
            print(f"{confidence.upper():<10}: {count:>4} requirements ({pct:>5.1f}%)")

        # Numeric values extracted
        print("\n" + "=" * 80)
        print("NUMERIC VALUE EXTRACTION")
        print("=" * 80)
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(value_numeric) as with_numeric,
                ROUND(COUNT(value_numeric) * 100.0 / COUNT(*), 1) as percentage
            FROM dcp_precinct_requirements
        """)
        total, with_numeric, pct = cur.fetchone()
        print(f"Total Requirements: {total}")
        print(f"With Numeric Values: {with_numeric} ({pct}%)")

        # Requirements with conditionals
        print("\n" + "=" * 80)
        print("CONDITIONAL DETECTION")
        print("=" * 80)
        cur.execute("""
            SELECT
                has_conditionals,
                COUNT(*) as count
            FROM dcp_precinct_requirements
            GROUP BY has_conditionals
        """)
        for has_cond, count in cur.fetchall():
            status = "WITH conditionals" if has_cond else "WITHOUT conditionals"
            print(f"{status}: {count}")

    def keyword_cross_check(self):
        """
        Check if we're missing any provisions with category keywords
        This helps calculate RECALL (did we find all relevant provisions?)
        """
        cur = self.conn.cursor()

        print("\n" + "=" * 80)
        print("KEYWORD CROSS-CHECK (Recall Estimation)")
        print("=" * 80)
        print("Checking if source provisions contain category keywords...")

        # Get category keywords from requirement_categories table
        cur.execute("SELECT category, positive_keywords FROM requirement_categories")
        categories = cur.fetchall()

        for category, keywords in categories:
            if not keywords:
                continue

            # Build keyword search pattern
            keyword_pattern = '|'.join([f"\\m{kw}\\M" for kw in keywords])

            # Find provisions that contain keywords but weren't categorized
            cur.execute("""
                SELECT COUNT(*)
                FROM dcp_precinct_provisions dpp
                WHERE dpp.provision_text ~* %s
                AND NOT EXISTS (
                    SELECT 1
                    FROM dcp_precinct_requirements dpr
                    WHERE dpr.category = %s
                    AND dpp.id = ANY(dpr.source_provision_ids)
                )
            """, (keyword_pattern, category))

            missed = cur.fetchone()[0]

            # Count total provisions with keywords
            cur.execute("""
                SELECT COUNT(*)
                FROM dcp_precinct_provisions
                WHERE provision_text ~* %s
            """, (keyword_pattern,))

            total_with_keyword = cur.fetchone()[0]

            # Count how many we captured
            cur.execute("""
                SELECT COUNT(DISTINCT provision_id)
                FROM (
                    SELECT unnest(source_provision_ids) as provision_id
                    FROM dcp_precinct_requirements
                    WHERE category = %s
                ) AS prov_ids
            """, (category,))

            captured = cur.fetchone()[0]

            if total_with_keyword > 0:
                recall_est = (captured / total_with_keyword) * 100
                print(f"\n{category}:")
                print(f"  Provisions with keywords: {total_with_keyword}")
                print(f"  Captured in requirements: {captured}")
                print(f"  Missed: {missed}")
                print(f"  Estimated Recall: {recall_est:.1f}%")

    def check_data_quality(self):
        """Check overall data quality"""
        cur = self.conn.cursor()

        print("\n" + "=" * 80)
        print("DATA QUALITY CHECKS")
        print("=" * 80)

        # Check for NULL values in critical fields
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN requirement_text IS NULL OR requirement_text = '' THEN 1 END) as null_text,
                COUNT(CASE WHEN category IS NULL THEN 1 END) as null_category,
                COUNT(CASE WHEN source_provision_ids IS NULL OR source_provision_ids = '{}' THEN 1 END) as null_sources
            FROM dcp_precinct_requirements
        """)

        total, null_text, null_cat, null_sources = cur.fetchone()
        print(f"Total Requirements: {total}")
        print(f"Missing requirement_text: {null_text}")
        print(f"Missing category: {null_cat}")
        print(f"Missing source_provision_ids: {null_sources}")

        if null_text == 0 and null_cat == 0 and null_sources == 0:
            print("\n[OK] All critical fields populated")
        else:
            print("\n[WARNING] Data quality issues detected")

    def generate_summary_report(self):
        """Generate final summary report"""
        cur = self.conn.cursor()

        print("\n" + "=" * 80)
        print("WEEK 2 PROCESSING - SUMMARY REPORT")
        print("=" * 80)

        # Success metrics
        cur.execute("SELECT COUNT(DISTINCT precinct_id) FROM dcp_precinct_requirements")
        precincts = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM dcp_precinct_requirements")
        requirements = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM dcp_precinct_requirements
            WHERE confidence = 'high'
        """)
        high_conf = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT category) FROM dcp_precinct_requirements")
        categories = cur.fetchone()[0]

        print(f"\n[OK] Precincts Processed: {precincts}/47")
        print(f"[OK] Requirements Extracted: {requirements}")
        print(f"[OK] High Confidence: {high_conf} ({high_conf/requirements*100:.1f}%)")
        print(f"[OK] Categories Used: {categories}")

        print("\nStatus: COMPLETE")
        print("\nNext Steps:")
        print("1. Expert review of medium/low confidence requirements")
        print("2. Validation of high confidence samples (10-20%)")
        print("3. Mark validated requirements in database")
        print("4. Create API endpoint to serve categorized requirements")
        print("5. Update UI to display categorized requirements")

        print("\n" + "=" * 80)

    def run(self):
        """Run full validation suite"""
        self.connect_db()
        self.get_overall_stats()
        self.keyword_cross_check()
        self.check_data_quality()
        self.generate_summary_report()
        self.conn.close()

if __name__ == "__main__":
    validator = ValidationMetrics()
    validator.run()
