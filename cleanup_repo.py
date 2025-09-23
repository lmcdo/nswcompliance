#!/usr/bin/env python3
"""
Repository cleanup script with safety checks
Analyzes files by age and usage before recommending deletion
"""

import os
import glob
from datetime import datetime, timedelta
from pathlib import Path
import json

class RepoCleanup:
 def __init__(self):
 self.current_time = datetime.now()
 self.recommendations = {
 'safe_to_delete': [],
 'review_needed': [],
 'keep': []
 }
 
 def check_file_age(self, filepath, days_old=7):
 """Check if file is older than specified days"""
 try:
 mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
 return (self.current_time - mtime).days > days_old
 except:
 return False
 
 def analyze_output_dirs(self):
 """Analyze output directories by content and age"""
 output_dirs = [
 'autoschemakg_output', 'autoschemakg_output_ollama_final', 
 'autoschemakg_output_ollama_working', 'langextract_verified_output',
 'monitored_pipeline_output', 'output', 'output_sepps', 'pipeline_output',
 'test_batch_output', 'test_output_1', 'validation_output', 'validated_outputs'
 ]
 
 for dirname in output_dirs:
 if not os.path.exists(dirname):
 continue
 
 dir_path = Path(dirname)
 files = list(dir_path.glob('**/*'))
 
 if not files:
 self.recommendations['safe_to_delete'].append({
 'path': dirname,
 'reason': 'Empty directory',
 'type': 'directory'
 })
 continue
 
 # Check most recent file in directory
 most_recent = max(files, key=lambda f: f.stat().st_mtime if f.is_file() else 0)
 
 if self.check_file_age(most_recent, days_old=14):
 self.recommendations['review_needed'].append({
 'path': dirname,
 'reason': f'No recent activity (oldest: {datetime.fromtimestamp(most_recent.stat().st_mtime).strftime("%Y-%m-%d")})',
 'file_count': len([f for f in files if f.is_file()]),
 'type': 'directory'
 })
 else:
 self.recommendations['keep'].append({
 'path': dirname,
 'reason': f'Recent activity (latest: {datetime.fromtimestamp(most_recent.stat().st_mtime).strftime("%Y-%m-%d")})',
 'type': 'directory'
 })
 
 def analyze_test_files(self):
 """Analyze test and debug files"""
 # Debug files - safe to delete
 debug_files = glob.glob('debug_*.py')
 for f in debug_files:
 self.recommendations['safe_to_delete'].append({
 'path': f,
 'reason': 'Debug file',
 'type': 'file'
 })
 
 # Root level test files - move or delete
 test_files = glob.glob('test_*.py')
 for f in test_files:
 if self.check_file_age(f, days_old=30):
 self.recommendations['review_needed'].append({
 'path': f,
 'reason': 'Old test file (suggest move to tests/ or delete)',
 'type': 'file'
 })
 else:
 self.recommendations['review_needed'].append({
 'path': f,
 'reason': 'Recent test file (suggest move to tests/)',
 'type': 'file'
 })
 
 def analyze_backup_files(self):
 """Analyze backup and temporary files"""
 # Database backups - keep newest only
 db_backups = glob.glob('*.db.*backup*') + glob.glob('nsw_planning.db.*')
 db_backups = [f for f in db_backups if 'backup' in f]
 
 if db_backups:
 # Sort by modification time, keep newest
 db_backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
 if len(db_backups) > 1:
 for backup in db_backups[1:]: # All except newest
 self.recommendations['safe_to_delete'].append({
 'path': backup,
 'reason': 'Old database backup (newer exists)',
 'type': 'file'
 })
 
 # Keep the newest
 self.recommendations['keep'].append({
 'path': db_backups[0],
 'reason': 'Newest database backup',
 'type': 'file'
 })
 
 # JSON test files
 test_jsons = glob.glob('*test*.json') + glob.glob('test_*.json')
 for f in test_jsons:
 if self.check_file_age(f, days_old=14):
 self.recommendations['safe_to_delete'].append({
 'path': f,
 'reason': 'Old test result file',
 'type': 'file'
 })
 
 # Disabled files
 disabled_files = glob.glob('*.DISABLED')
 for f in disabled_files:
 self.recommendations['safe_to_delete'].append({
 'path': f,
 'reason': 'Explicitly disabled file',
 'type': 'file'
 })
 
 def analyze_cache_dirs(self):
 """Analyze cache and temporary directories"""
 cache_dirs = ['.pytest_cache', '__pycache__']
 for dirname in cache_dirs:
 if os.path.exists(dirname):
 self.recommendations['safe_to_delete'].append({
 'path': dirname,
 'reason': 'Cache directory (will regenerate)',
 'type': 'directory'
 })
 
 def analyze_analysis_scripts(self):
 """Analyze one-off analysis/utility scripts"""
 analysis_patterns = [
 'analyze_*.py', 'check_*.py', 'add_*.py', 'implement_*.py',
 'convert_*.py', 'create_*.py', 'fix_*.py', 'migrate_*.py'
 ]
 
 for pattern in analysis_patterns:
 files = glob.glob(pattern)
 for f in files:
 # Skip if it's imported by other files (basic check)
 if self.is_imported(f):
 self.recommendations['keep'].append({
 'path': f,
 'reason': 'Appears to be imported by other files',
 'type': 'file'
 })
 elif self.check_file_age(f, days_old=21):
 self.recommendations['review_needed'].append({
 'path': f,
 'reason': 'Old analysis/utility script (check if still needed)',
 'type': 'file'
 })
 
 def is_imported(self, filename):
 """Basic check if a Python file is imported by others"""
 module_name = Path(filename).stem
 py_files = glob.glob('*.py')
 
 for py_file in py_files:
 if py_file == filename:
 continue
 try:
 with open(py_file, 'r', encoding='utf-8') as f:
 content = f.read()
 if f'import {module_name}' in content or f'from {module_name}' in content:
 return True
 except:
 continue
 return False
 
 def run_analysis(self):
 """Run full cleanup analysis"""
 print("Analyzing repository for cleanup opportunities...")
 
 self.analyze_output_dirs()
 self.analyze_test_files()
 self.analyze_backup_files()
 self.analyze_cache_dirs()
 self.analyze_analysis_scripts()
 
 return self.recommendations
 
 def print_report(self):
 """Print cleanup recommendations"""
 print("\n" + "="*60)
 print("REPOSITORY CLEANUP RECOMMENDATIONS")
 print("="*60)
 
 print(f"\nSAFE TO DELETE ({len(self.recommendations['safe_to_delete'])} items)")
 print("-" * 40)
 for item in self.recommendations['safe_to_delete']:
 print(f"[DELETE] {item['path']} - {item['reason']}")
 
 print(f"\nREVIEW NEEDED ({len(self.recommendations['review_needed'])} items)")
 print("-" * 40)
 for item in self.recommendations['review_needed']:
 extra = f" ({item['file_count']} files)" if 'file_count' in item else ""
 print(f"[REVIEW] {item['path']}{extra} - {item['reason']}")
 
 print(f"\nKEEP ({len(self.recommendations['keep'])} items)")
 print("-" * 40)
 for item in self.recommendations['keep']:
 print(f"[KEEP] {item['path']} - {item['reason']}")
 
 def save_report(self, filename='cleanup_report.json'):
 """Save detailed report to JSON"""
 with open(filename, 'w') as f:
 json.dump(self.recommendations, f, indent=2, default=str)
 print(f"\nDetailed report saved to: {filename}")

def main():
 cleanup = RepoCleanup()
 recommendations = cleanup.run_analysis()
 cleanup.print_report()
 cleanup.save_report()
 
 print("\n" + "="*60)
 print("NEXT STEPS:")
 print("1. Review the recommendations above")
 print("2. Check cleanup_report.json for detailed analysis")
 print("3. Manually delete items from 'SAFE TO DELETE' section")
 print("4. Review items in 'REVIEW NEEDED' section before deleting")
 print("="*60)

if __name__ == "__main__":
 main()