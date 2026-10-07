"""Small PostgreSQL adapter for the existing journal queries."""
import re
import psycopg
from psycopg.rows import dict_row
class Row(dict):
    def __getitem__(self,key):return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)
class Cursor:
    def __init__(self,cursor,lastrowid=None):self.cursor=cursor;self.lastrowid=lastrowid
    def fetchone(self):
        row=self.cursor.fetchone();return Row(row) if row is not None else None
    def __iter__(self):return (Row(row) for row in self.cursor)
class Connection:
    def __init__(self,url):self.connection=psycopg.connect(url,row_factory=dict_row,connect_timeout=15)
    def __enter__(self):return self
    def __exit__(self,kind,value,tb):
        try:self.connection.commit() if kind is None else self.connection.rollback()
        finally:self.connection.close()
    def execute(self,sql,args=()):
        sql=sql.replace('?','%s');insert=re.match(r'INSERT INTO (businesses|accounts|journal)\b',sql,re.I)
        if insert:sql+=' RETURNING id'
        cursor=self.connection.execute(sql,args)
        return Cursor(cursor,cursor.fetchone()['id'] if insert else None)
    def executemany(self,sql,rows):
        with self.connection.cursor() as c:c.executemany(sql.replace('?','%s'),rows)
    def executescript(self,script):
        for statement in script.split(';'):
            if not statement.strip():continue
            statement=statement.replace('id INTEGER PRIMARY KEY','id BIGSERIAL PRIMARY KEY')
            statement=re.sub(r'\bINTEGER\b','BIGINT',statement)
            self.connection.execute(statement)
