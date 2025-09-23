#!/usr/bin/env python3
"""
Autocomplete verification script for PRP-R2: Database Recreation
Automatically drops and recreates the nsw_planning database
"""

import subprocess
import json
from datetime import datetime

class PRPR2Verification:
    """Autocomplete database recreation"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "PRP-R2_DATABASE_RECREATION",
            "actions_taken": [],
            "checks": {},
            "errors": [],
            "success": False
        }
        self.psql_path = r"C:\Program Files\PostgreSQL\17\bin\psql.exe"

    def drop_database(self) -> bool:
        """Drop the corrupted database"""
        print("Dropping nsw_planning database...")
        try:
            result = subprocess.run(
                [self.psql_path, "-U", "postgres", "-c", "DROP DATABASE IF EXISTS nsw_planning;"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.results["actions_taken"].append("Database dropped")
                print("✅ Database dropped successfully")
                return True
            else:
                self.results["errors"].append(f"Drop failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            self.results["errors"].append("Drop operation timed out")
            return False
        except Exception as e:
            self.results["errors"].append(f"Drop error: {str(e)}")
            return False

    def create_database(self) -> bool:
        """Create fresh database"""
        print("Creating fresh nsw_planning database...")
        try:
            result = subprocess.run(
                [self.psql_path, "-U", "postgres", "-c", "CREATE DATABASE nsw_planning;"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.results["actions_taken"].append("Database created")
                print("✅ Database created successfully")
                return True
            else:
                self.results["errors"].append(f"Create failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            self.results["errors"].append("Create operation timed out")
            return False
        except Exception as e:
            self.results["errors"].append(f"Create error: {str(e)}")
            return False

    def verify_database(self) -> bool:
        """Verify database exists and is accessible"""
        print("Verifying database...")
        try:
            result = subprocess.run(
                [self.psql_path, "-U", "postgres", "-d", "nsw_planning", "-c", "SELECT version();"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.results["checks"]["database_accessible"] = True
                print("✅ Database verified and accessible")
                return True
            else:
                self.results["checks"]["database_accessible"] = False
                return False
        except:
            self.results["checks"]["database_accessible"] = False
            return False

    def check_empty_database(self) -> bool:
        """Verify database is empty"""
        print("Checking database is empty...")
        try:
            result = subprocess.run(
                [self.psql_path, "-U", "postgres", "-d", "nsw_planning", "-c",
                 "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and "0" in result.stdout:
                self.results["checks"]["database_empty"] = True
                print("✅ Database is empty")
                return True
        except:
            pass

        self.results["checks"]["database_empty"] = False
        return False

    def execute(self) -> bool:
        """Execute database recreation process"""
        print("\n" + "="*60)
        print("PRP-R2: Database Recreation - AUTOCOMPLETE")
        print("="*60 + "\n")

        # Drop existing database
        if not self.drop_database():
            print("WARNING: Drop had issues, continuing...")

        # Create fresh database
        if not self.create_database():
            self.results["success"] = False
            print("FAILED: Failed to create database")
        else:
            # Verify creation
            if self.verify_database() and self.check_empty_database():
                self.results["success"] = True
                print("\n✅ Database recreation successful")

                # Create marker
                import os
                os.makedirs("recovery_checkpoints", exist_ok=True)
                with open("recovery_checkpoints/R2_complete.marker", "w") as f:
                    f.write(f"PRP-R2 completed at {datetime.now().isoformat()}\n")
                    f.write("Fresh nsw_planning database created\n")

                self.results["actions_taken"].append("Created completion marker")
            else:
                self.results["success"] = False
                self.results["errors"].append("Database verification failed")

        # Save results
        with open("verify_r2_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nActions taken: {len(self.results['actions_taken'])}")
        print(f"Result: {'PASSED' if self.results['success'] else 'FAILED'}")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        return self.results["success"]

if __name__ == "__main__":
    verifier = PRPR2Verification()
    verifier.execute()