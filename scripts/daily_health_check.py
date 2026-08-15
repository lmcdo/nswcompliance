#!/usr/bin/env python3
"""Daily database health check."""

import psycopg2
import sys
from datetime import datetime, timedelta

def health_check():
    """Check database health and alert if issues."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="nsw_planning",
            user="postgres",
            password="postgres",
            connect_timeout=10
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Check 1: Statistics age
        cur.execute("""
            SELECT
                relname,
                last_analyze,
                NOW() - last_analyze as age
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
              AND relname IN ('documents', 'regulatory_provisions', 'development_controls')
            ORDER BY age DESC NULLS FIRST;
        """)

        stats = cur.fetchall()
        issues = []

        for table, last_analyze, age in stats:
            if last_analyze is None:
                issues.append(f"[CRITICAL] {table} has NEVER been analyzed!")
            elif age and age > timedelta(days=7):
                issues.append(f"[WARNING] {table} statistics are {age.days} days old (last: {last_analyze})")

        # Check 2: Connection count
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_trans
            FROM pg_stat_activity
            WHERE datname = 'nsw_planning';
        """)

        total_conns, idle_in_trans = cur.fetchone()

        if idle_in_trans > 5:
            issues.append(f"[WARNING] {idle_in_trans} connections idle in transaction (possible leak)")

        # Check 3: Database size
        cur.execute("""
            SELECT pg_size_pretty(pg_database_size('nsw_planning')) as size;
        """)

        db_size = cur.fetchone()[0]

        # Check 4: Long-running queries
        cur.execute("""
            SELECT COUNT(*)
            FROM pg_stat_activity
            WHERE datname = 'nsw_planning'
              AND state = 'active'
              AND NOW() - query_start > interval '5 minutes';
        """)

        long_queries = cur.fetchone()[0]

        if long_queries > 0:
            issues.append(f"[WARNING] {long_queries} queries running longer than 5 minutes")

        # Report results
        if issues:
            print(f"\n{'='*60}")
            print(f"DATABASE HEALTH CHECK - {datetime.now()}")
            print(f"{'='*60}")
            for issue in issues:
                print(issue)
            print(f"\nDatabase size: {db_size}")
            print(f"Total connections: {total_conns}")
            print(f"{'='*60}\n")

            # Write to log
            log_path = 'logs/health_check.log'
            with open(log_path, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Health Check - {datetime.now()}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Issues found:\n")
                for issue in issues:
                    f.write(f"  {issue}\n")
                f.write(f"\nDatabase size: {db_size}\n")
                f.write(f"Total connections: {total_conns}\n\n")

            # Update quickstart status
            import subprocess
            subprocess.run(['python', 'scripts/update_quickstart_status.py', 'health_check_failed', str(datetime.now())],
                          capture_output=True, check=False)

            sys.exit(1)  # Exit with error if issues found
        else:
            print(f"[OK] Database health check passed - {datetime.now()}")
            print(f"   Database size: {db_size}")
            print(f"   Total connections: {total_conns}")

            # Write success to log
            log_path = 'logs/health_check.log'
            with open(log_path, 'a') as f:
                f.write(f"{datetime.now()} - [OK] Health check passed, Size: {db_size}, Connections: {total_conns}\n")

            # Update quickstart status
            import subprocess
            subprocess.run(['python', 'scripts/update_quickstart_status.py', 'health_check', str(datetime.now())],
                          capture_output=True, check=False)

        cur.close()
        conn.close()

    except Exception as e:
        print(f"[CRITICAL] Health check failed: {e}")

        # Write error to log
        try:
            with open('logs/health_check.log', 'a') as f:
                f.write(f"\n{datetime.now()} - [CRITICAL] Health check failed: {e}\n")
        except:
            pass

        sys.exit(1)

if __name__ == "__main__":
    health_check()
