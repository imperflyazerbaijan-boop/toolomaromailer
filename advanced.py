"""Operator runner for authorized contacts, with persistent sync and reporting."""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import sqlite3
import time
from pathlib import Path
import main
from contextlib import contextmanager
import source_sync

@contextmanager
def instance_lock(path):
    with path.open("a+b") as lock:
        lock.seek(0,2)
        if lock.tell()==0:
            lock.write(b"0"); lock.flush()
        lock.seek(0)
        if __import__("os").name=="nt":
            import msvcrt
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            try: yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            try: yield
            finally: fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

def status(db):
    counts = dict(db.execute("SELECT status,count(*) FROM queue GROUP BY status"))
    print("Queue:",counts,"| Unique:",db.execute("SELECT count(*) FROM contacts").fetchone()[0],flush=True)
    for country,n in db.execute("SELECT country,count(*) FROM contacts GROUP BY country ORDER BY country"):
        print(f"  {country}: {n}",flush=True)
    for ident,state,records in db.execute("SELECT id,status,records FROM source_state ORDER BY id"):
        print(f"  Source {ident}: {state} ({records} records observed)",flush=True)

def run():
    p=argparse.ArgumentParser()
    p.add_argument("--once",action="store_true")
    p.add_argument("--interval",type=int,default=5)
    p.add_argument("--root",type=Path,default=main.ROOT)
    args=p.parse_args()
    root=args.root.resolve()
    data=root/"data"; folder=root/"input"
    data.mkdir(parents=True,exist_ok=True); folder.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),RotatingFileHandler(data/"runtime.log",maxBytes=2_000_000,backupCount=3,encoding="utf-8")])
    try:
        with instance_lock(data/"instance.lock"):
            return run_locked(args,root,data,folder)
    except OSError:
        logging.error("Could not acquire instance lock or open local state; check permissions and other running instances")
        return 1

def run_locked(args,root,data,folder):
    db=main.connect(data/"state.sqlite3")
    source_sync.init(db)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS export_revision(id INTEGER PRIMARY KEY CHECK(id=1),rev INTEGER NOT NULL);
    INSERT OR IGNORE INTO export_revision VALUES(1,0);
    CREATE TRIGGER IF NOT EXISTS contact_insert AFTER INSERT ON contacts BEGIN UPDATE export_revision SET rev=rev+1 WHERE id=1; END;
    CREATE TRIGGER IF NOT EXISTS contact_delete AFTER DELETE ON contacts BEGIN UPDATE export_revision SET rev=rev+1 WHERE id=1; END;
    CREATE TRIGGER IF NOT EXISTS contact_update AFTER UPDATE ON contacts BEGIN UPDATE export_revision SET rev=rev+1 WHERE id=1; END;
    """)
    last_export=None
    warned_empty=False
    try:
        while True:
            try:
                try:
                    sources=source_sync.read_config(root/"sources.json")
                except (ValueError,OSError):
                    logging.warning("Source configuration unavailable; local imports continue")
                    sources=[]
                if not sources and not warned_empty:
                    logging.warning("No enabled authorized API sources; only local CSV imports are available")
                    warned_empty=True
                main.ingest(db,folder)
                source_sync.sync(db,sources)
                main.process(db)
                rev=db.execute("SELECT rev FROM export_revision WHERE id=1").fetchone()[0]
                target=root/"toolomaro_emails.xlsx"
                ok=True
                if last_export!=rev or not target.exists():
                    ok=main.export(db,target)
                    if ok: last_export=rev
                status(db)
                if args.once:
                    pending=db.execute("SELECT count(*) FROM queue WHERE status IN ('pending','retry')").fetchone()[0]
                    return 0 if ok and not pending else 1
            except (OSError,sqlite3.Error):
                logging.exception("Recoverable cycle failure; stored state retained")
                if args.once: return 1
            time.sleep(max(1,args.interval))
    except KeyboardInterrupt:
        print("Stopped; checkpoint retained.")
        return 0
    finally:
        db.close()

if __name__=="__main__":
    raise SystemExit(run())
