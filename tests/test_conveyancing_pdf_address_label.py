"""The PDF report's address label must come from the resolved/cached property, not the caller.

On a cache hit, generate_conveyancing_pdf renders data belonging to the cached
report_id. If the address LABEL (and the address-derived lookups: shadow, structures,
former-council) came from req.address, a caller could pair a valid report_id for a
clean property with a different property's address and produce a due-diligence PDF
showing one property's data under another's address — a forgery vector.

This guards the invariant structurally (AST, so comments/strings can't fool it):
req.address may only appear as the right-hand side of an `address = ...` binding; the
label, response and every address-derived call must use that bound `address`.
"""

import ast
from pathlib import Path

_TREE = ast.parse((Path(__file__).parent.parent / "services" / "conveyancing.py").read_text(encoding="utf-8"))


def _pdf_func() -> ast.FunctionDef:
    for node in ast.walk(_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == "generate_conveyancing_pdf":
            return node
    raise AssertionError("generate_conveyancing_pdf not found")


def _address_binding_values(fn: ast.FunctionDef) -> list[ast.expr]:
    """RHS expressions of every `address = ...` assignment in the function."""
    values = []
    for n in ast.walk(fn):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "address"):
            values.append(n.value)
    return values


def _req_address_nodes(fn: ast.FunctionDef) -> list[ast.Attribute]:
    return [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
        and n.value.id == "req" and n.attr == "address"
    ]


def _if_cached(fn: ast.FunctionDef) -> ast.If:
    for n in ast.walk(fn):
        if isinstance(n, ast.If) and any(
            isinstance(x, ast.Name) and x.id == "cached" for x in ast.walk(n.test)
        ):
            return n
    raise AssertionError("cache-hit branch not found")


class TestPdfAddressLabelBinding:
    def test_req_address_only_feeds_the_local_binding(self):
        fn = _pdf_func()
        binding_values = _address_binding_values(fn)
        req_addr = _req_address_nodes(fn)
        assert req_addr, "expected req.address in the address bindings"
        for node in req_addr:
            assert any(node in set(ast.walk(v)) for v in binding_values), (
                "req.address is used outside an `address = ...` binding — it must never "
                "reach a fetcher, the PDF label, or the response directly (a cache hit "
                "would then render cached data under the caller's address)"
            )

    def test_cache_hit_binds_address_from_cache(self):
        for stmt in _if_cached(_pdf_func()).body:
            for n in ast.walk(stmt):
                if (isinstance(n, ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "address"
                        and "cached" in ast.dump(n.value)):
                    return
        raise AssertionError("the cache-hit branch must bind address from the cached entry")

    def test_pdf_label_uses_bound_address(self):
        gen = None
        for n in ast.walk(_pdf_func()):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "generate_pdf":
                gen = n
        assert gen is not None and len(gen.args) >= 2, "generate_pdf call not found"
        assert isinstance(gen.args[1], ast.Name) and gen.args[1].id == "address", (
            "generate_pdf must be labelled with the bound address, not req.address"
        )
