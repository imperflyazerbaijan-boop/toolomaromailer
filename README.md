# ToolomaroMailer v0.2 — advanced authorized contact pipeline
Windows / Python 3.11+. This program imports consented business contact exports and polls explicitly authorized JSON APIs. It is NOT an autonomous web-directory scraper or bulk mail sender.

## Install and run
```bat
git clone https://github.com/imperflyazerbaijan-boop/toolomaromailer.git
cd toolomaromailer
run.bat
```
For an existing checkout: git pull, then run.bat. First install requires internet. Subsequent runs skip dependency installation when packages are installed. Ctrl+C stops; restart resumes from SQLite. Only one advanced runner instance is allowed. Stop it before running the legacy suppression CLI.

## Input
Local UTF-8 CSV files in input/ with exact headers Email,Country,Consent,ConsentEvidence. Consent must be yes; evidence must be a real reference to permission for Toolomaro outreach. Use English names from countries.txt. Unchanged files are not reimported. Suppress a withdrawn address after stopping the runner: .venv\Scripts\python.exe main.py --suppress ADDRESS.

For API input, copy sources.example.json to sources.json, configure documented authorized HTTPS endpoint(s), id, country, authorization_reference, interval and token_env (set the token in environment, not repository). Only enable with actual permission. Each endpoint must accept optional cursor query parameter and return JSON {"records":[{"email":"...","consent":true,"consent_evidence":"...","country":"Germany"}],"next_cursor":null}. Non-null next_cursor is a string. This generic contract requires a provider-specific adapter when actual API shape differs. No real provider is configured by default; example.com is a disabled placeholder, not a working source.
Access denied triggers a source cooldown. 429 honors Retry-After and shares cooldown across the same hostname. One source per host per polling tick, up to 40 different-host fetches concurrently. Other eligible sources continue. Pagination and queue insertion are atomic. On final page the source is periodically refreshed from the beginning; duplicates are ignored.
 
## Runtime
- 40 configured geographic markets; not an official AdSense ranking.
- Each country processes at most 500 due records per cycle, independent workers for active countries.
- DNS cache, bounded exponential backoff, persistent queue. DNS/MX success is NOT proof of mailbox deliverability. No SMTP probing.
- SQLite WAL state in data/state.sqlite3, rotating logs in data/runtime.log; no contact datasets or credentials in GitHub.
- toolomaro_emails.xlsx: exactly one sheet, two columns Email and Country, streaming export, atomic replacement. Re-export only on changes or failed export. Excel has a maximum 1,048,575 contact rows plus header; larger datasets remain in SQLite and export fails visibly rather than truncating.
- One-time mode: .venv\Scripts\python.exe advanced.py --once (processes one cycle; nonzero if records remain or export fails).
- Tests: .venv\Scripts\python.exe -m unittest -v.
 
## Limitations
12 controlled tests passed locally on Linux including 20,000 synthetic records. Windows and real external API/DNS end-to-end execution not verified. No real source, consent list or live directory adapter provided; no guarantee of no blocks, exact revenue, mailbox existence or universal fault tolerance. No auto-harvesting of public email addresses. Actual market research and source permissions are still outstanding. See RESEARCH.md, TEST_RESULTS.md and handoff files.
