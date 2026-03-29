"""
Helper for smoke_test.sh — reads JSON from stdin, runs named check, prints result.
Usage: curl ... | python3 scripts/smoke_parse.py <check_name>
Exits 0 on pass, 1 on fail, 2 on bad input.
"""
import sys
import json

def main():
    if len(sys.argv) < 2:
        print("usage: smoke_parse.py <check>", file=sys.stderr)
        sys.exit(2)

    check = sys.argv[1]

    try:
        raw = sys.stdin.read()
        d = json.loads(raw)
    except Exception as e:
        print(f"PARSE_ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    data = d.get("data", {})

    if check == "leichhardt_provision_count":
        layers = data.get("by_layer", [])
        total = sum(len(layer.get("provisions", [])) for layer in layers)
        print(total)
        # >50 provisions expected for a Leichhardt residential address
        sys.exit(0 if total > 50 else 1)

    elif check == "leichhardt_section_count":
        by_toc = data.get("by_toc", {})
        sections = sum(len(p.get("sections", {})) for p in by_toc.values())
        print(sections)
        # >10 sections expected once TOC JOIN is working
        sys.exit(0 if sections > 10 else 1)

    elif check == "marrickville_part_count":
        by_toc = data.get("by_toc", {})
        parts = len(by_toc)
        print(parts)
        sys.exit(0 if parts > 3 else 1)

    elif check == "health_ok":
        status = d.get("status", "")
        print(status)
        # health endpoint returns "healthy" or "ok"
        sys.exit(0 if status in ("ok", "healthy") else 1)

    elif check == "section_response_saved":
        # Checks if a section response POST returned success
        success = d.get("success", False) or d.get("id") is not None
        print("success" if success else "failed")
        sys.exit(0 if success else 1)

    else:
        print(f"unknown check: {check}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
