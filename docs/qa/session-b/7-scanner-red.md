============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\.claude\worktrees\widen-figure-scanner
configfile: pytest.ini
plugins: hypothesis-6.155.1, anyio-4.14.1, Faker-40.43.0, platformdirs-4.12.2, asyncio-1.3.0, split-0.11.0, xdist-3.8.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 20 items

tests\test_lint_hardcoded_regulatory_numbers.py ................FFFF     [100%]

================================== FAILURES ===================================
__________________ test_min_and_max_count_as_planning_words ___________________
tests\test_lint_hardcoded_regulatory_numbers.py:145: in test_min_and_max_count_as_planning_words
    assert lint.hits_in_text("<li>studio apartments (300m² min) to manor houses</li>", ".tsx")
E   AssertionError: assert []
E    +  where [] = <function hits_in_text at 0x000001BA36ED3EC0>('<li>studio apartments (300m² min) to manor houses</li>', '.tsx')
E    +    where <function hits_in_text at 0x000001BA36ED3EC0> = lint.hits_in_text
__________ test_a_bare_number_compared_with_a_lot_measure_is_caught ___________
tests\test_lint_hardcoded_regulatory_numbers.py:150: in test_a_bare_number_compared_with_a_lot_measure_is_caught
    assert lint.hits_in_text("  return areaSqm >= 450;", ".ts")
E   AssertionError: assert []
E    +  where [] = <function hits_in_text at 0x000001BA36ED3EC0>('  return areaSqm >= 450;', '.ts')
E    +    where <function hits_in_text at 0x000001BA36ED3EC0> = lint.hits_in_text
______________________ test_a_typed_zone_list_is_caught _______________________
tests\test_lint_hardcoded_regulatory_numbers.py:158: in test_a_typed_zone_list_is_caught
    assert lint.hits_in_text("const Z = ['R2', 'RU1', 'C1'];", ".ts")
E   assert []
E    +  where [] = <function hits_in_text at 0x000001BA36ED3EC0>("const Z = ['R2', 'RU1', 'C1'];", '.ts')
E    +    where <function hits_in_text at 0x000001BA36ED3EC0> = lint.hits_in_text
__________________ test_a_paraphrased_quote_cannot_be_cited ___________________
tests\test_lint_hardcoded_regulatory_numbers.py:168: in test_a_paraphrased_quote_cannot_be_cited
    assert any("PARAPHRASED" in p for p in problems)
E   assert False
E    +  where False = any(<generator object test_a_paraphrased_quote_cannot_be_cited.<locals>.<genexpr> at 0x000001BA375A5490>)
=========================== short test summary info ===========================
FAILED tests/test_lint_hardcoded_regulatory_numbers.py::test_min_and_max_count_as_planning_words
FAILED tests/test_lint_hardcoded_regulatory_numbers.py::test_a_bare_number_compared_with_a_lot_measure_is_caught
FAILED tests/test_lint_hardcoded_regulatory_numbers.py::test_a_typed_zone_list_is_caught
FAILED tests/test_lint_hardcoded_regulatory_numbers.py::test_a_paraphrased_quote_cannot_be_cited
======================== 4 failed, 16 passed in 3.01s =========================
