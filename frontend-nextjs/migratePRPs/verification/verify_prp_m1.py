#!/usr/bin/env python3
"""
PRP-M1 Verification: Component Migration Foundation
Verifies that UI components were successfully migrated
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

def verify_component_migration() -> Dict[str, bool]:
    """Verify that all components were migrated successfully"""
    results = {}
    
    # Define expected component paths
    component_dirs = [
        "components/new-ui/core",
        "components/new-ui/panels",
        "components/new-ui/common",
        "components/ui"
    ]
    
    # Check directories exist
    for dir_path in component_dirs:
        exists = os.path.exists(dir_path) and os.path.isdir(dir_path)
        results[f"dir_{dir_path.replace('/', '_')}"] = exists
        
        if exists:
            # Count files in directory
            files = list(Path(dir_path).glob("*.tsx"))
            print(f"✅ {dir_path}: {len(files)} components")
        else:
            print(f"❌ Missing directory: {dir_path}")
    
    # Check specific components
    critical_components = [
        "components/new-ui/panels/property-panel.tsx",
        "components/new-ui/panels/assessment-panel.tsx",
        "components/new-ui/core/property-card.tsx",
        "components/new-ui/common/header.tsx"
    ]
    
    for component in critical_components:
        exists = os.path.exists(component)
        component_name = os.path.basename(component)
        results[f"component_{component_name}"] = exists
        
        if exists:
            print(f"✅ Component found: {component_name}")
        else:
            print(f"❌ Missing component: {component_name}")
    
    return results

def verify_import_paths() -> Dict[str, bool]:
    """Verify that import paths were updated correctly"""
    results = {}
    errors = []
    
    # Check a sample component for correct imports
    test_file = "components/new-ui/panels/property-panel.tsx"
    
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            content = f.read()
            
            # Check for correct import patterns
            has_ui_imports = '@/components/ui/' in content
            has_new_ui_imports = '@/components/new-ui/' in content or 'from "../' in content
            no_double_new_ui = 'new-ui/new-ui' not in content
            
            results['correct_ui_imports'] = has_ui_imports
            results['correct_new_ui_imports'] = has_new_ui_imports
            results['no_double_paths'] = no_double_new_ui
            
            if not has_ui_imports:
                errors.append("Missing UI component imports")
            if not no_double_new_ui:
                errors.append("Found double new-ui paths")
    else:
        results['imports_check'] = False
        errors.append(f"Could not check imports: {test_file} not found")
    
    if errors:
        print("⚠️ Import issues found:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Import paths correctly updated")
    
    return results

def verify_test_page() -> Dict[str, bool]:
    """Verify test page was created"""
    test_page = "app/new-ui-test/page.tsx"
    exists = os.path.exists(test_page)
    
    if exists:
        print(f"✅ Test page created: /new-ui-test")
    else:
        print(f"❌ Test page not found: {test_page}")
    
    return {'test_page': exists}

def verify_dependencies() -> Dict[str, bool]:
    """Verify required dependencies are installed"""
    results = {}
    
    if os.path.exists("package.json"):
        with open("package.json", 'r') as f:
            package_data = json.load(f)
            deps = {**package_data.get('dependencies', {}), 
                   **package_data.get('devDependencies', {})}
            
            required = [
                '@radix-ui/react-dialog',
                '@radix-ui/react-tabs',
                'lucide-react',
                'clsx',
                'tailwind-merge'
            ]
            
            for dep in required:
                installed = dep in deps
                results[f"dep_{dep.replace('/', '_').replace('@', '')}"] = installed
                
                if installed:
                    print(f"✅ Dependency installed: {dep}")
                else:
                    print(f"⚠️ Missing dependency: {dep}")
    else:
        print("❌ package.json not found")
        results['package_json'] = False
    
    return results

def verify_backup() -> Dict[str, bool]:
    """Verify backup was created"""
    backup_dir = "migratePRPs/backup"
    exists = os.path.exists(backup_dir) and os.path.isdir(backup_dir)
    
    if exists:
        # Check for recent backup
        backups = list(Path(backup_dir).glob("*"))
        if backups:
            latest = max(backups, key=os.path.getctime)
            print(f"✅ Backup found: {latest}")
            return {'backup_created': True, 'backup_recent': True}
    
    print("⚠️ No backup found")
    return {'backup_created': False}

def calculate_success_rate(results: Dict[str, Any]) -> float:
    """Calculate overall success rate"""
    all_checks = []
    
    for category_results in results.values():
        if isinstance(category_results, dict):
            all_checks.extend(category_results.values())
    
    if not all_checks:
        return 0.0
    
    passed = sum(1 for check in all_checks if check is True)
    return (passed / len(all_checks)) * 100

def main():
    print("\n" + "="*60)
    print("PRP-M1 VERIFICATION: Component Migration Foundation")
    print("="*60 + "\n")
    
    results = {
        'components': verify_component_migration(),
        'imports': verify_import_paths(),
        'test_page': verify_test_page(),
        'dependencies': verify_dependencies(),
        'backup': verify_backup()
    }
    
    # Calculate success rate
    success_rate = calculate_success_rate(results)
    
    # Determine status
    if success_rate >= 95:
        status = "PASSED"
        print(f"\n✅ VERIFICATION PASSED ({success_rate:.1f}%)")
    elif success_rate >= 80:
        status = "PARTIAL"
        print(f"\n⚠️ PARTIAL SUCCESS ({success_rate:.1f}%)")
    else:
        status = "FAILED"
        print(f"\n❌ VERIFICATION FAILED ({success_rate:.1f}%)")
    
    # Save results
    output = {
        'prp': 'M1',
        'timestamp': datetime.now().isoformat(),
        'success_rate': success_rate,
        'status': status,
        'detailed_results': results,
        'recommendations': []
    }
    
    # Add recommendations
    if success_rate < 100:
        if not results.get('backup', {}).get('backup_created'):
            output['recommendations'].append("Create backup before proceeding")
        if success_rate < 95:
            output['recommendations'].append("Fix missing components before continuing")
            output['recommendations'].append("Run: npm install to install missing dependencies")
    
    # Write results
    os.makedirs("migratePRPs/results", exist_ok=True)
    with open("migratePRPs/results/verify_m1_results.json", 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: migratePRPs/results/verify_m1_results.json")
    
    # Exit code based on success
    sys.exit(0 if status == "PASSED" else 1)

if __name__ == "__main__":
    main()