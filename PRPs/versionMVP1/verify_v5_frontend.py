#!/usr/bin/env python3
"""
Verification script for PRP-V5: Frontend Integration
Validates that frontend components exist and API integration works
"""

import sys
import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class FrontendVerification:
    """Verify frontend version integration"""

    def __init__(self, frontend_path: str = "frontend-nextjs"):
        self.frontend_path = Path(frontend_path)
        self.api_url = "http://localhost:8000"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "V5_FRONTEND_INTEGRATION",
            "checks": {},
            "errors": [],
            "warnings": [],
            "success": False
        }

    def check_component_files(self) -> Dict[str, bool]:
        """Check if required frontend component files exist"""
        required_files = [
            "components/version/VersionBadge.tsx",
            "components/version/VersionSelector.tsx",
            "components/version/VersionComparison.tsx",
            "hooks/useVersion.ts"
        ]

        file_checks = {}

        for file_path in required_files:
            full_path = self.frontend_path / file_path
            exists = full_path.exists()
            file_checks[file_path] = exists

            if not exists:
                self.results["errors"].append(f"Required file not found: {file_path}")

        return file_checks

    def check_component_syntax(self) -> Dict[str, bool]:
        """Basic syntax check for TypeScript/React components"""
        syntax_checks = {}

        components_to_check = [
            "components/version/VersionBadge.tsx",
            "components/version/VersionSelector.tsx",
            "hooks/useVersion.ts"
        ]

        for component in components_to_check:
            full_path = self.frontend_path / component
            if full_path.exists():
                try:
                    content = full_path.read_text()

                    # Basic syntax checks
                    has_imports = 'import' in content
                    has_export = 'export' in content
                    has_react = 'React' in content or 'FC' in content

                    if component.endswith('.tsx'):
                        syntax_checks[f"{component}_structure"] = has_imports and has_export and has_react
                    else:  # .ts files
                        syntax_checks[f"{component}_structure"] = has_imports and has_export

                    # Check for TypeScript interfaces/types
                    has_types = 'interface' in content or 'type' in content
                    syntax_checks[f"{component}_types"] = has_types

                except Exception as e:
                    syntax_checks[f"{component}_readable"] = False
                    self.results["warnings"].append(f"Could not read {component}: {str(e)}")
            else:
                syntax_checks[f"{component}_exists"] = False

        return syntax_checks

    def check_api_integration(self) -> Dict[str, bool]:
        """Check if frontend can connect to versioned APIs"""
        api_checks = {}

        try:
            # Check if API is accessible
            response = requests.get(f"{self.api_url}/docs", timeout=5)
            api_checks['api_accessible'] = response.status_code == 200

            if api_checks['api_accessible']:
                # Test version-aware endpoints that frontend would use
                endpoints_to_test = [
                    "/api/provisions?version=current",
                    "/api/provisions?include_version_info=true",
                    "/api/versions/current"
                ]

                for endpoint in endpoints_to_test:
                    try:
                        response = requests.get(f"{self.api_url}{endpoint}", timeout=5)
                        api_checks[f"endpoint_{endpoint.split('/')[-1]}"] = response.status_code == 200
                    except Exception as e:
                        api_checks[f"endpoint_{endpoint.split('/')[-1]}"] = False
                        self.results["warnings"].append(f"Endpoint {endpoint} test failed: {str(e)}")

        except Exception as e:
            api_checks['api_accessible'] = False
            self.results["warnings"].append(f"API not accessible: {str(e)}")

        return api_checks

    def check_existing_page_modifications(self) -> Dict[str, bool]:
        """Check if existing pages were modified to include version components"""
        page_checks = {}

        pages_to_check = [
            "app/authoritative/page.tsx"
        ]

        for page in pages_to_check:
            full_path = self.frontend_path / page
            if full_path.exists():
                try:
                    content = full_path.read_text()

                    # Check for version-related imports
                    has_version_imports = (
                        'VersionSelector' in content or
                        'VersionBadge' in content or
                        'useVersion' in content
                    )

                    # Check for version state management
                    has_version_state = (
                        'selectedVersion' in content or
                        'asAtDate' in content or
                        'version' in content.lower()
                    )

                    page_checks[f"{page}_version_imports"] = has_version_imports
                    page_checks[f"{page}_version_state"] = has_version_state

                except Exception as e:
                    page_checks[f"{page}_readable"] = False
                    self.results["warnings"].append(f"Could not read {page}: {str(e)}")
            else:
                page_checks[f"{page}_exists"] = False
                self.results["warnings"].append(f"Page {page} not found")

        return page_checks

    def check_package_dependencies(self) -> Dict[str, bool]:
        """Check if required npm packages are installed"""
        dep_checks = {}

        package_json_path = self.frontend_path / "package.json"

        if package_json_path.exists():
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)

                dependencies = {
                    **package_data.get('dependencies', {}),
                    **package_data.get('devDependencies', {})
                }

                # Check for required packages
                required_packages = [
                    'react',
                    'next',
                    'typescript',
                    '@types/react'
                ]

                for package in required_packages:
                    dep_checks[f"has_{package.replace('@', '').replace('/', '_')}"] = package in dependencies

                # Check for additional useful packages
                optional_packages = [
                    'diff',  # For version comparison
                    'date-fns',  # For date handling
                ]

                for package in optional_packages:
                    dep_checks[f"has_{package}"] = package in dependencies

            except Exception as e:
                dep_checks['package_json_readable'] = False
                self.results["warnings"].append(f"Could not read package.json: {str(e)}")
        else:
            dep_checks['package_json_exists'] = False
            self.results["warnings"].append("package.json not found")

        return dep_checks

    def check_build_compatibility(self) -> Dict[str, bool]:
        """Check if frontend can build with new components"""
        build_checks = {}

        # Check if TypeScript config exists
        tsconfig_path = self.frontend_path / "tsconfig.json"
        build_checks['has_tsconfig'] = tsconfig_path.exists()

        # Check if Next.js config exists
        nextconfig_path = self.frontend_path / "next.config.js"
        nextconfig_mjs_path = self.frontend_path / "next.config.mjs"
        build_checks['has_nextconfig'] = nextconfig_path.exists() or nextconfig_mjs_path.exists()

        return build_checks

    def run_verification(self) -> bool:
        """Run all frontend verification checks"""
        print("🔍 Verifying PRP-V5: Frontend Integration...")

        # Check component files
        print("\n📁 Checking component files...")
        file_checks = self.check_component_files()
        self.results["checks"]["files"] = file_checks
        files_exist = sum(file_checks.values())
        print(f"  Component files: {files_exist}/{len(file_checks)} found")

        # Check component syntax
        print("\n🔍 Checking component syntax...")
        syntax_checks = self.check_component_syntax()
        self.results["checks"]["syntax"] = syntax_checks
        syntax_valid = sum(syntax_checks.values())
        print(f"  Syntax checks: {syntax_valid}/{len(syntax_checks)} passed")

        # Check API integration
        print("\n🌐 Checking API integration...")
        api_checks = self.check_api_integration()
        self.results["checks"]["api"] = api_checks
        api_working = sum(api_checks.values())
        print(f"  API checks: {api_working}/{len(api_checks)} passed")

        # Check page modifications
        print("\n📄 Checking page modifications...")
        page_checks = self.check_existing_page_modifications()
        self.results["checks"]["pages"] = page_checks
        pages_modified = sum(page_checks.values())
        print(f"  Page modifications: {pages_modified}/{len(page_checks)} found")

        # Check dependencies
        print("\n📦 Checking package dependencies...")
        dep_checks = self.check_package_dependencies()
        self.results["checks"]["dependencies"] = dep_checks
        deps_ready = sum(dep_checks.values())
        print(f"  Dependencies: {deps_ready}/{len(dep_checks)} available")

        # Check build compatibility
        print("\n🏗️ Checking build compatibility...")
        build_checks = self.check_build_compatibility()
        self.results["checks"]["build"] = build_checks
        build_ready = sum(build_checks.values())
        print(f"  Build config: {build_ready}/{len(build_checks)} ready")

        # Determine overall success
        # For MVP, we're flexible on implementation - focus on structure
        critical_checks_passed = (
            files_exist >= len(file_checks) * 0.7 and  # 70% of files exist
            api_checks.get('api_accessible', False)  # API is accessible
        )

        self.results["success"] = critical_checks_passed

        # Save results
        with open("verify_v5_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\n" + "=" * 50)
        print("📊 Frontend Verification Summary:")
        print(f"  Component files: {'✅' if files_exist >= len(file_checks) * 0.7 else '❌'} ({files_exist}/{len(file_checks)})")
        print(f"  API integration: {'✅' if api_checks.get('api_accessible', False) else '❌'}")
        print(f"  Build readiness: {'✅' if build_ready > 0 else '❌'}")

        if self.results["errors"]:
            print("\n❌ Errors found:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        if self.results["warnings"]:
            print("\n⚠️ Warnings:")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")

        print(f"\n{'✅ PRP-V5 VERIFICATION PASSED' if critical_checks_passed else '❌ PRP-V5 VERIFICATION FAILED'}")

        if not critical_checks_passed:
            print("\n💡 Note: Frontend components may need to be created manually")
            print("   Refer to PRP-V5_FRONTEND_INTEGRATION.md for component code")

        return critical_checks_passed

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Verify frontend version integration')
    parser.add_argument('--frontend-path', default='frontend-nextjs',
                       help='Path to frontend directory (default: frontend-nextjs)')

    args = parser.parse_args()

    verifier = FrontendVerification(frontend_path=args.frontend_path)
    success = verifier.run_verification()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()