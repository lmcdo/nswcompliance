"""run_numeric_extraction is deleted, and must not come back by accident.

WHAT IT WAS. A seventh enrichment phase that filtered on `v2_enriched_at` and
wrote `v2_extracted_values`, `v2_enrichment_version` and `v2_enriched_at`. None of
those three columns exists on any table in this database (checked against
information_schema, 2026-09-11); only `v2_has_numeric_value`, the fourth column it
wrote, exists. It targeted a four-column schema that was replaced by the
`v2_extracted_rules` + `v2_extraction_status` pair.

WHY DELETED RATHER THAN FIXED. `enrichment/rule_extraction_pipeline.py` already
owns and writes that pair -- it is the only code in the repo with a
`SET v2_extracted_rules`, apart from a one-off single-row repair script. Fixing
the wrapper would have meant repointing it at columns another pipeline owns,
creating a second writer for one field. Two writers for one fact is the
duplication that left three enrichment phases wired to nothing (#1084).

These are source-level assertions because the thing being tested is an absence.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from enrichment import pipeline  # noqa: E402

PIPELINE_SRC = (ROOT / "enrichment" / "pipeline.py").read_text(encoding="utf-8")

#: The columns the deleted phase read and wrote, minus the one that exists.
DEAD_COLUMNS = ("v2_enriched_at", "v2_extracted_values", "v2_enrichment_version")


def test_the_function_is_gone():
    assert not hasattr(pipeline, "run_numeric_extraction"), (
        "run_numeric_extraction is back. It cannot run: it references three "
        "columns that do not exist. Wire enrichment/rule_extraction_pipeline.py "
        "instead -- that is what writes v2_extracted_rules."
    )


def test_numeric_is_not_an_offered_phase():
    """The CLI choice outlived the function once already. A `--phase numeric` that
    resolves to nothing is a command that fails at the worst moment."""
    assert '"numeric"' not in PIPELINE_SRC.split("choices=[")[1].split("]")[0], (
        "--phase numeric is still offered on the command line"
    )


def test_no_query_in_the_pipeline_references_a_column_that_does_not_exist():
    """Comments may NAME the dead columns -- explaining why they are gone is the
    point of those comments. What must not survive is a reference inside code.

    Scoped to non-comment lines, and to SQL-ish context, so the explanatory
    comment above STANDARD_ENRICHMENT_PHASES does not fail its own explanation.
    """
    offenders = []
    for n, line in enumerate(PIPELINE_SRC.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for col in DEAD_COLUMNS:
            if col in line:
                offenders.append(f"{n}: {stripped[:90]}")
    assert not offenders, (
        "these lines reference a column that exists on no table:\n  "
        + "\n  ".join(offenders)
    )


def test_the_extractor_class_itself_was_not_deleted():
    """The confusable negative. NumericExtractor is used by
    rule_extraction_pipeline, by tests, and by around ten debug scripts. Only the
    dead wrapper was removed -- deleting the class would have been a much larger
    and quite different change."""
    from enrichment.extractors.numeric_extractor import NumericExtractor
    assert NumericExtractor is not None


def test_the_surviving_six_phases_are_untouched():
    """Deleting a seventh phase must not disturb the six that run."""
    fns = [fn for _, fn in pipeline.STANDARD_ENRICHMENT_PHASES]
    assert len(fns) == 6
    for fn_name in fns:
        assert callable(getattr(pipeline, fn_name, None)), f"{fn_name} no longer resolves"
