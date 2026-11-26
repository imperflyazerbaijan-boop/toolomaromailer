import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from email.message import Message
import main
import source_sync as s

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"state.sqlite3"
        self.db=main.connect(self.path)
        self.src=dict(id="de",country="Germany",interval_seconds=60,page_delay_seconds=1)
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def ready(self):
        with self.db: self.db.execute("UPDATE source_state SET next_at=0")
    def test_checkpoint_and_consent(self):
        record=dict(email="hello@example.com",consent=True,consent_evidence="fixture")
        s.sync(self.db,[self.src],lambda a,b: {"records":[record,{},dict(record,consent=False)],"next_cursor":"p2"})
        self.assertEqual(self.db.execute("SELECT count(*) FROM queue").fetchone()[0],1)
        self.db.close(); self.db=main.connect(self.path)
        self.ready()
        def page(a,b):
            self.assertEqual(b,"p2")
            return {"records":[record],"next_cursor":None}
        s.sync(self.db,[self.src],page)
        self.assertEqual(self.db.execute("SELECT count(*) FROM queue").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT status FROM source_state").fetchone()[0],"complete")
    def test_rate_limit_isolation(self):
        second=dict(self.src,id="ca",country="Canada")
        def fetch(src,cursor):
            if src["id"]=="de":
                h=Message(); h["Retry-After"]="120"
                raise HTTPError("https://example.com",429,"rate",h,None)
            return {"records":[dict(email="ok@example.com",consent=True,consent_evidence="fixture")]}
        s.sync(self.db,[self.src,second],fetch)
        self.assertEqual(dict(self.db.execute("SELECT id,status FROM source_state")),{"de":"rate_limited","ca":"complete"})
        self.assertEqual(self.db.execute("SELECT country FROM queue").fetchone()[0],"Canada")
    def test_bad_page_and_repeated_cursor(self):
        s.sync(self.db,[self.src],lambda a,b: {"records":[],"next_cursor":"x"})
        self.ready()
        s.sync(self.db,[self.src],lambda a,b: {"records":[],"next_cursor":"x"})
        self.assertEqual(self.db.execute("SELECT cursor,status FROM source_state").fetchone(),("x","retry"))
    def test_access_denied(self):
        def fetch(a,b):
            raise HTTPError("https://example.com",403,"denied",None,None)
        s.sync(self.db,[self.src],fetch)
        self.assertEqual(self.db.execute("SELECT status FROM source_state").fetchone()[0],"access_denied")

if __name__=="__main__": unittest.main()
