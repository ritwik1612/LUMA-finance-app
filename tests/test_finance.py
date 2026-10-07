import shutil
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
import app

def test_management_backups_and_targets(tmp_path):
    import gzip,json
    from datetime import date
    isolated=tmp_path/'management.sqlite3';shutil.copyfile(app.DB,isolated)
    with patch.object(app,'DB',isolated):
        a=TestClient(app.app);b=TestClient(app.app)
        for client,email in [(a,'manage-a@example.test'),(b,'manage-b@example.test')]:
            assert client.post('/api/register',json={'email':email,'password':'long-password','name':'Management QA'}).status_code==200
        assert a.post('/api/accounts',json={'name':'Payroll','opening':'1000','purpose':'salary'}).status_code==200
        w=a.get('/api/workspace').json();pay=next(x for x in w['accounts'] if x['name']=='Payroll')
        assert pay['purpose']=='salary' and pay['balance']==100000
        body={'name':'Payroll reserve','purpose':'salary','archived':True}
        assert b.post('/api/accounts/'+str(pay['id']),json=body).status_code==404
        assert a.post('/api/accounts/'+str(pay['id']),json=body).status_code==200
        assert a.post('/api/transactions',json={'date':str(date.today()),'kind':'expense','description':'Salary','amount':100,'account':pay['id']}).status_code==400
        body['archived']=False;assert a.post('/api/accounts/'+str(pay['id']),json=body).status_code==200
        for kind,description in [('income','Customer receipt'),('expense','Salary payment')]:
            assert a.post('/api/transactions',json={'date':str(date.today()),'kind':kind,'description':description,'amount':100,'account':pay['id']}).status_code==200
        pref={'name':'Renamed business','theme':'light','accent':'#0f8b81','motion':False,'categories':['Payroll','Supplies']}
        assert a.post('/api/settings',json=pref).status_code==200
        assert b.get('/api/workspace').json()['business']['name']=='Management QA'
        assert a.post('/api/settings',json={**pref,'accent':'not-a-color'}).status_code==422
        target={'id':'test-goal','name':'Reserve target','metric':'cash','amount':'2000','deadline':None}
        assert a.post('/api/targets',json={'targets':[target]}).status_code==200
        assert not b.get('/api/workspace').json()['targets']
        response=a.get('/api/backup');assert response.status_code==200
        backup=json.loads(gzip.decompress(response.content));assert backup['version']==2
        assert len(response.content)<len(json.dumps(backup).encode())
        assert 'password' not in backup and 'salt' not in backup
        corrupt=json.loads(json.dumps(backup));corrupt['entries'][0]['debit']+=1
        assert a.post('/api/restore',json=corrupt).status_code==400
        assert a.get('/api/workspace').json()['transactions']
        assert a.post('/api/restore',json=backup).status_code==200
        restored=a.get('/api/workspace').json();assert restored['settings']['accent']=='#0f8b81'
        assert [t['description'] for t in restored['transactions']]==[t['description'] for t in backup['journal']]
        assert restored['targets'][0]['name']=='Reserve target'
        assert next(x for x in restored['accounts'] if x['name']=='Payroll reserve')['balance']==100000
        with app.connect() as c:assert c.execute('SELECT SUM(debit)-SUM(credit) FROM entries').fetchone()[0]==0
        assert a.post('/api/logout').status_code==200
        assert a.post('/api/login',json={'email':'manage-a@example.test','password':'long-password'}).status_code==200
        assert a.get('/api/workspace').json()['settings']['theme']=='light'

def test_workspace_accounting_and_isolation(tmp_path):
    isolated=tmp_path/'test.sqlite3';shutil.copyfile(app.DB,isolated)
    with patch.object(app,'DB',isolated):
        a=TestClient(app.app);b=TestClient(app.app)
        assert a.get('/api/workspace').status_code==401
        assert a.post('/api/register',json={'email':'a@example.test','password':'long-password','name':'Test business','currency':'USD'}).status_code==200
        initial=a.get('/api/workspace').json();bank,wallet=[x['id'] for x in initial['accounts'] if x['type']=='asset']
        assert not initial['transactions']
        from datetime import date
        def tx(kind,amount,account=bank,destination=None):return a.post('/api/transactions',json={'date':str(date.today()),'kind':kind,'description':'Test entry','amount':amount,'account':account,'destination':destination})
        assert tx('funding','1000.00').status_code==200
        assert tx('income','300.00').status_code==200
        assert tx('expense','100.00').status_code==200
        assert tx('transfer','200.00',destination=wallet).status_code==200
        w=a.get('/api/workspace').json();balances={x['id']:x['balance'] for x in w['accounts']}
        assert balances[bank]==100000 and balances[wallet]==20000
        with app.connect() as c:assert c.execute('SELECT SUM(debit)-SUM(credit) FROM entries').fetchone()[0]==0
        assert tx('transfer','10.00',destination=bank).status_code==400
        assert tx('income','0.001').status_code==422
        assert b.post('/api/register',json={'email':'b@example.test','password':'long-password','name':'Other business'}).status_code==200
        assert not b.get('/api/workspace').json()['transactions']
        assert b.post('/api/transactions',json={'date':str(date.today()),'kind':'income','description':'Bad account','amount':'10','account':bank}).status_code==400
        assert a.post('/api/plan',json={'revenue':1000,'expenses':800,'growth':5,'cost_growth':2,'budget':900}).status_code==200
        assert a.get('/api/workspace').json()['plan']['budget']=='900'
        assert a.post('/api/logout').status_code==200
        assert a.get('/api/workspace').status_code==401
        assert a.post('/api/login',json={'email':'a@example.test','password':'wrong-password'}).status_code==401
        assert a.post('/api/login',json={'email':'a@example.test','password':'long-password'}).status_code==200

def test_opening_balances_validation_and_persistence(tmp_path):
    from datetime import date,timedelta
    isolated=tmp_path/'more.sqlite3';shutil.copyfile(app.DB,isolated)
    with patch.object(app,'DB',isolated):
        c=TestClient(app.app)
        creds={'email':'features-test@example.test','password':'valid-password','name':'Feature verification','currency':'INR'}
        assert c.post('/api/register',json=creds).status_code==200
        assert c.post('/api/register',json=creds).status_code==409
        assert c.post('/api/accounts',json={'name':'Savings','opening':'2500.45'}).status_code==200
        w=c.get('/api/workspace').json();savings=next(a for a in w['accounts'] if a['name']=='Savings')
        assert savings['balance']==250045
        assert w['transactions'][0]['kind']=='funding'
        assert c.post('/api/accounts',json={'name':'   ','opening':0}).status_code==400
        assert c.post('/api/accounts',json={'name':'Invalid','opening':-1}).status_code==422
        bank=next(a for a in w['accounts'] if a['type']=='asset')['id']
        assert c.post('/api/transactions',json={'date':str(date.today()+timedelta(days=1)),'kind':'income','description':'Future','amount':5,'account':bank}).status_code==400
        assert c.post('/api/transactions',json={'date':str(date.today()),'kind':'income','description':'   ','amount':5,'account':bank}).status_code==400
        assert c.post('/api/plan',json={'revenue':1000,'expenses':800,'growth':101,'cost_growth':2,'budget':900}).status_code==422
        assert c.post('/api/plan',json={'revenue':1000,'expenses':800,'growth':5,'cost_growth':2,'budget':900}).status_code==200
        c.post('/api/logout');assert c.post('/api/login',json=creds).status_code==200
        assert c.get('/api/workspace').json()['plan']['budget']=='900'
        assert c.post('/api/accounts',json={'name':'Blocked'},headers={'Origin':'https://outside.test'}).status_code==403
        for route in ('/','/dashboard','/transactions','/accounts','/forecast','/budgets'):assert c.get(route).status_code==200

def test_exports_authenticated_content_and_file_integrity(tmp_path):
    import io,zipfile,json
    from openpyxl import load_workbook
    import fitz
    isolated=tmp_path/'exports.sqlite3';shutil.copyfile(app.DB,isolated)
    with patch.object(app,'DB',isolated):
        c=TestClient(app.app)
        assert c.get('/api/export/pdf').status_code==401
        c.post('/api/register',json={'email':'export-audit@example.test','password':'valid-password','name':'Export audit'})
        c.post('/api/accounts',json={'name':'Savings','opening':'1234.56'})
        for fmt in ('pdf','csv','xlsx','json'):
            r=c.get('/api/export/'+fmt);assert r.status_code==200;assert 'attachment' in r.headers['content-disposition']
            if fmt=='pdf':
                pdf=fitz.open(stream=r.content,filetype='pdf');assert len(pdf)>=5;assert '1,234.56' in ''.join(p.get_text() for p in pdf)
                Path('data/export-verification.pdf').write_bytes(r.content)
                pdf[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save('data/export-verification.png')
            if fmt=='csv':
                z=zipfile.ZipFile(io.BytesIO(r.content));assert 'accounts.csv' in z.namelist();assert '1,234.56' in z.read('accounts.csv').decode('utf-8-sig')
            if fmt=='xlsx':assert set(load_workbook(io.BytesIO(r.content)).sheetnames)=={'Summary','Accounts','Transactions','Forecast','Budget','Targets','Read me'}
            if fmt=='json':
                data=r.json();assert 'sessions' not in data and 'password' not in r.text and data['data']['business']['name']=='Export audit'
        assert c.get('/api/export/csv?scope=transactions').headers['content-type'].startswith('text/csv')
        assert c.get('/api/export/pdf?scope=wrong').status_code==422
