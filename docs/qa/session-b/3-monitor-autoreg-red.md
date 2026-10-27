============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\.claude\worktrees\fix-monitor-autoreg
configfile: pytest.ini
plugins: hypothesis-6.155.1, anyio-4.14.1, Faker-40.43.0, platformdirs-4.12.2, asyncio-1.3.0, split-0.11.0, xdist-3.8.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 3 items

tests\test_r2_monitor_auto_register_failure_is_loud.py FF.               [100%]

================================== FAILURES ===================================
__________________ test_a_failed_registration_fails_the_run ___________________
tests\test_r2_monitor_auto_register_failure_is_loud.py:92: in test_a_failed_registration_fails_the_run
    assert len(results.get("register_failed", [])) == 1
E   AssertionError: assert 0 == 1
E    +  where 0 = len([])
E    +    where [] = <built-in method get of dict object at 0x000001DE72F68540>('register_failed', [])
E    +      where <built-in method get of dict object at 0x000001DE72F68540> = {'changed': [], 'checked': 0, 'failed': 0, 'hub_alerts': [], ...}.get
---------------------------- Captured stdout call -----------------------------
Checking 1 chapters across 1 councils...

[testcouncil] Scraping hub page...
  Hub returned 2 PDF links (previous: 1)
  [NEW] Part Z (new)  https://c.example/new.pdf
    [auto-reg ERROR] insert failed

  testcouncil/part-a
    [no council_url] hub-only chapter -- no hash check possible; discovery for this council runs off its hub page

  [testcouncil] verified_at NOT updated — checked 0 of 1 active chapters, 0 changed, 0 failed
___________ test_a_failed_registration_keeps_the_old_document_count ___________
tests\test_r2_monitor_auto_register_failure_is_loud.py:100: in test_a_failed_registration_keeps_the_old_document_count
    assert not any("SET hub_last_pdf_count" in s for s in sql), (
E   AssertionError: the count moved, so the next run will not see the new document again
E   assert not True
E    +  where True = any(<generator object test_a_failed_registration_keeps_the_old_document_count.<locals>.<genexpr> at 0x000001DE72FC9FF0>)
---------------------------- Captured stdout call -----------------------------
Checking 1 chapters across 1 councils...

[testcouncil] Scraping hub page...
  Hub returned 2 PDF links (previous: 1)
  [NEW] Part Z (new)  https://c.example/new.pdf
    [auto-reg ERROR] insert failed

  testcouncil/part-a
    [no council_url] hub-only chapter -- no hash check possible; discovery for this council runs off its hub page

  [testcouncil] verified_at NOT updated — checked 0 of 1 active chapters, 0 changed, 0 failed
=========================== short test summary info ===========================
FAILED tests/test_r2_monitor_auto_register_failure_is_loud.py::test_a_failed_registration_fails_the_run
FAILED tests/test_r2_monitor_auto_register_failure_is_loud.py::test_a_failed_registration_keeps_the_old_document_count
========================= 2 failed, 1 passed in 0.74s =========================
