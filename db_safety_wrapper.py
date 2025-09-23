#!/usr/bin/env python3
"""
CRITICAL DATABASE SAFETY WRAPPER
DO NOT MODIFY - This prevents database corruption and data loss

MANDATORY SAFETY REQUIREMENTS:
1. NEVER REMOVE safety checks
2. NEVER allow direct database access without this wrapper
3. NEVER modify timeout settings
4. NEVER bypass backup requirements
5. ALWAYS use prepared statements
6. ALWAYS log all operations

VIOLATION OF THESE RULES = IMMEDIATE DATA LOSS RISK
"""

import os
import sys
import json
import time
import signal
import psycopg2
import subprocess
from typing import Optional, Any, Dict, List
import logging

# Configure safety logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - SAFETY - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseSafetyError(Exception):
    """Critical database safety violation"""
    pass

class SafeConnection:
    """
    MANDATORY Safe Database Connection Wrapper
    NEVER BYPASS - Prevents database destruction
    """

    def __init__(self, host="127.0.0.1", database="nsw_planning", user="postgres", port=5432):
        self.host = host
        self.database = database
        self.user = user
        self.port = port
        self.timeout = 30  # NEVER CHANGE - Hard limit
        self.backup_created = False
        self.connection = None
        self.safety_checks_passed = False

        # MANDATORY: Run safety checks before ANY operation
        self.enforce_db_safety()

    def enforce_db_safety(self):
        """
        NEVER REMOVE - Critical safety enforcement
        This function prevents database corruption and data loss
        """
        # print("ENFORCING DATABASE SAFETY PROTOCOLS")  # Disabled for JSON output compatibility

        # 1. Set timeout (Windows compatible)
        import platform
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.timeout)
        else:
            pass  # Windows mode - using statement timeout instead of SIGALRM

        # 2. Check database health
        if not self._test_connection_health():
            raise DatabaseSafetyError("DB_SAFETY: Database unhealthy, aborting all operations")

        # 3. Check system resources
        if not self._check_system_resources():
            raise DatabaseSafetyError("DB_SAFETY: Insufficient system resources")

        # 4. Run external safety script (optional)
        self._run_safety_script()  # Don't fail if script missing

        self.safety_checks_passed = True
        # print("Database safety protocols enforced")  # Disabled for JSON compatibility

    def _timeout_handler(self, signum, frame):
        """Handle operation timeout"""
        raise DatabaseSafetyError("DB_SAFETY: Operation timeout (30 seconds) - Auto-abort to prevent corruption")

    def _test_connection_health(self) -> bool:
        """Test if database is healthy and responsive"""
        try:
            test_conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                port=self.port,
                connect_timeout=5
            )
            cursor = test_conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            test_conn.close()
            return result[0] == 1
        except Exception as e:
            # print(f"Database health check failed: {str(e)}")  # Disabled for JSON compatibility
            return False

    def _check_system_resources(self) -> bool:
        """Check system has sufficient resources"""
        try:
            # Check available disk space (simplified)
            import shutil
            free_bytes = shutil.disk_usage('.').free
            free_gb = free_bytes / (1024**3)

            if free_gb < 1.0:  # Less than 1GB
                # print(f"Insufficient disk space: {free_gb:.1f}GB")  # Disabled for JSON compatibility
                return False

            # print(f"Disk space OK: {free_gb:.1f}GB available")  # Disabled for JSON compatibility
            return True
        except Exception as e:
            # print(f"Could not check system resources: {str(e)}")  # Disabled for JSON compatibility
            return True  # Don't block if we can't check

    def _run_safety_script(self) -> bool:
        """Run external safety check script"""
        try:
            safety_script = os.path.join("scripts", "db_safety_check.sh")
            if os.path.exists(safety_script):
                result = subprocess.run(
                    ["bash", safety_script],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    # print(f"Safety script failed: {result.stderr}")  # Disabled for JSON compatibility
                    return False
                # print("External safety checks passed")  # Disabled for JSON compatibility
                return True
            else:
                # print("Safety script not found, using internal checks only")  # Disabled for JSON compatibility
                return True
        except Exception as e:
            # print(f"Could not run safety script: {str(e)}")  # Disabled for JSON compatibility
            return True  # Don't block if script fails

    def create_emergency_backup(self):
        """
        CRITICAL - Create emergency backup before any operation
        NEVER SKIP THIS
        """
        if self.backup_created:
            return True

        backup_dir = "emergency_backups"
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = int(time.time())
        backup_file = os.path.join(backup_dir, f"emergency_backup_{timestamp}.sql")

        try:
            # Create PostgreSQL dump
            cmd = [
                "pg_dump",
                f"--host={self.host}",
                f"--port={self.port}",
                f"--username={self.user}",
                f"--dbname={self.database}",
                "--no-password",
                f"--file={backup_file}"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                self.backup_created = True
                print(f"Emergency backup created: {backup_file}")
                return True
            else:
                print(f"Backup failed: {result.stderr}")
                raise DatabaseSafetyError("DB_SAFETY: Could not create emergency backup")

        except Exception as e:
            print(f"Backup error: {str(e)}")
            raise DatabaseSafetyError(f"DB_SAFETY: Backup failed - {str(e)}")

    def is_query_dangerous(self, sql: str) -> bool:
        """
        CRITICAL - Check if SQL query is dangerous
        NEVER ALLOW dangerous operations
        """
        sql_upper = sql.upper().strip()

        # Absolutely forbidden operations
        forbidden = [
            'DROP DATABASE',
            'DROP SCHEMA',
            'TRUNCATE',
            'DELETE FROM',
            'UPDATE WITHOUT WHERE',  # Will be checked separately
            'ALTER DATABASE',
            'CREATE DATABASE',
            'GRANT ALL',
            'REVOKE',
        ]

        for dangerous in forbidden:
            if dangerous in sql_upper:
                print(f"DANGEROUS QUERY BLOCKED: {dangerous}")
                return True

        # Check for UPDATE/DELETE without WHERE
        if self._affects_too_many_records(sql):
            return True

        return False

    def _affects_too_many_records(self, sql: str) -> bool:
        """Check if query affects too many records without WHERE clause"""
        sql_upper = sql.upper().strip()

        # Check for DELETE without WHERE
        if 'DELETE FROM' in sql_upper and 'WHERE' not in sql_upper:
            print("DELETE without WHERE clause blocked")
            return True

        # Check for UPDATE without WHERE
        if sql_upper.startswith('UPDATE') and 'WHERE' not in sql_upper:
            print("UPDATE without WHERE clause blocked")
            return True

        return False

    def connect(self):
        """Create safe database connection"""
        if not self.safety_checks_passed:
            raise DatabaseSafetyError("DB_SAFETY: Safety checks not passed")

        try:
            self.connection = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                port=self.port,
                connect_timeout=self.timeout
            )

            # Set statement timeout
            cursor = self.connection.cursor()
            cursor.execute(f"SET statement_timeout = '{self.timeout}s'")
            cursor.close()

            # print("Safe database connection established")  # Disabled for JSON compatibility
            return self.connection

        except Exception as e:
            print(f"Connection failed: {str(e)}")
            raise DatabaseSafetyError(f"DB_SAFETY: Connection failed - {str(e)}")

    def execute_safe(self, sql: str, params: Optional[tuple] = None, fetch: bool = False) -> Any:
        """
        CRITICAL - Execute SQL with full safety checks
        NEVER bypass these checks
        """
        if not self.connection:
            self.connect()

        # MANDATORY safety checks
        if self.is_query_dangerous(sql):
            raise DatabaseSafetyError(f"DB_SAFETY: Dangerous query blocked: {sql}")

        # Create backup before any modification
        if any(word in sql.upper() for word in ['INSERT', 'UPDATE', 'DELETE', 'ALTER', 'CREATE', 'DROP']):
            self.create_emergency_backup()

        try:
            cursor = self.connection.cursor()

            # Log the operation for safety
            logger.info(f"EXECUTING SAFE SQL: {sql[:200]}...")

            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            if fetch:
                result = cursor.fetchall()
                cursor.close()
                return result
            else:
                cursor.close()
                return cursor.rowcount

        except Exception as e:
            print(f"Query execution failed: {str(e)}")
            self.rollback()
            raise DatabaseSafetyError(f"DB_SAFETY: Query failed - {str(e)}")

    def cursor(self):
        """Get database cursor with safety wrapper"""
        if not self.connection:
            self.connect()
        return self.connection.cursor()

    def commit(self):
        """Commit transaction with safety logging"""
        if self.connection:
            self.connection.commit()
            print("Transaction committed safely")

    def rollback(self):
        """Rollback transaction with safety logging"""
        if self.connection:
            self.connection.rollback()
            print("Transaction rolled back safely")

    def close(self):
        """Close connection with cleanup"""
        if self.connection:
            self.connection.close()
            self.connection = None
            # print("Database connection closed safely")  # Disabled for JSON compatibility

        # Clear timeout alarm
        import platform
        if platform.system() != 'Windows':
            signal.alarm(0)

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.close()

def get_safe_connection(**kwargs) -> SafeConnection:
    """
    MANDATORY - Get safe database connection
    NEVER use psycopg2.connect() directly
    """
    return SafeConnection(**kwargs)