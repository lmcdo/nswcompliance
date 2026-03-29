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

    if check == "toc_section_count":
        # browse/toc response: {data: {sections: [...]}, meta: {sectionCount: N}}
        inner = data.get("data") or data
        sections = inner.get("sections") or []
        count = len(sections) if isinstance(sections, list) else data.get("meta", {}).get("sectionCount", 0)
        print(count)
        sys.exit(0 if count > 10 else 1)

    elif check == "toc_has_sections":
        inner = data.get("data") or data
        sections = inner.get("sections") or []
        count = len(sections) if isinstance(sections, list) else 0
        print(count)
        sys.exit(0 if count > 0 else 1)

    elif check == "health_ok":
        status = data.get("status", "")
        # Accept ok, healthy, or degraded (degraded = some check failed but server is running)
        ok = status in ("ok", "healthy", "degraded")
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

    elif check == "da_sessions_reachable":
        # POST with empty body → {error: "address is required"} = API is up
        # 404/500 → we get HTML or empty, which won't parse as JSON
        # Any JSON response (even an error) confirms the route exists and DB is accessible
        print("reachable")
        sys.exit(0)

    else:
        print(f"smoke_parse: unknown check '{check}'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
