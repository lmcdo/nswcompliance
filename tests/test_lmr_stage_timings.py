# prior-art-checked: a grep of tests/ for "lmr stage" and _stage finds none; this is the first test of the stage-timing helper added 2026-11-26 to read where a slow evidence call spends its time.
"""The stage timer logs how long each stage took and changes nothing else."""
import logging

import pytest

from services import lmr_area_inputs as inp


def test_it_returns_what_the_function_returns_and_logs_the_stage_and_seconds(caplog):
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        assert inp._stage("demo", lambda a, b=2: a + b, 1, b=5) == 6
    assert any(r.getMessage().startswith("lmr stage demo ") and r.getMessage().endswith("s") for r in caplog.records)


def test_an_exception_passes_through_and_the_stage_is_still_logged(caplog):
    def boom():
        raise ValueError("x")

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        with pytest.raises(ValueError):
            inp._stage("failing", boom)
    assert any("lmr stage failing" in r.getMessage() for r in caplog.records)


def test_the_logger_is_uvicorns_so_the_line_reaches_the_service_log():
    assert inp._STAGE_LOG.name == "uvicorn.error"


def test_the_evidence_endpoints_own_timer_passes_values_and_errors_through_and_logs(caplog):
    from services import housing_sepp_gates_api as api

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        assert api._timed("demo_api", lambda a: a * 2, 4) == 8
        with pytest.raises(KeyError):
            api._timed("failing_api", lambda: {}["x"])
    msgs = [r.getMessage() for r in caplog.records]
    assert any(m.startswith("lmr stage demo_api ") for m in msgs) and any(m.startswith("lmr stage failing_api ") for m in msgs)
