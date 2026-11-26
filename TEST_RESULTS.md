# Test results — 2026-11-26
Local Python 3.13.5 on Linux, command python -m unittest -v.
Verified local files match GitHub Git blob SHAs:
- main.py: 8b90e9502d3c2eb5486609f0860862e07f7c514d
- countries.txt: efbfb560a408e2952b9cc8d7bfa4877171859110
- test_main.py: 2c7eb39213049147b6a4286b0443c80cff2bd226
Results:
- test_country_parallelism: PASS (40 threads meet at barrier)
- test_syntax_and_opt_out: PASS
- test_validation_retry_restart_and_export: PASS (simulated timeout, deduplication, reopen DB, exact sheet and two columns, simulated Excel lock)
Ran 3 tests in 0.089s — OK.
Limitations: mock validators used for concurrency/retry tests; no live DNS check, no platform access tests, no Windows execution or GitHub Actions result verified. No actual external contacts harvested. This is a tested importer foundation, not a tested automated lead scraper.
