"""Consent-based business contact importer. No website harvesting or sending."""
import argparse
import csv
import hashlib
import logging
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from email_validator import validate_email, EmailNotValidError, EmailUndeliverableError, caching_resolver
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent
COUNTRIES = tuple((ROOT / "countries.txt").read_text(encoding="utf-8").splitlines())
COUNTRY_NAMES = {c.casefold(): c for c in COUNTRIES}
LOG = logging.getLogger("toolomaro")
RESOLVER = None

def resolver():
    global RESOLVER
    if RESOLVER is None:
        RESOLVER = caching_resolver(timeout=5)
    return RESOLVER

def connect(path):
    db = sqlite3.connect(path, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS queue(
        id TEXT PRIMARY KEY, email TEXT NOT NULL, country TEXT NOT NULL,
        evidence TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS contacts(
        key TEXT PRIMARY KEY, email TEXT NOT NULL, country TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS suppressed(key TEXT PRIMARY KEY);
    """)
    return db

def ingest(db, folder):
    """Files are exports from authorized opt-in sources, never scraped lists."""
    for file in sorted(folder.glob("*.csv")):
        try:
            with file.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                required = {"Email", "Country", "Consent", "ConsentEvidence"}
                if not required.issubset(reader.fieldnames or []):
                    LOG.warning("Skipped CSV: missing required headers")
                    continue
                for row in reader:
                    try:
                        email = (row.get("Email") or "").strip()
                        country = COUNTRY_NAMES.get((row.get("Country") or "").strip().casefold())
                        evidence = (row.get("ConsentEvidence") or "").strip()
                        if not email or not country or not evidence or (row.get("Consent") or "").strip().lower() != "yes":
                            continue
                        key = hashlib.sha256((email.casefold()+"\0"+country).encode()).hexdigest()
                        with db:
                            db.execute("INSERT OR IGNORE INTO queue(id,email,country,evidence) VALUES(?,?,?,?)",
                                       (key,email,country,evidence))
                    except (ValueError, TypeError):
                        LOG.warning("Skipped malformed record")
        except (OSError, UnicodeError, csv.Error):
            LOG.warning("Skipped unreadable CSV; other files continue")

def validate(raw):
    try:
        syntax = validate_email(raw, check_deliverability=False, allow_smtputf8=False)
    except EmailNotValidError:
        return "rejected", None
    try:
        info = validate_email(syntax.normalized, check_deliverability=True,
                              dns_resolver=resolver(), allow_smtputf8=False)
        if not getattr(info, "mx", None):
            return "retry", None
        return "accepted", info.normalized
    except EmailUndeliverableError as exc:
        # Unexpected resolver errors are wrapped by email-validator.
        # Preserve records when the cause is not a confirmed DNS rejection.
        if exc.__cause__ is not None:
            import dns.resolver
            if not isinstance(exc.__cause__, (dns.resolver.NXDOMAIN,dns.resolver.NoAnswer)):
                return "retry", None
        return "rejected", None
    except Exception:
        return "retry", None

def work_country(rows, validator=validate):
    for ident, raw, country, attempts in rows:
        try:
            status, normalized = validator(raw)
        except Exception:
            status, normalized = "retry", None
        yield ident, country, attempts, status, normalized

def apply_result(db, result):
    ident, country, attempts, status, normalized = result
    with db:
        if status == "accepted" and normalized:
            key = normalized.casefold()
            if db.execute("SELECT 1 FROM suppressed WHERE key=?", (key,)).fetchone():
                status = "suppressed"
            else:
                db.execute("INSERT OR IGNORE INTO contacts VALUES(?,?,?)",
                           (key, normalized, country))
        elif status not in ("rejected", "retry"):
            status = "retry"
        delay = min(900, 5 * 2 ** min(attempts, 8)) if status == "retry" else 0
        db.execute("UPDATE queue SET status=?,attempts=attempts+1,next_at=? WHERE id=?",
                   (status,time.time()+delay,ident))

def process(db, validator=validate):
    rows = db.execute("""SELECT id,email,country,attempts FROM queue
                         WHERE status IN ('pending','retry') AND next_at<=?
                         ORDER BY country,id""",(time.time(),)).fetchall()
    groups = {country: [] for country in COUNTRIES}
    for row in rows:
        groups[row[2]].append(row)
    # Independent country workers: a slow country never creates a round barrier.
    with ThreadPoolExecutor(max_workers=len(COUNTRIES)) as pool:
        futures = {}
        def schedule(country):
            if groups[country]:
                row = groups[country].pop()
                futures[pool.submit(lambda r: next(work_country([r],validator)),row)] = (country,row)
        for country in COUNTRIES:
            schedule(country)
        while futures:
            done, _ = wait(futures,return_when=FIRST_COMPLETED)
            for future in done:
                country,row = futures.pop(future)
                try:
                    result = future.result()
                except Exception:
                    result = (row[0],country,row[3],"retry",None)
                apply_result(db,result)
                schedule(country)
    return len(rows)

def export(db, target):
    wb = Workbook()
    ws = wb.active
    ws.title = "Emails"
    ws.append(["Email", "Country"])
    for email, country in db.execute("SELECT email,country FROM contacts ORDER BY country,email"):
        ws.append([email,country])
        ws.cell(ws.max_row,1).data_type = "s"
        ws.cell(ws.max_row,2).data_type = "s"
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 50
    ws.column_dimensions["B"].width = 27
    tmp = target.with_name(target.stem+".tmp.xlsx")
    try:
        wb.save(tmp)
        os.replace(tmp,target)
        return True
    except OSError:
        LOG.warning("Excel export unavailable; SQLite records retained; retry later")
        return False
    finally:
        wb.close()
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            LOG.warning("Temporary Excel file could not be removed")

def suppress(db, raw):
    normalized = validate_email(raw, check_deliverability=False, allow_smtputf8=False).normalized
    key = normalized.casefold()
    with db:
        db.execute("INSERT OR IGNORE INTO suppressed VALUES(?)",(key,))
        db.execute("DELETE FROM contacts WHERE key=?",(key,))
        db.execute("UPDATE queue SET status='suppressed' WHERE lower(email)=?",(key,))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="Keep importing and retrying until Ctrl+C")
    parser.add_argument("--suppress", help="Remove an opted-out address and prevent reimport")
    args = parser.parse_args()
    folder = ROOT / "input"
    folder.mkdir(exist_ok=True)
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    db = connect(data / "state.sqlite3")
    try:
        if args.suppress:
            suppress(db,args.suppress)
            return 0 if export(db,ROOT / "toolomaro_emails.xlsx") else 1
        while True:
            ingest(db,folder)
            processed = process(db)
            exported = export(db,ROOT / "toolomaro_emails.xlsx")
            contacts = db.execute("SELECT count(*) FROM contacts").fetchone()[0]
            pending = db.execute("SELECT count(*) FROM queue WHERE status IN ('pending','retry')").fetchone()[0]
            print(f"Processed: {processed} | Unique: {contacts} | Pending/retry: {pending} | Excel: {exported}",flush=True)
            if not args.watch:
                return 0 if exported and not pending else 1
            time.sleep(10)
    except KeyboardInterrupt:
        print("Stopped; SQLite checkpoint retained.")
        export(db,ROOT / "toolomaro_emails.xlsx")
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    raise SystemExit(main())
