"""
Processing package for RAG-Anything and document extraction

WHY RAGProcessor IS IMPORTED LAZILY
-----------------------------------
`rag_processor` imports `raganything`, which is not installed in the test
environment or in the deployed service image. Importing it eagerly here made
the ENTIRE package unimportable without that one optional dependency — so
`from src.processing import SchemaExtractor` failed with
`ModuleNotFoundError: No module named 'raganything'`, even though
SchemaExtractor has nothing to do with RAG.

That is what kept tests/test_integration.py quarantined since 2026-05-23: it
imports SimplePDFProcessor, which triggers this file, which demanded a library
nothing in `services/` uses. Checked before changing: `RAGProcessor` appears in
two one-off scripts (lightrag_compliance_processor.py, real_lightrag_processor.py)
and in no deployed code path.

Accessing `RAGProcessor` still raises — with the original ImportError attached,
so the message names the missing library rather than something vague. The
dependency is required to USE it, not to import its neighbours.
"""

from .schema_extractor import SchemaExtractor
from .spatial_mapper import determine_former_council_area

__all__ = [
    'RAGProcessor',
    'SchemaExtractor',
    'determine_former_council_area'
]


def __getattr__(name: str):
    """PEP 562 module-level __getattr__ — defers the heavy import to first use.

    Deliberately not a try/except at import time setting RAGProcessor = None:
    a None would let `RAGProcessor()` fail later with an unhelpful
    'NoneType is not callable' at some distance from the real cause. Raising
    here keeps the original ImportError text, which names `raganything`.
    """
    if name == 'RAGProcessor':
        from .rag_processor import RAGProcessor as _RAGProcessor
        return _RAGProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
