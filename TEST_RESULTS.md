# v0.2 test results — 2026-11-26
Local Linux, Python 3.13.5; command python -m unittest -v. 12 tests passed in 6.953 seconds, zero failures.
- test_country_parallelism: 40 threads meet at barrier.
- test_syntax_and_opt_out: malformed syntax and suppression.
- test_validation_retry_restart_and_export: mocked timeout, DB restart, deduplication, exact Excel format, simulated locked output.
- test_checkpoint_and_consent: atomic pagination cursor persistence and malformed/nonconsenting record filtering.
- test_rate_limit_isolation: simulated 429 while another source succeeds.
- test_bad_page_and_repeated_cursor: invalid repeated cursor preserves checkpoint.
- test_access_denied: simulated 403 classified correctly.
- test_host_cooldown_survives_restart: same-host 429 cooldown persists, other host succeeds.
- test_temporary_dns_error_is_retry: mocked DNS failure does not discard address.
- test_incremental_file_import: unchanged file skipped, modified file imported.
- test_load_20000_records: 500 synthetic contacts per each of 40 countries; stream XLSX; one sheet, two columns, 20,000 rows.
- test_runner_empty_and_lock: local process lock and valid empty workbook.
Git blob SHAs verified against GitHub:
main.py 052ffe21a38792817d4443a98931aefac8e33b26
countries.txt efbfb560a408e2952b9cc8d7bfa4877171859110
test_main.py 2c7eb39213049147b6a4286b0443c80cff2bd226
source_sync.py 84451d95f0ade1510a57673ff6c4cbe8197bcee0
test_source_sync.py 7f1ab98e9049de471894fc7ee6610cfab64dda4c
advanced.py 36d64ddc41045d7d19d343787a7b90edd36e6fa9
test_advanced.py d3bb562d342bd75bdc429459f9f23818e1614183
Limitations: controlled fixtures/mock validators and HTTP failures; no live DNS/API traffic, no real emails collected. Linux test execution only, no confirmed Windows CI. Not a production readiness certification. Container cannot directly resolve github.com, so exact local copies were checked by Git blob SHA.

## v0.3 — actual rerun
Local Linux, command python -m unittest -q. 16 tests in 7.171s, OK. Existing 12 tests rerun (including 20,000 synthetic records). Added 4 tests:
- provider pagination / explicit consent / opt-out: PASS (mock HTTP response)
- revocation and multi-country queue: PASS (SQLite fixture)
- configuration / fixed provider hostname: PASS
- weighted market RPM and insufficient samples: PASS (synthetic CSV)
Exact local/GitHub blob SHA matches:
mailchimp_adapter.py ce6bda6d4df0a6043351e0dbe085b88c736c36a0
market_priority.py e2099a80ea0fc7b6626e265f8e0743045c28db1c
test_v03.py 2f1337b9f7dd57d4d625634e19286ba166b5d1f2
source_sync.py 4ac929a3e1f389426c228a9c9315f665d089892c
DNS resolution of github.com, us1.api.mailchimp.com and google.com failed in container. No real external API request or Windows run validated. No actual contacts harvested; fixtures only.
