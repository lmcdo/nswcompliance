#!/usr/bin/env python3
"""
Safe repository cleanup script
Executes only the items marked as 'safe_to_delete' from cleanup analysis
"""

import os
import shutil
import glob
from pathlib import Path
import json

class SafeCleanup:
 def __init__(self):
 self.deleted_items = []
 self.failed_deletions = []
 self.dry_run = True
 
 def load_recommendations(self, filename='cleanup_report.json'):
 """Load cleanup recommendations from JSON report"""
 try:
 with open(filename, 'r') as f:
 return json.load(f)
 except FileNotFoundError:
 print(f"Error: {filename} not found. Run cleanup_repo.py first.")
 return None
 
 def safe_delete_file(self, filepath):
 """Safely delete a file"""
 if not os.path.exists(filepath):
 print(f" Skip: {filepath} (already deleted)")
 return True
 
 try:
 if self.dry_run:
 print(f" [DRY RUN] Would delete file: {filepath}")
 return True
 else:
 os.remove(filepath)
 print(f" Deleted file: {filepath}")
 return True
 except Exception as e:
 print(f" Error deleting {filepath}: {e}")
 self.failed_deletions.append({'path': filepath, 'error': str(e)})
 return False
 
 def safe_delete_directory(self, dirpath):
 """Safely delete a directory"""
 if not os.path.exists(dirpath):
 print(f" Skip: {dirpath} (already deleted)")
 return True
 
 try:
 if self.dry_run:
 print(f" [DRY RUN] Would delete directory: {dirpath}")
 return True
 else:
 shutil.rmtree(dirpath)
 print(f" Deleted directory: {dirpath}")
 return True
 except Exception as e:
 print(f" Error deleting {dirpath}: {e}")
 self.failed_deletions.append({'path': dirpath, 'error': str(e)})
 return False
 
 def execute_safe_deletions(self, recommendations):
 """Execute only the safe deletions"""
 safe_items = recommendations.get('safe_to_delete', [])
 
 if not safe_items:
 print("No safe items to delete found.")
 return
 
 print(f"\nExecuting safe cleanup ({len(safe_items)} items):")
 print("=" * 50)
 
 for item in safe_items:
 filepath = item['path']
 file_type = item['type']
 reason = item['reason']
 
 print(f"\n{reason}: {filepath}")
 
 if file_type == 'directory':
 if self.safe_delete_directory(filepath):
 self.deleted_items.append(filepath)
 else:
 if self.safe_delete_file(filepath):
 self.deleted_items.append(filepath)
 
 def organize_test_files(self):
 """Move test files to organized directory structure"""
 test_files = glob.glob('test_*.py')
 
 if not test_files:
 print("\nNo root-level test files to organize.")
 return
 
 print(f"\nOrganizing test files ({len(test_files)} files):")
 print("=" * 50)
 
 # Create directory structure
 tests_dir = Path('tests/root_tests')
 if self.dry_run:
 print(f" [DRY RUN] Would create directory: {tests_dir}")
 else:
 tests_dir.mkdir(parents=True, exist_ok=True)
 print(f" Created directory: {tests_dir}")
 
 # Move test files
 for test_file in test_files:
 dest_path = tests_dir / test_file
 
 if self.dry_run:
 print(f" [DRY RUN] Would move: {test_file} -> {dest_path}")
 else:
 try:
 shutil.move(test_file, dest_path)
 print(f" Moved: {test_file} -> {dest_path}")
 self.deleted_items.append(f"moved: {test_file}")
 except Exception as e:
 print(f" Error moving {test_file}: {e}")
 self.failed_deletions.append({'path': test_file, 'error': str(e)})
 
 def remove_duplicate_backups(self):
 """Remove duplicate database backups (keep newest only)"""
 backup_files = []
 
 # Find all backup files
 patterns = ['*.db.*backup*', 'nsw_planning.db.*']
 for pattern in patterns:
 backup_files.extend(glob.glob(pattern))
 
 # Filter to actual backup files
 backup_files = [f for f in backup_files if 'backup' in f]
 
 if len(backup_files) <= 1:
 print("\nNo duplicate database backups to remove.")
 return
 
 # Sort by modification time (newest first)
 backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
 newest_backup = backup_files[0]
 old_backups = backup_files[1:]
 
 print(f"\nRemoving old database backups ({len(old_backups)} files):")
 print(f"Keeping newest: {newest_backup}")
 print("=" * 50)
 
 for backup in old_backups:
 print(f"\nRemoving old backup: {backup}")
 if self.safe_delete_file(backup):
 self.deleted_items.append(backup)
 
 def print_summary(self):
 """Print cleanup summary"""
 print("\n" + "=" * 60)
 print("CLEANUP SUMMARY")
 print("=" * 60)
 
 if self.dry_run:
 print("*** DRY RUN MODE - NO ACTUAL CHANGES MADE ***")
 print("Run with --execute to perform actual cleanup")
 
 print(f"\nSuccessfully processed: {len(self.deleted_items)} items")
 for item in self.deleted_items:
 print(f" [OK] {item}")
 
 if self.failed_deletions:
 print(f"\nFailed deletions: {len(self.failed_deletions)} items")
 for item in self.failed_deletions:
 print(f" [ERROR] {item['path']}: {item['error']}")
 else:
 print("\nNo deletion failures!")
 
 def run_cleanup(self, execute=False):
 """Run the complete cleanup process"""
 self.dry_run = not execute
 
 # Load recommendations
 recommendations = self.load_recommendations()
 if not recommendations:
 return
 
 print("SAFE REPOSITORY CLEANUP")
 print("=" * 60)
 
 if self.dry_run:
 print("*** DRY RUN MODE ***")
 print("Add --execute flag to perform actual cleanup")
 else:
 print("*** EXECUTING CLEANUP ***")
 print("Starting cleanup in 2 seconds...")
 
 # Execute safe deletions
 self.execute_safe_deletions(recommendations)
 
 # Organize test files
 self.organize_test_files()
 
 # Remove duplicate backups
 self.remove_duplicate_backups()
 
 # Print summary
 self.print_summary()

def main():
 import sys
 
 execute = '--execute' in sys.argv
 cleanup = SafeCleanup()
 cleanup.run_cleanup(execute=execute)

if __name__ == "__main__":
 main()