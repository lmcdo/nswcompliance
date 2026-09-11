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


def test_the_module_docstring_does_not_advertise_the_deleted_command():
    """Caught only because a late grep listed line 8 of this very file.

    The module's own Usage block still read
    `python enrichment/pipeline.py --phase numeric`, so the file documented a
    command it no longer accepts. The choices-list test above does not see a
    docstring, and the dead-column test skips comment lines by design -- between
    them they left the most-read line in the file uncovered.
    """
    head = PIPELINE_SRC.split('"""')[1]
    advertised = [
        line.strip() for line in head.splitlines()
        if line.strip().startswith("python ") and "--phase numeric" in line
    ]
    assert not advertised, (
        "the module docstring offers a deleted command as something to run:\n  "
        + "\n  ".join(advertised)
    )


#: A line only matters if it could reach the database. Prose may NAME the dead
#: columns -- recording why they are gone is the entire point of those notes, and
#: an earlier version of this test failed on its own explanation, twice.
_SQL_CONTEXT = ("SELECT", "WHERE", "SET ", "COUNT(", "CASE WHEN", "INSERT", "UPDATE", "FROM ")


def test_no_query_in_the_pipeline_references_a_column_that_does_not_exist():
    """The failure mode is a QUERY naming a column that does not exist.

    So this looks for the dead names in SQL context, not anywhere in the file.
    Narrower than "the string never appears", and deliberately: a test that
    forbids mentioning the problem forbids documenting it, and the documentation
    is what stops the next person reintroducing it.
    """
    offenders = []
    for n, line in enumerate(PIPELINE_SRC.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if not any(tok in line.upper() for tok in (t.upper() for t in _SQL_CONTEXT)):
            continue
        for col in DEAD_COLUMNS:
            if col in line:
                offenders.append(f"{n}: {stripped[:90]}")
    assert not offenders, (
        "these lines put a column that exists on no table into SQL:\n  "
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
