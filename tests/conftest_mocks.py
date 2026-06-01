"""
Pre-load mock modules into sys.modules so that pure-logic unit tests
can import service modules without requiring production dependencies
(psycopg2, pyproj, requests, etc.).

This file must be imported BEFORE any test file is collected.
conftest.py handles this via a top-level import.

Strategy: only mock modules that require native compilation or external
services. Let pure-Python packages (pydantic, fastapi) be real imports
so their behavior is tested accurately.
"""

import sys
from unittest.mock import MagicMock

# ── Modules to mock ──────────────────────────────────────────────────────────
# Only mock modules that won't be installed in the test environment.
# pydantic, fastapi: installed as test deps (pure Python, needed for model tests)
# psycopg2, pyproj, requests: heavy/native deps, not needed for pure-logic tests

_MOCK_MODULES = [
    # Database (requires libpq native library)
    "psycopg2",
    "psycopg2.extras",
    # HTTP client (tests mock all HTTP calls)
    "requests",
    # Geo projection (requires PROJ native library)
    "pyproj",
    # Internal module not on PYTHONPATH in test env
    "audit_trail",
]

for mod_name in _MOCK_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# ── Special handling: pyproj Transformer ─────────────────────────────────────
# flood_truth.py does `Transformer.from_crs(...)`.
pyproj_mock = sys.modules["pyproj"]
transformer_instance = MagicMock()
pyproj_mock.Transformer.from_crs = MagicMock(return_value=transformer_instance)

# ── Special handling: psycopg2.extras.RealDictCursor ─────────────────────────
psycopg2_extras = sys.modules["psycopg2.extras"]
psycopg2_extras.RealDictCursor = MagicMock()

# ── Special handling: audit_trail ────────────────────────────────────────────
# Services import DataSourceQuery, log_audit_trail, get_current_disclaimer_version.
audit_mock = sys.modules["audit_trail"]
# DataSourceQuery("name", url, params) — positional args hit spec/wraps/name
# in MagicMock.__init__, which locks attribute access. Use a lambda factory instead.
audit_mock.DataSourceQuery = lambda *a, **kw: MagicMock()
audit_mock.log_audit_trail = MagicMock()
audit_mock.get_current_disclaimer_version = MagicMock(return_value="1.0")

# ── numpy: try real import, mock only if unavailable ─────────────────────────
try:
    import numpy  # noqa: F401
except ImportError:
    np_mock = MagicMock()
    np_mock._is_mock = True
    # pytest.approx internally does `isinstance(val, np.bool_)` when numpy
    # is in sys.modules. MagicMock as arg 2 of isinstance() crashes.
    # Provide real types so isinstance() works.
    np_mock.bool_ = type("bool_", (int,), {})
    np_mock.float64 = type("float64", (float,), {})
    np_mock.int64 = type("int64", (int,), {})
    np_mock.ndarray = type("ndarray", (), {})
    sys.modules["numpy"] = np_mock
    sys.modules["numpy.typing"] = MagicMock()
