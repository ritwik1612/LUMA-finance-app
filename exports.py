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
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics.shapes import Drawing, Line, PolyLine, String, Circle
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
    targets=[['Target','Measure','Target amount','Current amount','Deadline','Currency']]+[[g['name'],g['metric'],cash(int(Decimal(str(g['amount']))*100)),cash(cash_balance if g['metric']=='cash' else revenue),g.get('deadline') or 'None',currency] for g in w.get('targets',[])]
    return {'Summary':summary,'Accounts':accounts,'Transactions':transactions,'Forecast':forecast,'Budget':budget,'Targets':targets}

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
            numeric={'Summary':{1},'Accounts':{2},'Transactions':{4},'Forecast':{2,3,4},'Budget':{1},'Targets':{2,3}}[name]
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
    ink=colors.HexColor('#17263B');muted=colors.HexColor('#607086');paper=colors.HexColor('#F2F5FA')
    accent=w.get('settings',{}).get('accent','purple');accent=colors.HexColor({'purple':'#7862BF','blue':'#3877C9','teal':'#168775','rose':'#B84674','amber':'#9B6E15'}.get(accent,accent if accent.startswith('#') else '#7862BF'))
    styles=getSampleStyleSheet();styles['Title'].textColor=ink;styles['Title'].alignment=0;styles['Title'].fontSize=30;styles['Title'].leading=35
    styles['Normal'].fontSize=9;styles['Normal'].leading=13;styles['Normal'].textColor=ink
    styles['Heading1'].textColor=ink;styles['Heading1'].fontSize=22;styles['Heading1'].leading=28
    styles.add(ParagraphStyle('Caption',fontName='Helvetica',fontSize=8,leading=12,textColor=muted))
    styles.add(ParagraphStyle('TableHead',fontName='Helvetica-Bold',fontSize=8,leading=11,textColor=colors.white))
    styles.add(ParagraphStyle('KPI',fontName='Helvetica-Bold',fontSize=16,leading=24,textColor=ink))
    doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=35,leftMargin=35,topMargin=72,bottomMargin=48,title='LUMA Financial Report',author='LUMA Finance')
    story=[Paragraph('Financial report',styles['Title']),Paragraph(escape(w['business']['name']),styles['Heading2']),Paragraph(f"PREPARED {date.today().strftime('%d %b %Y').upper()} &nbsp; / &nbsp; {escape(w['business']['currency'])} REPORTING",styles['Caption']),Spacer(1,12),Paragraph(DISCLAIMER,styles['Caption']),Spacer(1,20)]
    def forecast_chart():
        # Draw directly into the PDF so chart labels remain sharp when printed.
        rows=[r for r in export_tables(w)['Forecast'][1:] if r[1]=='Base'];values=[float(r[4].replace(',','')) for r in rows]
        d=Drawing(520,160);lo=min(0,*values);hi=max(1,*values);span=hi-lo;left=70;right=505;top=140;bottom=30
        for i in range(4):
            v=lo+span*i/3;y=bottom+(v-lo)/span*(top-bottom)
            d.add(Line(left,y,right,y,strokeColor=colors.HexColor('#DFE5EE'),strokeWidth=.5));d.add(String(left-8,y-3,f'{v:,.0f}',fontSize=7,textAnchor='end',fillColor=muted))
        points=[]
        for i,v in enumerate(values):
            x=left+i*(right-left)/11;y=bottom+(v-lo)/span*(top-bottom);points.extend([x,y]);d.add(Circle(x,y,2.3,fillColor=accent,strokeColor=accent))
            if i%2==0 or i==11:d.add(String(x,12,rows[i][0][2:],fontSize=7,textAnchor='middle',fillColor=muted))
        d.add(PolyLine(points,strokeColor=accent,strokeWidth=2));return d
    for index,(name,rows) in enumerate(tables.items()):
        if index:story.append(PageBreak())
        story.append(Paragraph(escape(name),styles['Heading1']));story.append(Spacer(1,12))
        if name=='Summary':
            cards=[[Paragraph(escape(row[0].replace(' this month','').upper()),styles['Caption']),Paragraph(escape(row[1]),styles['KPI'])] for row in rows[1:]]
            kpis=Table([[Table([[x] for x in card],colWidths=[111]) for card in cards]],colWidths=[131]*4)
            kpis.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),paper),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#E2E8F0')),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]));story.extend([kpis,Spacer(1,18)])
        if name=='Forecast':story.extend([Paragraph('BASE SCENARIO / PROJECTED CASH',styles['Caption']),forecast_chart(),Spacer(1,15)])
        cells=[[Paragraph(escape(str(v)),styles['TableHead'] if i==0 else styles['Normal']) for v in row] for i,row in enumerate(rows)]
        if name=='Forecast':width=[65,75,95,95,115,70]
        elif name=='Transactions':width=[65,55,145,90,65,55]
        else:width=[515/len(rows[0])]*len(rows[0])
        table=Table(cells,colWidths=width,repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),ink),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,0),1,accent),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#E1E7EF')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,paper])]))
        story.append(table)
        if len(rows)==1:story.append(Paragraph('No records entered yet.',styles['Normal']))
    def footer(canvas,doc):
        canvas.setFillColor(ink);canvas.roundRect(35,A4[1]-48,28,25,6,fill=1,stroke=0);canvas.setFillColor(colors.white);canvas.setFont('Helvetica-Bold',12);canvas.drawString(45,A4[1]-40,'L')
        canvas.setFillColor(ink);canvas.setFont('Helvetica-Bold',10);canvas.drawString(73,A4[1]-39,'LUMA / FINANCE')
        canvas.setStrokeColor(accent);canvas.setLineWidth(2);canvas.line(A4[0]-105,A4[1]-36,A4[0]-35,A4[1]-36)
        canvas.setStrokeColor(colors.HexColor('#DDE4ED'));canvas.setLineWidth(.5);canvas.line(35,37,A4[0]-35,37)
        canvas.setFont('Helvetica',8);canvas.setFillColor(muted);canvas.drawString(35,22,'LUMA  /  Cash-based management report');canvas.drawRightString(A4[0]-35,22,f'{doc.page:02d}')
    doc.build(story,onFirstPage=footer,onLaterPages=footer);return out.getvalue(),'application/pdf','pdf'
