import csv
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from email.message import Message
from urllib.error import HTTPError
from unittest.mock import patch
from types import SimpleNamespace
from openpyxl import load_workbook
import advanced
import main
import source_sync as s

class AdvancedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=main.connect(self.root/'state.sqlite3')
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def test_host_cooldown_survives_restart(self):
        a=dict(id='a',country='Germany',url='https://api.example.com/a',interval_seconds=60,page_delay_seconds=1)
        b=dict(a,id='b',country='Canada')
        c=dict(a,id='c',url='https://other.example.com/c')
        calls=[]
        def fetch(src,cursor):
            calls.append(src['id'])
            if src['id']=='a':
                h=Message(); h['Retry-After']='120'
                raise HTTPError(src['url'],429,'rate',h,None)
            return {'records':[]}
        s.sync(self.db,[a,b,c],fetch)
        self.assertCountEqual(calls,['a','c'])
        self.db.close(); self.db=main.connect(self.root/'state.sqlite3')
        self.assertEqual(s.sync(self.db,[a,b],fetch),0)
        with self.db: self.db.execute('UPDATE host_state SET next_at=0')
        self.assertEqual(s.sync(self.db,[a,b],fetch),1)
        self.assertEqual(calls[-1],'b')
    def test_temporary_dns_error_is_retry(self):
        from email_validator import EmailUndeliverableError
        def fake(raw,**kwargs):
            if not kwargs['check_deliverability']:
                return SimpleNamespace(normalized=raw)
            try: raise OSError('offline')
            except OSError as exc: raise EmailUndeliverableError('temporary') from exc
        with patch('main.validate_email',side_effect=fake),patch('main.resolver',return_value=object()):
            self.assertEqual(main.validate('test@sample.com'),('retry',None))
    def test_incremental_file_import(self):
        file=self.root/'input.csv'
        file.write_text('Email,Country,Consent,ConsentEvidence\na@example.com,Germany,yes,fixture\n')
        main.ingest(self.db,self.root)
        self.assertEqual(self.db.execute('SELECT count(*) FROM queue').fetchone()[0],1)
        changes=self.db.total_changes
        main.ingest(self.db,self.root)
        self.assertEqual(self.db.total_changes,changes)
        with file.open('a') as f: f.write('b@example.com,Canada,yes,fixture\n')
        main.ingest(self.db,self.root)
        self.assertEqual(self.db.execute('SELECT count(*) FROM queue').fetchone()[0],2)
    def test_load_20000_records(self):
        rows=[]
        for country in main.COUNTRIES:
            for i in range(500):
                email=f'user{i}@{country.lower().replace(" ","-")}.example.com'
                ident=hashlib.sha256(email.encode()).hexdigest()
                rows.append((ident,email,country,'fixture'))
        with self.db: self.db.executemany('INSERT INTO queue(id,email,country,evidence) VALUES(?,?,?,?)',rows)
        self.assertEqual(main.process(self.db,lambda raw:('accepted',raw)),20000)
        target=self.root/'output.xlsx'
        self.assertTrue(main.export(self.db,target))
        book=load_workbook(target,read_only=True)
        self.assertEqual(book.sheetnames,['Emails'])
        data=book.active.values
        self.assertEqual(next(data),('Email','Country'))
        self.assertEqual(sum(1 for row in data if len(row)==2),20000)
        book.close()
    def test_runner_empty_and_lock(self):
        data=self.root/'data'; folder=self.root/'input'
        data.mkdir(); folder.mkdir()
        lock=data/'instance.lock'
        with advanced.instance_lock(lock):
            with self.assertRaises(OSError):
                with advanced.instance_lock(lock): pass
        self.assertEqual(advanced.run_locked(SimpleNamespace(once=True,interval=1),self.root,data,folder),0)
        book=load_workbook(self.root/'toolomaro_emails.xlsx')
        self.assertEqual(list(book.active.values),[('Email','Country')]); book.close()

if __name__=='__main__': unittest.main()
