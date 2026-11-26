import csv
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from openpyxl import load_workbook
import main

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = main.connect(self.root / "state.sqlite3")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def ingest(self, rows):
        with (self.root / "contacts.csv").open("w",newline="",encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Email","Country","Consent","ConsentEvidence"])
            w.writerows(rows)
        main.ingest(self.db,self.root)

    def test_country_parallelism(self):
        self.ingest([(f"test{i}@example.com",c,"yes","fixture") for i,c in enumerate(main.COUNTRIES)])
        barrier = threading.Barrier(len(main.COUNTRIES),timeout=10)
        def check(raw):
            barrier.wait()
            return "accepted",raw
        self.assertEqual(main.process(self.db,check),40)
        self.assertEqual(self.db.execute("SELECT count(*) FROM contacts").fetchone()[0],40)

    def test_validation_retry_restart_and_export(self):
        self.ingest([("ok@example.com","Germany","yes","fixture"),
                     ("OK@example.com","Germany","yes","fixture"),
                     ("fail@example.com","Germany","yes","fixture"),
                     ("bad","Canada","yes","fixture"),
                     ("no@example.com","Canada","no","fixture"),
                     ("unknown@example.com","Atlantis","yes","fixture"),
                     ("empty@example.com","Canada","yes","")])
        def check(raw):
            if raw.startswith("fail"): raise TimeoutError()
            if raw == "bad": return "rejected",None
            return "accepted",raw.lower()
        main.process(self.db,check)
        self.assertEqual(self.db.execute("SELECT count(*) FROM contacts").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM queue WHERE status='retry'").fetchone()[0],1)
        self.db.close()
        self.db = main.connect(self.root / "state.sqlite3")
        with self.db: self.db.execute("UPDATE queue SET next_at=0 WHERE status='retry'")
        main.process(self.db,lambda r: ("accepted",r))
        target = self.root / "out.xlsx"
        self.assertTrue(main.export(self.db,target))
        wb = load_workbook(target)
        self.assertEqual(wb.sheetnames,["Emails"])
        self.assertEqual(wb.active.max_column,2)
        self.assertEqual(list(wb.active.values),[("Email","Country"),("fail@example.com","Germany"),("ok@example.com","Germany")])
        wb.close()
        with patch("main.os.replace",side_effect=PermissionError):
            self.assertFalse(main.export(self.db,target))
        self.assertTrue(target.exists())
        self.assertEqual(self.db.execute("SELECT count(*) FROM contacts").fetchone()[0],2)

    def test_syntax_and_opt_out(self):
        self.assertEqual(main.validate("not an email"),("rejected",None))
        self.ingest([("test@example.com","Germany","yes","fixture")])
        main.process(self.db,lambda r: ("accepted",r))
        main.suppress(self.db,"test@example.com")
        self.ingest([("test@example.com","Canada","yes","fixture")])
        main.process(self.db,lambda r: ("accepted",r))
        self.assertEqual(self.db.execute("SELECT count(*) FROM contacts").fetchone()[0],0)

if __name__ == "__main__":
    unittest.main()
