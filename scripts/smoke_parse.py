#!/usr/bin/env python3
"""JSON parser for smoke tests — called by smoke_test.sh.

Usage: python3 smoke_parse.py <check_name>
Reads JSON from stdin. Exits 0 on pass, 1 on fail.

Checks:
  leichhardt_provision_count  — provisions array length > 50
  leichhardt_section_count    — distinct toc_section_number values > 10
  marrickville_part_count     — distinct part values > 3
  health_ok                   — status field is 'ok' or 'healthy'
  section_response_saved      — response indicates successful save
"""
import json
import sys


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: smoke_parse.py <check_name>", file=sys.stderr)
        sys.exit(1)

    check = sys.argv[1]

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"smoke_parse: invalid JSON — {e}", file=sys.stderr)
        sys.exit(1)

    if check == "leichhardt_provision_count":
        provisions = data.get("provisions") or data.get("data") or []
        if isinstance(provisions, list):
            count = len(provisions)
        else:
            count = 0
        print(count)
        sys.exit(0 if count > 50 else 1)

    elif check == "leichhardt_section_count":
        provisions = data.get("provisions") or data.get("data") or []
        sections = set()
        for p in provisions:
            sec = p.get("toc_section_number") or p.get("section_number")
            if sec:
                sections.add(sec)
        count = len(sections)
        print(count)
        sys.exit(0 if count > 10 else 1)

    elif check == "marrickville_part_count":
        provisions = data.get("provisions") or data.get("data") or []
        parts = set()
        for p in provisions:
            part = p.get("v2_dcp_part") or p.get("part") or p.get("v2_part")
            if part:
                parts.add(part)
        count = len(parts)
        print(count)
        sys.exit(0 if count > 3 else 1)

    elif check == "health_ok":
        status = data.get("status", "")
        ok = status in ("ok", "healthy")
        print(status)
        sys.exit(0 if ok else 1)

    elif check == "section_response_saved":
        # Accept any non-error response: {id}, {success: true}, {saved: true}
        if data.get("error") or data.get("errors"):
            print("error response", file=sys.stderr)
            sys.exit(1)
        ok = bool(data.get("id") or data.get("success") or data.get("saved"))
        print("saved" if ok else "not saved")
        sys.exit(0 if ok else 1)

    else:
        print(f"smoke_parse: unknown check '{check}'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
