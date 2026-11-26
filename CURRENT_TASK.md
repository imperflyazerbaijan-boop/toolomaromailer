# Current task — v0.3 checkpoint
Implemented and locally tested advanced authorized-contact pipeline, including read-only Mailchimp adapter, country RPM ranking from first-party AdSense CSV and 30/40 market proxy data. Main entry remains run.bat -> advanced.py. All 16 controlled tests pass; exact hashes in TEST_RESULTS.md.
No real account or source credentials or actual AdSense report provided. No live API, DNS, Windows or full directory E2E verified. No automated public email harvesting or arbitrary directory discovery implemented. Mailchimp sample is disabled by default. Archived/deleted audience members absent from API pages are not reconciled automatically; review provider records before outreach. No marketing email sender.
Read README.md, MARKET_RESEARCH.md, RESEARCH.md, TEST_RESULTS.md. Repository is public: do not commit credentials, contact records or AdSense exports.

## Latest checkpoint
Added public_market.py (commit 98bc3fa1cb41bfffd126fa4b970795707801a768), a separate keyless aggregate market research tool. It is not an email scraper. User asked to leave Windows testing to them. Live API run and tests remain unverified. Original mass-email discovery objective is not delivered; do not describe it as completed. No Mailchimp setup required for the new market module.
