#!/usr/bin/env python3
"""
MANDATORY DATABASE SAFETY WRAPPER
NEVER REMOVE - Prevents database corruption and data loss

This wrapper MUST be used for ALL database operations.
It provides automatic timeouts, backup creation, and query safety checks.
"""

import os
import sys
import signal
import psycopg2
import subprocess
import time
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

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
  self.timeout = 30 # NEVER CHANGE - Hard limit
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
    print("ENFORCING DATABASE SAFETY PROTOCOLS")

    # 1. Set timeout (Windows compatible)
    import platform
    if platform.system() != 'Windows':
      signal.signal(signal.SIGALRM, self._timeout_handler)
      signal.alarm(self.timeout)
    else:
      print(" Timeout enforcement: Windows mode (30s statement timeout)")

    # 2. Check database health
    if not self._test_connection_health():
      raise DatabaseSafetyError("DB_SAFETY: Database unhealthy, aborting all operations")

    # 3. Check system resources
    if not self._check_system_resources():
      raise DatabaseSafetyError("DB_SAFETY: Insufficient system resources")

    # 4. Run external safety script
    if not self._run_safety_script():
      raise DatabaseSafetyError("DB_SAFETY: External safety checks failed")

    self.safety_checks_passed = True
    print(" Database safety protocols enforced")

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
      print(f" Database health check failed: {str(e)}")
      return False

  def _check_system_resources(self) -> bool:
    """Check system has sufficient resources"""
    try:
      # Check available disk space (simplified)
      import shutil
      free_bytes = shutil.disk_usage('.').free
      free_gb = free_bytes / (1024**3)

      if free_gb < 1.0: # Less than 1GB
        print(f" Insufficient disk space: {free_gb:.1f}GB")
        return False

      print(f" Disk space OK: {free_gb:.1f}GB available")
      return True
    except Exception as e:
      print(f" Could not check system resources: {str(e)}")
      return True # Don't block if we can't check

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
 return result.returncode == 0
 else:
 print(" Safety script not found - proceeding with caution")
 return True
 except Exception as e:
 print(f" Safety script failed: {str(e)}")
 return False

 def create_emergency_backup(self):
 """
 MANDATORY: Create backup before ANY database changes
 NEVER SKIP - This prevents data loss
 """
 if self.backup_created:
 return True

 print(" CREATING MANDATORY EMERGENCY BACKUP ")

 try:
 backup_script = os.path.join("scripts", "backup_database.sh")
 if os.path.exists(backup_script):
 result = subprocess.run(
 ["bash", backup_script],
 capture_output=True,
 text=True,
 timeout=300 # 5 minutes for backup
 )

 if result.returncode == 0:
 self.backup_created = True
 print(" Emergency backup created successfully")
 return True
 else:
 print(f" Backup failed: {result.stderr}")
 raise DatabaseSafetyError("DB_SAFETY: Cannot proceed without backup")
 else:
 print(" Backup script not found")
 raise DatabaseSafetyError("DB_SAFETY: No backup mechanism available")

 except subprocess.TimeoutExpired:
 raise DatabaseSafetyError("DB_SAFETY: Backup timeout - database may be corrupted")
 except Exception as e:
 raise DatabaseSafetyError(f"DB_SAFETY: Backup failed - {str(e)}")

 def is_query_dangerous(self, sql: str) -> bool:
 """
 Analyze if query is dangerous and should be blocked
 NEVER REMOVE - Prevents accidental data destruction
 """
 sql_upper = sql.upper().strip()

 # Block UPDATE/DELETE without WHERE clause
 if re.match(r'UPDATE\s+\w+\s+SET\s+.*(?!.*WHERE)', sql_upper):
 return True

 if re.match(r'DELETE\s+FROM\s+\w+\s*(?!.*WHERE)', sql_upper):
 return True

 # Block DROP operations on main tables
 dangerous_drops = ['DROP TABLE', 'DROP DATABASE', 'DROP SCHEMA']
 if any(drop in sql_upper for drop in dangerous_drops):
 return True

 # Block TRUNCATE on main tables
 if 'TRUNCATE' in sql_upper and any(table in sql_upper for table in ['REGULATORY_PROVISIONS', 'DOCUMENT_VERSIONS']):
 return True

 # Check for operations on too many records
 if self._affects_too_many_records(sql):
 return True

 return False

 def _affects_too_many_records(self, sql: str) -> bool:
 """Check if query affects too many records"""
 # This is a simplified check - in production, estimate affected rows
 sql_upper = sql.upper()

 # If it's an UPDATE or DELETE without specific WHERE conditions, it's risky
 if ('UPDATE' in sql_upper or 'DELETE' in sql_upper) and 'LIMIT' not in sql_upper:
 if 'WHERE' not in sql_upper:
 return True

 # Check for broad WHERE conditions
 broad_conditions = ['WHERE 1=1', 'WHERE TRUE', 'WHERE id > 0']
 if any(condition in sql_upper for condition in broad_conditions):
 return True

 return False

 def connect(self):
 """Establish safe database connection"""
 if not self.safety_checks_passed:
 raise DatabaseSafetyError("DB_SAFETY: Safety checks not passed")

 try:
 self.connection = psycopg2.connect(
 host=self.host,
 database=self.database,
 user=self.user,
 port=self.port,
 connect_timeout=10
 )

 # Set statement timeout to prevent runaway queries
 cursor = self.connection.cursor()
 cursor.execute(f"SET statement_timeout = '{self.timeout}s'")
 self.connection.commit()
 cursor.close()

 print(" Safe database connection established")
 return self.connection

 except Exception as e:
 raise DatabaseSafetyError(f"DB_SAFETY: Connection failed - {str(e)}")

 def execute_safe(self, sql: str, params: Optional[tuple] = None, fetch: bool = False) -> Any:
 """
 Execute SQL with comprehensive safety checks
 NEVER BYPASS - Use this for ALL database operations
 """
 if not self.safety_checks_passed:
 raise DatabaseSafetyError("DB_SAFETY: Safety protocols not enforced")

 # Check if query is dangerous
 if self.is_query_dangerous(sql):
 raise DatabaseSafetyError(f"DB_SAFETY: Query blocked for safety - {sql[:100]}...")

 # Create backup before any changes
 if any(keyword in sql.upper() for keyword in ['INSERT', 'UPDATE', 'DELETE', 'ALTER', 'DROP', 'CREATE']):
 self.create_emergency_backup()

 # Establish connection if needed
 if not self.connection:
 self.connect()

 try:
 cursor = self.connection.cursor()

 # Execute with parameters to prevent SQL injection
 if params:
 cursor.execute(sql, params)
 else:
 cursor.execute(sql)

 result = None
 if fetch:
 if 'SELECT' in sql.upper():
 result = cursor.fetchall()

 # Commit changes
 if any(keyword in sql.upper() for keyword in ['INSERT', 'UPDATE', 'DELETE', 'ALTER', 'CREATE', 'DROP']):
 self.connection.commit()
 print(f" Database operation committed safely")

 cursor.close()
 return result

 except Exception as e:
 if self.connection:
 self.connection.rollback()
 raise DatabaseSafetyError(f"DB_SAFETY: Query execution failed - {str(e)}")

 def cursor(self):
 """Get a cursor from the safe connection"""
 if not self.connection:
 self.connect()
 return self.connection.cursor()

 def commit(self):
 """Commit the current transaction"""
 if self.connection:
 self.connection.commit()

 def rollback(self):
 """Rollback the current transaction"""
 if self.connection:
 self.connection.rollback()

 def close(self):
 """Safely close connection"""
 if self.connection:
 self.connection.close()
 self.connection = None

 # Cancel the timeout alarm (Unix only)
 import platform
 if platform.system() != 'Windows':
 signal.alarm(0)
 print(" Database connection closed safely")

 def __enter__(self):
 """Context manager entry"""
 self.connect()
 return self

 def __exit__(self, exc_type, exc_val, exc_tb):
 """Context manager exit"""
 self.close()

def get_safe_connection(**kwargs) -> SafeConnection:
 """
 MANDATORY: Get a safe database connection
 ALWAYS use this instead of direct psycopg2.connect()
 """
 return SafeConnection(**kwargs)

# Example usage (MANDATORY pattern):
if __name__ == "__main__":
 # This is how ALL database scripts must connect
 try:
 with get_safe_connection() as db:
 # Example safe operations
 result = db.execute_safe("SELECT COUNT(*) FROM regulatory_provisions", fetch=True)
 print(f"Provision count: {result[0][0]}")

 # This would be blocked:
 # db.execute_safe("DELETE FROM regulatory_provisions") # No WHERE clause = blocked

 except DatabaseSafetyError as e:
 print(f" SAFETY VIOLATION: {str(e)}")
 sys.exit(1)
 except Exception as e:
 print(f" Error: {str(e)}")
 sys.exit(1)
