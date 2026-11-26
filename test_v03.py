import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import mailchimp_adapter as mc
import market_priority as mp
import source_sync as sync
import main

class V03Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.src=mc.prepare(dict(id='mc',provider='mailchimp',datacenter='us1',audience_id='abc',country_merge_tag='COUNTRY',permission_id='p1',token_env='MC_TEST',interval_seconds=60,page_delay_seconds=1))
    def tearDown(self):
        self.tmp.cleanup()
    def test_provider_pagination_and_permission(self):
        member=dict(id='1',email_address='yes@example.com',status='subscribed',marketing_permissions=[dict(marketing_permission_id='p1',enabled=True)],merge_fields={'COUNTRY':'Germany'})
        def read(url,headers):
            self.assertEqual(urlsplit(url).hostname,'us1.api.mailchimp.com')
            self.assertEqual(parse_qs(urlsplit(url).query)['offset'],['0'])
            self.assertEqual(headers['Authorization'],'Bearer fake-us1')
            return {'members':[member,dict(member,id='2',email_address='no@example.com',marketing_permissions=[]),dict(member,id='3',email_address='stop@example.com',status='unsubscribed',marketing_permissions=None)],'total_items':4}
        with patch.dict('os.environ',{'MC_TEST':'fake-us1'}):
            result=mc.page(self.src,None,read,main.COUNTRY_NAMES)
        self.assertEqual([r['email'] for r in result['records']],['yes@example.com'])
        self.assertEqual(result['revoked'],['stop@example.com'])
        self.assertEqual(result['next_cursor'],'3')
    def test_revocation_and_multi_country(self):
        db=main.connect(self.root/'db.sqlite')
        try:
            with db: db.execute('INSERT INTO contacts VALUES(?,?,?)',('stop@example.com','stop@example.com','Germany'))
            payload={'records':[dict(email='yes@example.com',country='Canada',consent=True,consent_evidence='fixture')],'revoked':['stop@example.com']}
            sync.sync(db,[self.src],lambda a,b:payload)
            self.assertEqual(db.execute('SELECT count(*) FROM contacts').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT key FROM suppressed').fetchone()[0],'stop@example.com')
            self.assertEqual(db.execute('SELECT country FROM queue').fetchone()[0],'Canada')
        finally: db.close()
    def test_configuration(self):
        p=self.root/'sources.json'
        p.write_text(json.dumps([dict(self.src,enabled=True,authorization_reference='fixture',url='https://bad.example'),dict(self.src,id='bad',enabled=True,authorization_reference='fixture',datacenter='evil.example')]))
        out=sync.read_config(p)
        self.assertEqual(len(out),1)
        self.assertEqual(urlsplit(out[0]['url']).hostname,'us1.api.mailchimp.com')
    def test_market_weighted_rpm(self):
        p=self.root/'report.csv'
        p.write_text('Country,PageViews,EstimatedEarnings\nGermany,1000,10\nGermany,2000,20\nCanada,1,100\nAustralia,1000,20\nFrance,1000,NaN\n')
        ranked=mp.rank(p)
        self.assertEqual(len(ranked),40)
        self.assertEqual(ranked[0],('Australia',1000,20,'sufficient'))
        self.assertEqual(ranked[1],('Germany',3000,10,'sufficient'))
        self.assertEqual(ranked[2][0],'Canada')
        self.assertEqual(ranked[2][3],'insufficient')

if __name__=='__main__': unittest.main()
