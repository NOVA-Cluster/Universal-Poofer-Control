#!/usr/bin/env python3
"""Render the canonical Markdown customer guide and its vector wiring figures.

Run with the bundled/document Python runtime containing reportlab and Pillow.
No schematic, PCB, firmware behavior or operating specification is modified.
"""
from pathlib import Path
import re
import os
from xml.sax.saxutils import escape
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                               Spacer, PageBreak, Table, TableStyle, Image,
                               Preformatted, KeepTogether, CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String
from reportlab.graphics import renderSVG

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'docs/hardware-user-guide.md'
OUTPUT = ROOT/'output/pdf/Universal_Poofer_Control_Hardware_User_Guide.pdf'
FIGURES = ROOT/'docs/figures'
GREEN = colors.HexColor('#173F35')
GOLD = colors.HexColor('#AE813E')
INK = colors.HexColor('#233A35')
MUTED = colors.HexColor('#526861')
PALE = colors.HexColor('#EDF3EF')
LINE = colors.HexColor('#CCD8D2')
RETURN = colors.HexColor('#32697A')

font_dir = Path(rl_config.__file__).parent/'fonts'
for name, filename in [('Guide','Vera.ttf'),('Guide-Bold','VeraBd.ttf'),('Guide-Italic','VeraIt.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(font_dir/filename)))
pdfmetrics.registerFontFamily('Guide',normal='Guide',bold='Guide-Bold',italic='Guide-Italic',boldItalic='Guide-Bold')

def text(d,x,y,label,size=15,color=INK,bold=False):
    d.add(String(x,y,label,fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,fillColor=color))

def box(d,x,y,w,h,title):
    d.add(Rect(x,y,w,h,rx=6,ry=6,fillColor=PALE,strokeColor=LINE,strokeWidth=1.2))
    text(d,x+12,y+h-25,title,16,GREEN,True)

def wire(d,points,color=GREEN,width=2.4):
    for a,b in zip(points,points[1:]):
        d.add(Line(*a,*b,strokeColor=color,strokeWidth=width))

def dot(d,x,y,color=GREEN):
    d.add(Circle(x,y,3.5,fillColor=color,strokeColor=color))

def valve_figure():
    d=Drawing(900,300)
    box(d,15,55,180,220,'External 12 V supply')
    text(d,28,212,'Valve branch',14)
    text(d,28,180,'Positive',14);text(d,28,82,'Negative',14,RETURN)
    box(d,300,160,200,115,'Relay 1 contacts')
    text(d,317,222,'J31.1 COM',15);text(d,407,222,'J31.2 NO',15)
    wire(d,[(195,195),(245,195),(300,195),(350,195)])
    d.add(Rect(231,187,29,16,fillColor=colors.white,strokeColor=GOLD,strokeWidth=1.8))
    text(d,214,222,'Fuse',13,GOLD)
    dot(d,350,195);dot(d,430,195);wire(d,[(350,195),(410,213)]);wire(d,[(430,195),(665,195)])
    text(d,320,173,'NC auxiliary is unused',12,MUTED)
    box(d,665,125,200,150,'Your 12 VDC valve')
    text(d,678,174,'Positive / NO',13);text(d,678,143,'Negative',13,RETURN)
    wire(d,[(195,90),(765,90),(765,125)],RETURN)
    dot(d,550,195);dot(d,550,90,RETURN)
    text(d,522,231,'J41.1 NO',15,GREEN,True)
    text(d,519,57,'J41.2 RETURN',15,RETURN,True)
    wire(d,[(550,195),(550,155)]);wire(d,[(550,122),(550,90)],RETURN)
    d.add(Rect(520,122,60,33,rx=3,ry=3,fillColor=colors.white,strokeColor=GOLD,strokeWidth=1.5))
    text(d,526,142,'Onboard',10,GOLD);text(d,531,129,'clamp',10,GOLD)
    text(d,15,28,'RETURN joins valve negative AND the external supply negative.',15,RETURN,True)
    text(d,15,11,'J2 separately powers coils/analog; it does not feed all valve loads.',13,MUTED)
    return d

def contact_figure():
    d=Drawing(900,290)
    box(d,15,60,215,205,'Ordinary input 1')
    text(d,28,201,'J11.1 FIELD',15);text(d,28,115,'J11.2 GND',15,RETURN)
    wire(d,[(230,193),(300,193)]);dot(d,300,193)
    wire(d,[(300,193),(350,145)]);dot(d,350,130)
    wire(d,[(350,130),(230,130)],RETURN)
    text(d,264,227,'Your dry switch',14,GREEN,True)
    text(d,254,82,'Board supplies nominal 20 mA',12,MUTED)
    box(d,470,60,215,205,'Single-board stop')
    text(d,483,201,'J9.1 FIELD',15);text(d,483,150,'J9.2 CHAIN OUT',15)
    box(d,735,133,150,100,'NC contact')
    text(d,748,169,'Opens when',12);text(d,748,152,'stop is pressed',12)
    wire(d,[(685,193),(735,193)]);wire(d,[(655,145),(735,145)]);dot(d,655,145)
    wire(d,[(655,145),(655,100),(565,100)])
    dot(d,565,100);dot(d,565,75,RETURN);wire(d,[(565,100),(565,75)],GOLD,4)
    wire(d,[(565,75),(495,75)],RETURN)
    text(d,593,81,'J10 shunt',15,GOLD,True)
    text(d,484,65,'GND',11,RETURN)
    text(d,15,27,'Close FIELD to GND. Do not add an external logic-voltage source.',13,MUTED)
    text(d,470,27,'Fit JP1 host. J10 closes only on a single board or the chain tail.',12,MUTED)
    return d

def chain_figure():
    d=Drawing(900,300)
    for i,x in enumerate([20,330,640]):
        box(d,x,75,240,200,f'Module {i}: '+('HOST' if i==0 else 'EXPANDER'))
        text(d,x+13,220,'Own J1 / J2 power',14)
        text(d,x+13,195,'JP1 '+('closed' if i==0 else 'open'),14,GREEN,True)
        text(d,x+13,171,'JP2 '+('one pullup provider' if i==0 else 'open'),12)
        text(d,x+13,82,'J10 '+('closed at tail' if i==2 else 'open'),13,GOLD,True)
        text(d,x+32,114,'J9 NC path',15,GOLD)
        wire(d,[(x,132),(x+63,132),(x+125,132),(x+240,132)],GOLD)
        dot(d,x+63,132,GOLD);dot(d,x+125,132,GOLD)
    wire(d,[(260,248),(330,248)]);wire(d,[(570,248),(640,248)])
    text(d,265,268,'DOWN to UP',10,GREEN);text(d,575,268,'DOWN to UP',10,GREEN)
    wire(d,[(260,132),(330,132)],GOLD);wire(d,[(570,132),(640,132)],GOLD)
    text(d,263,150,'Pin 11',15,GOLD);text(d,574,150,'Pin 11',15,GOLD)
    wire(d,[(5,132),(20,132)],GOLD);text(d,7,53,'Host sources stop-loop wetting',13,GOLD)
    wire(d,[(880,132),(891,132),(891,45),(810,45)],RETURN)
    text(d,777,23,'Tail return to GND',13,RETURN)
    text(d,20,11,'One host, one tail terminator, common reference. Chain cables carry NO supply power.',13,MUTED)
    return d

def write_figures():
    FIGURES.mkdir(parents=True,exist_ok=True)
    for name,d in [('valve-wiring',valve_figure()),('contact-stop-wiring',contact_figure()),('expansion-chain',chain_figure())]:
        renderSVG.drawToFile(d,str(FIGURES/(name+'.svg')))

styles={
    'body':ParagraphStyle('body',fontName='Guide',fontSize=10.1,leading=14.2,textColor=INK,spaceAfter=8,allowWidows=0,allowOrphans=0),
    'h2':ParagraphStyle('h2',fontName='Guide-Bold',fontSize=18.5,leading=23,textColor=GREEN,spaceAfter=15,keepWithNext=True),
    'h3':ParagraphStyle('h3',fontName='Guide-Bold',fontSize=12.1,leading=16,textColor=GREEN,spaceBefore=10,spaceAfter=7,keepWithNext=True),
    'cell':ParagraphStyle('cell',fontName='Guide',fontSize=9,leading=12.2,textColor=INK,spaceAfter=0,splitLongWords=True),
    'th':ParagraphStyle('th',fontName='Guide-Bold',fontSize=9,leading=12.2,textColor=colors.white,spaceAfter=0),
    'code':ParagraphStyle('code',fontName='Courier',fontSize=8.8,leading=12,textColor=INK,backColor=PALE,borderPadding=10,spaceBefore=4,spaceAfter=12),
    'caption':ParagraphStyle('caption',fontName='Guide-Italic',fontSize=8.5,leading=11,textColor=MUTED,spaceAfter=12),
    'cover':ParagraphStyle('cover',fontName='Guide-Bold',fontSize=28,leading=33,textColor=GREEN,spaceAfter=12),
    'sub':ParagraphStyle('sub',fontName='Guide',fontSize=18,leading=23,textColor=GOLD,spaceAfter=15),
    'meta':ParagraphStyle('meta',fontName='Guide',fontSize=9,leading=13,textColor=MUTED,spaceAfter=9),
}

def inline(value):
    value=escape(value)
    def link(m):
        target=m[2]
        if not re.match(r'^[a-z]+://',target):
            target=os.path.relpath((SOURCE.parent/target).resolve(),OUTPUT.parent)
        return f'<link href="{target}" color="#236653">{m[1]}</link>'
    value=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,value)
    value=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',value)
    value=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',value)
    return value

class GuideDoc(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(str(path),pagesize=(612,792),leftMargin=54,rightMargin=54,topMargin=52,bottomMargin=51,
                         title='Universal Poofer Control Hardware User Guide',author='Universal Poofer Control',
                         subject='A.3 purchaser setup and operation - engineering preview')
        self.width=504;self.height=689
        self.addPageTemplates(PageTemplate(id='guide',frames=[Frame(54,51,504,689,id='normal',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.chrome))
    def beforeDocument(self):self.heading_index=0
    def chrome(self,canvas,doc):
        canvas.saveState();canvas.setStrokeColor(LINE);canvas.setLineWidth(.6)
        canvas.line(54,39,558,39)
        canvas.setFont('Guide',8);canvas.setFillColor(MUTED)
        canvas.drawString(54,26,'UG-A3-1.0  |  A.3 engineering preview')
        canvas.drawRightString(558,26,str(doc.page))
        if doc.page>1:
            canvas.setFont('Guide-Bold',8);canvas.setFillColor(GREEN);canvas.drawString(54,762,'UNIVERSAL POOFER CONTROL')
            canvas.setFont('Guide',8);canvas.drawRightString(558,762,'HARDWARE USER GUIDE')
        canvas.restoreState()
    def afterFlowable(self,flow):
        if isinstance(flow,Paragraph) and flow.style.name=='h2':
            self.heading_index+=1;label=flow.getPlainText();key='section-'+str(self.heading_index)
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(label,key,0,False)
            self.notify('TOCEntry',(0,label,self.page,key))

def make_table(rows):
    count=len(rows[0]);widths={2:[182,322],3:[124,174,206],4:[132,124,124,124]}.get(count,[504/count]*count)
    if rows[0][0]=='File':widths=[260,244]
    data=[]
    for ri,row in enumerate(rows):data.append([Paragraph(inline(cell),styles['th' if ri==0 else 'cell']) for cell in row])
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),GREEN),('VALIGN',(0,0),(-1,-1),'TOP'),
                           ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
                           ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                           ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
                           ('LINEBELOW',(0,0),(-1,0),.8,GOLD),('LINEBELOW',(0,1),(-1,-1),.3,LINE)]))
    return [KeepTogether([t]),Spacer(1,12)]

def parse_blocks(lines):
    story=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('## '):
            if line.startswith('## 2. '):story.append(PageBreak())
            else:story.append(CondPageBreak(225))
            story.extend([Spacer(1,14),Paragraph(inline(line[3:]),styles['h2'])]);i+=1;continue
        if line.startswith('### '):story.append(Paragraph(inline(line[4:]),styles['h3']));i+=1;continue
        if line.startswith('```'):
            body=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):body.append(lines[i]);i+=1
            story.append(Preformatted('\n'.join(body),styles['code']));i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',x.replace(' ','')) for x in row):rows.append(row)
                i+=1
            story.extend(make_table(rows));continue
        m=re.fullmatch(r'!\[([^\]]+)\]\(([^)]+)\)',line)
        if m:
            path=(SOURCE.parent/m[2]).resolve()
            if path.suffix=='.svg':
                art={'valve-wiring':valve_figure,'contact-stop-wiring':contact_figure,'expansion-chain':chain_figure}[path.stem]()
                scale=504/art.width;art.scale(scale,scale);art.width=504;art.height*=scale
            else:
                from PIL import Image as PILImage
                with PILImage.open(path) as im:w,h=im.size
                width=504;height=width*h/w
                if height>378:height=378;width=height*w/h
                art=Image(str(path),width=width,height=height,hAlign='LEFT')
            story.append(KeepTogether([art,Paragraph(inline(m[1]),styles['caption'])]));i+=1;continue
        m=re.match(r'^(\d+)\. (.*)',line)
        if m:
            style=ParagraphStyle('step',parent=styles['body'],leftIndent=20,firstLineIndent=-20,spaceAfter=9)
            story.append(Paragraph('<b>'+m[1]+'.</b> '+inline(m[2]),style));i+=1;continue
        parts=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#{2,3} |\||```|!\[|\d+\. )',lines[i].strip()):parts.append(lines[i].strip());i+=1
        story.append(Paragraph(inline(' '.join(parts)),styles['body']))
    return story

def main():
    write_figures();OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    lines=SOURCE.read_text().splitlines();split=next(i for i,l in enumerate(lines) if l.startswith('## '))
    front=[l.strip() for l in lines[:split] if l.strip()]
    story=[Spacer(1,22),Paragraph(inline(front[0].lstrip('# ')),styles['cover']),
           Paragraph(inline(front[1]),styles['sub']),Paragraph(inline(front[2]),styles['meta']),
           Paragraph(inline(front[3]),styles['h3'])]
    for block in front[4:]:story.append(Paragraph(inline(block),styles['body']))
    from PIL import Image as PILImage
    board_path=ROOT/'output/pcb/placement_top.png'
    with PILImage.open(board_path) as im:w,h=im.size
    story.append(Spacer(1,12));story.append(Image(str(board_path),width=260*w/h,height=260,hAlign='LEFT'))
    story.extend([PageBreak(),Paragraph('Contents',styles['sub'])])
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle('toc',fontName='Guide',fontSize=10.5,leading=19,textColor=GREEN,leftIndent=0,firstLineIndent=0,spaceBefore=3)]
    story.append(toc);story.append(Spacer(1,24));story.append(Paragraph('First use: identify connectors, wire both supplies and the NC stop, then follow sections 5 and 6 before connecting loads. Expansion and application development follow after the single-board checks.',styles['body']))
    story.extend(parse_blocks(lines[split:]));GuideDoc(OUTPUT).multiBuild(story)
    print(OUTPUT)

if __name__=='__main__':main()
