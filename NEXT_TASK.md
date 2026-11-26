# Next tasks
1. Read master spec, current/previous/next task docs, README, RESEARCH and TEST_RESULTS.
2. Verify Windows GitHub Actions or execute on real Windows; investigate platform-specific locking and launcher behavior.
3. Select actual permitted providers with user-owned accounts and consent data; verify API terms, permissions, field mapping, pagination and rate limits. Add provider-specific adapters and test with authorized credentials; do not use public bulk email harvesting or evade access restrictions.
4. Run networked DNS and authorized endpoint E2E tests, kill/restart during processing, disk-full, long-running soak, and larger dataset tests. Improve isolation based on evidence. Note per-source cycle waits on slowest request, and source-specific backoff remains.
5. Research empirical country-level advertising data (first-party AdSense when available) and compliant acquisition channels. No universal official AdSense country RPM list.
6. Update all handoff docs and actual test evidence; commit progress.
