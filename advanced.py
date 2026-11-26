"""Operator runner for authorized contacts, with persistent sync and reporting."""
import argparse
import logging
import sqlite3
import time
from pathlib import Path
import main
import source_sync

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
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    db=main.connect(data/"state.sqlite3")
    source_sync.init(db)
    try:
        while True:
            try:
                try:
                    sources=source_sync.read_config(root/"sources.json")
                except (ValueError,OSError):
                    logging.warning("Source configuration unavailable; local imports continue")
                    sources=[]
                main.ingest(db,folder)
                source_sync.sync(db,sources)
                main.process(db)
                ok=main.export(db,root/"toolomaro_emails.xlsx")
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
