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

import os
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

# ── Opt-out for tests that need a REAL database ──────────────────────────────
# The stub below replaces psycopg2 whenever it has not already been imported —
# which, at conftest time, is always. So a database test could never obtain a
# real connection even with DATABASE_URL set: psycopg2.connect() returned a
# MagicMock and assertions failed with things like
# "'>' not supported between instances of 'MagicMock' and 'int'".
#
# That is what kept tests/test_lga_coverage.py — the LGA-onboarding gate —
# unrunnable even after its syntax was repaired.
#
# Deliberately OPT-IN via an environment variable rather than "use the real
# library whenever it happens to be installed". The automatic version would
# silently change the import environment for all 4,100+ tests on any machine
# with psycopg2 present, and tests that currently rely on the stub (expecting
# a MagicMock cursor) would start attempting real connections. Opt-in has a
# blast radius of exactly the runs that ask for it:
#
#     PYTEST_REAL_DB=1 DATABASE_URL=postgresql://... pytest -m database
_REAL_DB = os.environ.get("PYTEST_REAL_DB") == "1"
_DB_MODULES = {"psycopg2", "psycopg2.extras"}

for mod_name in _MOCK_MODULES:
    if _REAL_DB and mod_name in _DB_MODULES:
        continue  # let the genuine library be imported normally
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# ── Special handling: requests exception hierarchy ──────────────────────────
# dem_service.py catches `requests.RequestException`. MagicMock attributes are
# not real exception classes, so `except MockObj:` crashes with TypeError.
# Provide real exception classes so catch clauses work.
requests_mock = sys.modules["requests"]
if isinstance(requests_mock, MagicMock):

    class _RequestException(IOError):
        pass

    class _HTTPError(_RequestException):
        pass

    class _ConnectionError(_RequestException):
        pass

    class _Timeout(_RequestException):
        pass

    requests_mock.RequestException = _RequestException
    requests_mock.HTTPError = _HTTPError
    requests_mock.ConnectionError = _ConnectionError
    requests_mock.Timeout = _Timeout

# ── Special handling: pyproj Transformer ─────────────────────────────────────
# flood_truth.py does `Transformer.from_crs(...)`.
pyproj_mock = sys.modules["pyproj"]
transformer_instance = MagicMock()
transformer_instance.transform = MagicMock(return_value=(0.0, 0.0))
pyproj_mock.Transformer.from_crs = MagicMock(return_value=transformer_instance)

# ── Special handling: psycopg2.extras.RealDictCursor ─────────────────────────
# Guarded: under PYTEST_REAL_DB=1 the stub is skipped, so this key is absent and
# an unguarded lookup raised KeyError while LOADING conftest — which kills the
# entire run before a single test is collected. Only patch the stub, never the
# real library: RealDictCursor is genuine there and replacing it with a
# MagicMock would defeat the point of asking for a real database.
if _REAL_DB:
    pass
else:
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
    sys.modules["numpy.random"] = MagicMock()

# ── rasterio: try real import, mock only if unavailable ─────────────────────
try:
    import rasterio  # noqa: F401
except ImportError:
    rio_mock = MagicMock()
    sys.modules["rasterio"] = rio_mock
    sys.modules["rasterio.transform"] = MagicMock()
    sys.modules["rasterio.crs"] = MagicMock()
    # A MagicMock does not satisfy `import rasterio.windows` — Python resolves a
    # dotted import through sys.modules, not through attribute access, and raises
    # "'rasterio' is not a package". Every submodule that any module under test
    # imports by name has to be registered, exactly as numpy.typing/numpy.random
    # are above. Missing this made 6 flood_truth tests fail in a clean
    # requirements-test.txt environment while passing in a dev checkout that has
    # real rasterio installed — the suite silently depended on the fat env.
    sys.modules["rasterio.windows"] = MagicMock()
    sys.modules["rasterio.warp"] = MagicMock()
    sys.modules["rasterio.mask"] = MagicMock()
    sys.modules["rasterio.features"] = MagicMock()
    sys.modules["rasterio.enums"] = MagicMock()

# ── whitebox: try real import, mock only if unavailable ─────────────────────
try:
    import whitebox  # noqa: F401
except ImportError:
    sys.modules["whitebox"] = MagicMock()
