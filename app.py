"""Luma Finance: local financial workspace with a balanced journal."""
import hashlib, hmac, secrets, sqlite3, json, os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
BASE=Path(__file__).resolve().parent
DB=BASE/'data'/'finance.sqlite3'
DATABASE_URL=os.getenv('DATABASE_URL','').strip()
HOSTED=bool(os.getenv('VERCEL'))
if not HOSTED and not DATABASE_URL:DB.parent.mkdir(exist_ok=True)
app=FastAPI(title='Luma Finance')
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
def connect():
    if DATABASE_URL:
        from database import Connection
        return Connection(DATABASE_URL)
    if HOSTED:raise RuntimeError('Persistent DATABASE_URL is required on Vercel; local SQLite is not supported.')
    c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
with connect() as c:
    c.executescript('''CREATE TABLE IF NOT EXISTS businesses(id INTEGER PRIMARY KEY,email TEXT UNIQUE,name TEXT,currency TEXT,password TEXT,salt TEXT); CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,business INTEGER REFERENCES businesses(id),expires TEXT); CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY,business INTEGER REFERENCES businesses(id),name TEXT,type TEXT); CREATE TABLE IF NOT EXISTS journal(id INTEGER PRIMARY KEY,business INTEGER REFERENCES businesses(id),date TEXT,kind TEXT,description TEXT,category TEXT,amount INTEGER); CREATE TABLE IF NOT EXISTS entries(id INTEGER PRIMARY KEY,journal INTEGER REFERENCES journal(id),account INTEGER REFERENCES accounts(id),debit INTEGER,credit INTEGER); CREATE TABLE IF NOT EXISTS plans(business INTEGER PRIMARY KEY REFERENCES businesses(id),payload TEXT);''')
class Credentials(BaseModel):
    email:str=Field(min_length=3,max_length=200)
    password:str=Field(min_length=8,max_length=200)
    name:str=Field(default='',max_length=100)
    currency:Literal['USD','INR','EUR','GBP']='USD'
class Transaction(BaseModel):
    date:date
    kind:Literal['income','expense','transfer','funding']
    description:str=Field(min_length=1,max_length=150)
    category:str=Field(default='General',max_length=80)
    amount:Decimal=Field(gt=0,le=Decimal('1000000000'),decimal_places=2)
    account:int
    destination:int|None=None
class Account(BaseModel):
    name:str=Field(min_length=1,max_length=80)
    opening:Decimal=Field(default=Decimal(0),ge=0,le=Decimal('1000000000'),decimal_places=2)
class Plan(BaseModel):
    revenue:Decimal=Field(ge=0,le=1000000000)
    expenses:Decimal=Field(ge=0,le=1000000000)
    growth:float=Field(ge=-90,le=100)
    cost_growth:float=Field(ge=-90,le=100)
    budget:Decimal=Field(ge=0,le=1000000000)
def cents(n):return int((Decimal(n)*100).quantize(Decimal(1),rounding=ROUND_HALF_UP))
def password_hash(password,salt):return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),310000).hex()
def business(request):
    token=request.cookies.get('luma_session','')
    with connect() as c:
        row=c.execute('SELECT businesses.* FROM businesses JOIN sessions ON business=businesses.id WHERE token=? AND expires>?',(token,datetime.now(timezone.utc).isoformat())).fetchone()
    if not row:raise HTTPException(401,'Please sign in.')
    return dict(row)
def session(c,bid):
    token=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,bid,(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()));return token
@app.middleware('http')
async def local_only(request,call_next):
    if request.method!='GET' and request.headers.get('origin') and request.headers['origin']!=str(request.base_url).rstrip('/'):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Cross-origin request blocked'},status_code=403)
    response=await call_next(request);response.headers['Cache-Control']='no-store';response.headers['X-Content-Type-Options']='nosniff';return response
@app.get('/')
@app.get('/dashboard')
@app.get('/transactions')
@app.get('/accounts')
@app.get('/forecast')
@app.get('/budgets')
def home():return FileResponse(BASE/'static/index.html')
@app.post('/api/register')
def register(body:Credentials,response:Response):
    if not body.name.strip() or '@' not in body.email:raise HTTPException(400,'Enter a business name and valid email.')
    salt=secrets.token_hex(16)
    with connect() as c:
        try:bid=c.execute('INSERT INTO businesses(email,name,currency,password,salt) VALUES(?,?,?,?,?)',(body.email.strip().lower(),body.name.strip(),body.currency,password_hash(body.password,salt),salt)).lastrowid
        except Exception as exc:
            if isinstance(exc,sqlite3.IntegrityError) or getattr(exc,'sqlstate',None)=='23505':raise HTTPException(409,'An account with this email already exists.')
            raise
        for name,kind in [('Business bank','asset'),('Cash wallet','asset'),('Sales revenue','revenue'),('Business expenses','expense'),('Owner equity','equity')]:c.execute('INSERT INTO accounts(business,name,type) VALUES(?,?,?)',(bid,name,kind))
        token=session(c,bid)
    response.set_cookie('luma_session',token,httponly=True,samesite='strict',secure=HOSTED,max_age=604800);return {'ok':True}
@app.post('/api/login')
def login(body:Credentials,response:Response):
    with connect() as c:
        row=c.execute('SELECT * FROM businesses WHERE email=?',(body.email.strip().lower(),)).fetchone()
        if not row or not hmac.compare_digest(row['password'],password_hash(body.password,row['salt'])):raise HTTPException(401,'Email or password is incorrect.')
        token=session(c,row['id'])
    response.set_cookie('luma_session',token,httponly=True,samesite='strict',secure=HOSTED,max_age=604800);return {'ok':True}
@app.post('/api/logout')
def logout(request:Request,response:Response):
    with connect() as c:c.execute('DELETE FROM sessions WHERE token=?',(request.cookies.get('luma_session',''),))
    response.delete_cookie('luma_session');return {'ok':True}
def add_journal(c,bid,day,kind,description,category,amount,debit,credit):
    jid=c.execute('INSERT INTO journal(business,date,kind,description,category,amount) VALUES(?,?,?,?,?,?)',(bid,str(day),kind,description,category,amount)).lastrowid
    c.executemany('INSERT INTO entries(journal,account,debit,credit) VALUES(?,?,?,?)',[(jid,debit,amount,0),(jid,credit,0,amount)])
@app.post('/api/transactions')
def transaction(body:Transaction,request:Request):
    bid=business(request)['id']
    if not body.description.strip():raise HTTPException(400,'Enter a transaction description.')
    body.description=body.description.strip()
    body.category=body.category.strip() or 'General'
    if body.date>date.today():raise HTTPException(400,'Use Forecast for future plans; transactions must be dated today or earlier.')
    with connect() as c:
        accounts={r['id']:dict(r) for r in c.execute('SELECT * FROM accounts WHERE business=?',(bid,))}
        if body.account not in accounts or accounts[body.account]['type']!='asset':raise HTTPException(400,'Select a cash or bank account.')
        types={r['type']:r['id'] for r in accounts.values() if r['type']!='asset'}
        if body.kind=='transfer':
            if body.destination not in accounts or accounts[body.destination]['type']!='asset' or body.destination==body.account:raise HTTPException(400,'Choose a different destination account.')
            debit,credit=body.destination,body.account
        elif body.kind=='expense':debit,credit=types['expense'],body.account
        else:debit,credit=body.account,types['revenue' if body.kind=='income' else 'equity']
        add_journal(c,bid,body.date,body.kind,body.description,body.category,cents(body.amount),debit,credit)
    return {'ok':True}
@app.post('/api/accounts')
def account(body:Account,request:Request):
    bid=business(request)['id']
    if not body.name.strip():raise HTTPException(400,'Enter an account name.')
    with connect() as c:
        aid=c.execute('INSERT INTO accounts(business,name,type) VALUES(?,?,?)',(bid,body.name.strip(),'asset')).lastrowid
        if body.opening:
            equity=c.execute("SELECT id FROM accounts WHERE business=? AND type='equity'",(bid,)).fetchone()[0]
            add_journal(c,bid,date.today(),'funding','Opening balance · '+body.name,'Opening balance',cents(body.opening),aid,equity)
    return {'ok':True}
@app.post('/api/plan')
def plan(body:Plan,request:Request):
    bid=business(request)['id']
    with connect() as c:c.execute('INSERT INTO plans VALUES(?,?) ON CONFLICT(business) DO UPDATE SET payload=excluded.payload',(bid,body.model_dump_json()))
    return {'ok':True}
@app.get('/api/workspace')
def workspace(request:Request):
    b=business(request)
    with connect() as c:
        accounts=[dict(r) for r in c.execute('SELECT a.id,a.name,a.type,COALESCE(SUM(e.debit-e.credit),0) balance FROM accounts a LEFT JOIN entries e ON e.account=a.id WHERE a.business=? GROUP BY a.id',(b['id'],))]
        transactions=[dict(r) for r in c.execute('SELECT * FROM journal WHERE business=? ORDER BY date DESC,id DESC',(b['id'],))]
        p=c.execute('SELECT payload FROM plans WHERE business=?',(b['id'],)).fetchone()
    for account in accounts:account['balance']=int(account['balance'])
    return {'business':{k:b[k] for k in ('name','email','currency')},'accounts':accounts,'transactions':transactions,'plan':json.loads(p[0]) if p else {'revenue':0,'expenses':0,'growth':5,'cost_growth':2,'budget':0}}

@app.get('/api/export/{fmt}')
def export(fmt:Literal['pdf','csv','xlsx','json'],request:Request,scope:Literal['all','summary','accounts','transactions','forecast','budget']='all'):
    from exports import export_file
    from fastapi.responses import Response
    payload,mime,extension=export_file(workspace(request),fmt,scope)
    return Response(payload,media_type=mime,headers={'Content-Disposition':f'attachment; filename="luma-{scope}-{date.today()}.{extension}"'})
