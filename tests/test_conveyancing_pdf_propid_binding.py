"""The PDF report must bind coordinates to the resolved property, never the caller triple.

Companion to test_conveyancing_propid_binding, which covers the behaviour of
_resolve_property itself. generate_conveyancing_pdf previously trusted the caller's
prop_id (int(req.prop_id)) and used req.lat / req.lng for every spatial fetch, so a
direct /conveyancing/pdf caller could mix one property's controls and valuation with
another property's overlays, strata and DAs — the same cross-property defect fixed in
run_conveyancing (#811).

The handler is a large orchestrator (parallel fetchers, PDF generation, R2 upload),
so this is a structural guard in the style of test_conveyancing_nearby_da_council.
It uses the AST (not a text scan) so comments and strings can't satisfy or break it,
and it isolates the cache-miss branch so a regression there is caught even if the
cache-hit fallback still resolves authoritatively.
"""

import ast
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_TREE = ast.parse((_ROOT / "services" / "conveyancing.py").read_text(encoding="utf-8"))


def _pdf_func() -> ast.FunctionDef:
    for node in ast.walk(_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == "generate_conveyancing_pdf":
            return node
    raise AssertionError("generate_conveyancing_pdf not found in conveyancing.py")


def _req_attrs(nodes) -> list[str]:
    """Attribute names read off a `req.` access within the given AST node(s)."""
    stmts = nodes if isinstance(nodes, list) else [nodes]
    found = []
    for stmt in stmts:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "req":
                found.append(n.attr)
    return found


def _called_names(nodes) -> set[str]:
    stmts = nodes if isinstance(nodes, list) else [nodes]
    names = set()
    for stmt in stmts:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                names.add(n.func.id)
    return names


def _if_cached(fn: ast.FunctionDef) -> ast.If:
    for n in ast.walk(fn):
        if isinstance(n, ast.If):
            names = {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)}
            if "cached" in names:
                return n
    raise AssertionError("could not locate the cache-hit branch in generate_conveyancing_pdf")


class TestPdfCoordinateBinding:
    def test_no_code_path_reads_request_coordinates(self):
        # AST-level: no executable req.lat / req.lng access anywhere in the handler.
        attrs = _req_attrs(_pdf_func())
        assert "lat" not in attrs and "lng" not in attrs, (
            f"generate_conveyancing_pdf reads req.lat/req.lng in code (attrs={attrs}); "
            "all coordinates must be the resolved, property-bound lat/lng"
        )

    def test_handler_never_trusts_caller_prop_id(self):
        # prop_id must come from the cache or from _resolve_property, never req.prop_id.
        attrs = _req_attrs(_pdf_func())
        assert "prop_id" not in attrs, (
            "generate_conveyancing_pdf must not read req.prop_id; the property is "
            "resolved authoritatively"
        )

    # req.address (to resolve) and req.report_id (cache key / logging) are legitimate;
    # only the caller-controlled IDENTITY fields must never be trusted here.
    _FORBIDDEN = {"lat", "lng", "prop_id"}

    def test_cache_miss_branch_resolves_authoritatively(self):
        else_body = _if_cached(_pdf_func()).orelse
        assert "_resolve_property" in _called_names(else_body), (
            "the cache-miss (else) branch must bind the property via "
            "_resolve_property(req), not caller-derived values"
        )
        leaked = self._FORBIDDEN.intersection(_req_attrs(else_body))
        assert not leaked, f"the cache-miss branch trusts caller identity fields: {leaked}"

    def test_cache_hit_requires_cached_coordinates(self):
        # The cache-hit guard must require the entry's own lat/lng, so a coordless
        # entry falls through to authoritative resolution instead of being paired
        # with request-supplied coordinates.
        node = _if_cached(_pdf_func())
        test_src = ast.dump(node.test)
        assert "'lat'" in test_src and "'lng'" in test_src, (
            "the cache-hit guard must require cached lat/lng present"
        )
        leaked = self._FORBIDDEN.intersection(_req_attrs(node.body))
        assert not leaked, f"the cache-hit branch trusts caller identity fields: {leaked}"
