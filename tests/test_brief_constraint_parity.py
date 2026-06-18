"""Regression guard: constraint-arithmetic parity across the two brief paths.

The Intelligence Brief is assembled twice — `run_intelligence_brief`
(non-streaming JSON) and `_generate_brief_sse` (SSE, the path the live UI uses).
The capacity headline (`constraint_arithmetic`: realistic yield + binding
constraint + #500 DCP-adjusted GFA) had drifted OUT of the streaming path, so
the live brief silently lost it while the non-streaming path kept it.

These are deliberately source-level checks: the two ~500-line paths are not
driven end-to-end in tests (too many fetches to mock), so this guards the one
thing that matters — both paths must compute and attach constraint_arithmetic —
and fails loudly if a future edit drops it from either path again.
"""

import inspect

from services import intelligence_brief as ib


def test_both_brief_paths_attach_constraint_arithmetic():
    non_streaming = inspect.getsource(ib.run_intelligence_brief)
    streaming = inspect.getsource(ib._generate_brief_sse)
    assert "constraint_arithmetic=" in non_streaming, \
        "non-streaming brief no longer attaches constraint_arithmetic"
    assert "constraint_arithmetic=" in streaming, \
        "streaming brief no longer attaches constraint_arithmetic (drift regressed)"


def test_streaming_path_computes_and_emits_constraint_arithmetic():
    streaming = inspect.getsource(ib._generate_brief_sse)
    assert "compute_constraint_arithmetic" in streaming, \
        "streaming path no longer computes constraint arithmetic"
    assert '"constraint_arithmetic"' in streaming, \
        "streaming path no longer emits the constraint_arithmetic SSE section"


def test_development_brief_model_carries_constraint_arithmetic():
    # The field both paths populate must exist on the model.
    assert "constraint_arithmetic" in ib.DevelopmentBrief.model_fields
