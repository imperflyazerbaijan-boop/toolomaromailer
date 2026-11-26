# ToolomaroMailer — consent-based importer (v0.1)
Windows / Python 3.11+. This is a contact-management foundation, not an autonomous public-email scraper or mail sender. It imports authorized opt-in records from local CSVs, validates syntax and domain DNS, and exports one sheet with Email and Country. A valid DNS domain does not prove the individual mailbox exists. ConsentEvidence must describe actual consent for Toolomaro marketing; the program cannot independently verify the evidence.
1. Clone this repository.
2. Install Python if necessary.
3. Create input/ and put authorized UTF-8 CSV exports there. Headers: Email,Country,Consent,ConsentEvidence. Consent must be yes. Country must be one of countries.txt.
4. Double-click run.bat to continuously import, process and retry transient DNS failures. Ctrl+C stops. Or run python main.py for one pass after installing requirements.
5. Output: toolomaro_emails.xlsx. SQLite state is in data/state.sqlite3. Do not delete state unless deliberately resetting. Do not commit contacts, evidence or output.
6. To suppress an opt-out: .venv/Scripts/python.exe main.py --suppress ADDRESS
Limitations: no live platform adapters, no campaign sending, no verified universal RPM ranking, no mailbox-delivery verification. One instance at a time. Country workers operate in parallel when input exists; empty countries have no work. The country shortlist is an initial hypothesis, not a ranking. See RESEARCH.md and handoff documents.
