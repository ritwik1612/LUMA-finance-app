"""Portable finance exports. No credentials or session tokens enter exports."""
import csv, io, json, zipfile
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from html import escape
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

DISCLAIMER='Cash-based management report. Forecast assumes same-month collection and payment; excludes taxes, loans, capital expenditure and payment delays.'
def cash(n):return f'{Decimal(n)/100:,.2f}'
def safe(v):
    s=str(v)
    return "'"+s if s.lstrip().startswith(('=','+','-','@','\t','\r')) else s

def export_tables(w):
    currency=w['business']['currency'];today=date.today();month=today.strftime('%Y-%m')
    cash_balance=sum(a['balance'] for a in w['accounts'] if a['type']=='asset')
    tx=w['transactions'];p=w['plan'];expenses=sum(t['amount'] for t in tx if t['kind']=='expense' and t['date'].startswith(month))
    revenue=sum(t['amount'] for t in tx if t['kind']=='income' and t['date'].startswith(month))
    summary=[['Measure','Amount','Currency'],['Available cash',cash(cash_balance),currency],['Revenue this month',cash(revenue),currency],['Expenses this month',cash(expenses),currency],['Net cash profit this month',cash(revenue-expenses),currency]]
    accounts=[['Account','Type','Recorded balance','Currency']]+[[a['name'],a['type'],cash(a['balance']),currency] for a in w['accounts'] if a['type']=='asset']
    transactions=[['Date','Type','Description','Category','Amount','Currency']]+[[t['date'],t['kind'],t['description'],t['category'],cash(t['amount']),currency] for t in tx]
    forecast=[['Month','Scenario','Revenue','Expenses','Closing cash','Currency']]
    for scenario,adjust in [('Base',0),('Optimistic',3),('Cautious',-3)]:
        balance=cash_balance
        for i in range(12):
            index=today.year*12+today.month+i;y,m=divmod(index,12)
            r=int((Decimal(str(p['revenue']))*100*(1+Decimal(str(p['growth']+adjust))/100)**i).quantize(Decimal(1),rounding=ROUND_HALF_UP))
            e=int((Decimal(str(p['expenses']))*100*(1+Decimal(str(p['cost_growth']))/100)**i).quantize(Decimal(1),rounding=ROUND_HALF_UP));balance+=r-e
            forecast.append([f'{y}-{m+1:02d}',scenario,cash(r),cash(e),cash(balance),currency])
    budget=[['Measure','Value','Unit'],['Monthly budget',str(p['budget']),currency],['Spent this month',cash(expenses),currency],['Remaining budget',cash(int(Decimal(str(p['budget']))*100)-expenses),currency],['Monthly revenue assumption',str(p['revenue']),currency],['Monthly expense assumption',str(p['expenses']),currency],['Monthly revenue growth',str(p['growth']),'percent'],['Monthly cost growth',str(p['cost_growth']),'percent']]
    return {'Summary':summary,'Accounts':accounts,'Transactions':transactions,'Forecast':forecast,'Budget':budget}

def export_file(w,fmt,scope='all'):
    tables=export_tables(w)
    if scope!='all':tables={scope.title():tables[scope.title()]}
    out=io.BytesIO()
    if fmt=='json':return json.dumps({'version':1,'exported_on':date.today().isoformat(),'business':w['business'],'data':w if scope=='all' else tables,'limitations':DISCLAIMER},indent=2).encode(),'application/json','json'
    if fmt=='csv':
        def csv_bytes(rows):
            s=io.StringIO(newline='');writer=csv.writer(s);writer.writerows([[safe(v) for v in row] for row in rows]);return s.getvalue().encode('utf-8-sig')
        if scope!='all':return csv_bytes(next(iter(tables.values()))),'text/csv','csv'
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for name,rows in tables.items():z.writestr(name.lower()+'.csv',csv_bytes(rows))
            z.writestr('README.txt',DISCLAIMER+'\nBusiness: '+w['business']['name']+'\nCurrency: '+w['business']['currency'])
        return out.getvalue(),'application/zip','zip'
    if fmt=='xlsx':
        wb=Workbook();wb.remove(wb.active)
        for name,rows in tables.items():
            sheet=wb.create_sheet(name)
            numeric={'Summary':{1},'Accounts':{2},'Transactions':{4},'Forecast':{2,3,4},'Budget':{1}}[name]
            for index,row in enumerate(rows):
                sheet.append([float(Decimal(str(v).replace(',',''))) if index and column in numeric else safe(v) for column,v in enumerate(row)])
            for row in sheet.iter_rows(min_row=2):
                for column in numeric:row[column].number_format='#,##0.00;[Red]-#,##0.00'
            sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
            for cell in sheet[1]:cell.font=Font(color='FFFFFF',bold=True);cell.fill=PatternFill('solid',fgColor='302B50')
            for column in sheet.columns:
                letter=column[0].column_letter;sheet.column_dimensions[letter].width=min(55,max(16,max(len(str(c.value or '')) for c in column)+2))
        notes=wb.create_sheet('Read me');notes.append(['Business',w['business']['name']]);notes.append(['Currency',w['business']['currency']]);notes.append(['Report date',str(date.today())]);notes.append(['Limitations',DISCLAIMER]);notes.column_dimensions['A'].width=20;notes.column_dimensions['B'].width=90;notes['B4'].alignment=Alignment(wrap_text=True);notes.row_dimensions[4].height=50
        wb.save(out);return out.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','xlsx'
    styles=getSampleStyleSheet();styles['Title'].textColor=colors.HexColor('#302B50');styles['Normal'].fontSize=9;styles['Normal'].leading=13
    doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=35,leftMargin=35,topMargin=38,bottomMargin=38)
    story=[Paragraph('LUMA / FINANCE',styles['Title']),Paragraph(escape(w['business']['name']),styles['Heading2']),Paragraph(f"{date.today().isoformat()} | Reporting currency: {escape(w['business']['currency'])}",styles['Normal']),Spacer(1,14),Paragraph(DISCLAIMER,styles['Normal']),Spacer(1,18)]
    for index,(name,rows) in enumerate(tables.items()):
        if index:story.append(PageBreak())
        story.append(Paragraph(escape(name),styles['Heading1']));story.append(Spacer(1,12))
        cells=[[Paragraph(escape(str(v)),styles['Normal']) for v in row] for row in rows]
        if name=='Forecast':width=[65,75,95,95,115,70]
        elif name=='Transactions':width=[65,55,145,90,65,55]
        else:width=[515/len(rows[0])]*len(rows[0])
        table=Table(cells,colWidths=width,repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E9E5F5')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#ADA0CC')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8F7FC')])]))
        story.append(table)
        if len(rows)==1:story.append(Paragraph('No records entered yet.',styles['Normal']))
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#777788'));canvas.drawString(35,22,'Luma Finance | Cash-based management report');canvas.drawRightString(A4[0]-35,22,f'Page {doc.page}')
    doc.build(story,onFirstPage=footer,onLaterPages=footer);return out.getvalue(),'application/pdf','pdf'
