#!/usr/bin/env python3
"""
CLI wrapper for version_manager.py
Provides command-line interface for version management operations
"""

import argparse
import json
import sys
from datetime import date, datetime
from version_manager import VersionManager, DocumentType, VersionStatus

def main():
    parser = argparse.ArgumentParser(description='NSW Document Version Manager CLI')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Get current version
    current_parser = subparsers.add_parser('get_current_version', help='Get current version')
    current_parser.add_argument('--document-type', required=True, choices=['SEPP', 'LEP', 'DCP'])
    current_parser.add_argument('--document-identifier', required=True)

    # Get version at date
    date_parser = subparsers.add_parser('get_version_at_date', help='Get version at specific date')
    date_parser.add_argument('--document-type', required=True, choices=['SEPP', 'LEP', 'DCP'])
    date_parser.add_argument('--document-identifier', required=True)
    date_parser.add_argument('--target-date', required=True)

    # Get statistics
    stats_parser = subparsers.add_parser('get_statistics', help='Get version statistics')

    # Get comparison
    comparison_parser = subparsers.add_parser('get_comparison', help='Get version comparison')
    comparison_parser.add_argument('--document-type', required=True, choices=['SEPP', 'LEP', 'DCP'])
    comparison_parser.add_argument('--document-identifier', required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        with VersionManager() as vm:
            if args.command == 'get_current_version':
                result = vm.get_current_version(
                    DocumentType(args.document_type),
                    args.document_identifier
                )
                if result:
                    print(json.dumps(result.dict(), default=str))
                else:
                    print(json.dumps({"error": "Version not found"}))

            elif args.command == 'get_version_at_date':
                target_date = datetime.fromisoformat(args.target_date).date()
                result = vm.get_version_at_date(
                    DocumentType(args.document_type),
                    args.document_identifier,
                    target_date
                )
                if result:
                    print(json.dumps(result.dict(), default=str))
                else:
                    print(json.dumps({"error": "Version not found for date"}))

            elif args.command == 'get_statistics':
                result = vm.get_version_statistics()
                print(json.dumps(result, default=str))

            elif args.command == 'get_comparison':
                current, previous = vm.get_version_comparison(
                    DocumentType(args.document_type),
                    args.document_identifier
                )
                result = {
                    "current": current.dict() if current else None,
                    "previous": previous.dict() if previous else None
                }
                print(json.dumps(result, default=str))

        return 0

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
