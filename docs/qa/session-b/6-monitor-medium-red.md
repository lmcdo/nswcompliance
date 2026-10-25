============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\.claude\worktrees\fix-monitor-medium
configfile: pytest.ini
plugins: hypothesis-6.155.1, anyio-4.14.1, Faker-40.43.0, platformdirs-4.12.2, asyncio-1.3.0, split-0.11.0, xdist-3.8.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 5 items

tests\test_r2_monitor_medium_findings.py FFFFF                           [100%]

================================== FAILURES ===================================
___________ test_skipped_no_link_chapters_are_named_as_not_checked ____________
tests\test_r2_monitor_medium_findings.py:43: in test_skipped_no_link_chapters_are_named_as_not_checked
    note = r2_monitor.not_checked_note(_results(checked=10, skipped_no_url=3))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: module 'r2_monitor' has no attribute 'not_checked_note'
________________________ test_all_checked_has_no_note _________________________
tests\test_r2_monitor_medium_findings.py:48: in test_all_checked_has_no_note
    assert r2_monitor.not_checked_note(_results(checked=10)) == ""
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: module 'r2_monitor' has no attribute 'not_checked_note'
______________ test_main_prints_all_current_only_without_a_note _______________
tests\test_r2_monitor_medium_findings.py:53: in test_main_prints_all_current_only_without_a_note
    assert 'infra_note = not_checked_note(results)' in src
E   assert 'infra_note = not_checked_note(results)' in '#!/usr/bin/env python3\n"""\nWeekly DCP Chapter Monitor\n===========================\nFor each council, scrapes the h...n  No changes detected. All chapters are current.")\n        sys.exit(0)\n\n\nif __name__ == "__main__":\n    main()\n'
__________________ test_unchanged_chapters_are_counted_once ___________________
tests\test_r2_monitor_medium_findings.py:59: in test_unchanged_chapters_are_counted_once
    assert r2_monitor.chapters_checked(_results(checked=10, unchanged=7)) == 10
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: module 'r2_monitor' has no attribute 'chapters_checked'
_______________ test_a_broken_hub_scrapers_import_fails_loudly ________________
tests\test_r2_monitor_medium_findings.py:66: in test_a_broken_hub_scrapers_import_fails_loudly
    with pytest.raises(ImportError):
E   Failed: DID NOT RAISE <class 'ImportError'>
=========================== short test summary info ===========================
FAILED tests/test_r2_monitor_medium_findings.py::test_skipped_no_link_chapters_are_named_as_not_checked
FAILED tests/test_r2_monitor_medium_findings.py::test_all_checked_has_no_note
FAILED tests/test_r2_monitor_medium_findings.py::test_main_prints_all_current_only_without_a_note
FAILED tests/test_r2_monitor_medium_findings.py::test_unchanged_chapters_are_counted_once
FAILED tests/test_r2_monitor_medium_findings.py::test_a_broken_hub_scrapers_import_fails_loudly
============================== 5 failed in 0.81s ==============================
