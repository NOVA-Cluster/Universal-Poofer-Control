#!/usr/bin/env python3
"""Reproducible KiCad schematic source builder; native symbols and editable sheets."""
import copy, csv, json, math, re, sys, uuid
from pathlib import Path
from kicad_sexp import parse, parse_file, find_all, find_first
ROOT=Path(__file__).resolve().parents[1]
import os
LIB=Path(os.environ.get('KICAD_SYMBOL_DIR','/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols' if sys.platform=='darwin' else '/usr/share/kicad/symbols'))
PARTS=json.loads((ROOT/'bom/parts.json').read_text())
PROJECT='Universal_Poofer_Control'
NS=uuid.UUID('10c84b56-174d-4894-96c3-14220cd0b416')
def uid(key): return str(uuid.uuid5(NS,key))
def q(s): return json.dumps(str(s),ensure_ascii=False)
def snap(x): return round(round(x/1.27)*1.27,5)
def f(x): return f'{snap(x):.5f}'.rstrip('0').rstrip('.')
def sexp(node):
    if not isinstance(node,list): return q(node)
    quoted={'symbol':{1},'property':{1,2},'name':{1},'number':{1},'extends':{1},'description':{1}}
    out=[node[0]]
    for i,v in enumerate(node[1:],1):
        if isinstance(v,list): out.append(sexp(v))
        elif i in quoted.get(node[0],set()): out.append(q(v))
        else: out.append(str(v))
    return '('+' '.join(out)+')'
libs={}
def get_symbol(libid):
    if libid=='Poofer:PCA9517AD':
        def pin(n,name,kind,x,y,a):return ['pin',kind,'line',['at',str(x),str(y),str(a)],['length','2.54'],['name',name,['effects',['font',['size','1','1']]]],['number',str(n),['effects',['font',['size','1','1']]]]]
        return ['symbol',libid,['pin_names',['offset','0.508']],['in_bom','yes'],['on_board','yes'],['property','Reference','U',['at','0','10.16','0'],['effects',['font',['size','1.27','1.27']]]],['property','Value','PCA9517AD',['at','0','-10.16','0'],['effects',['font',['size','1.27','1.27']]]],['symbol','PCA9517AD_0_1',['rectangle',['start','-7.62','7.62'],['end','7.62','-7.62'],['stroke',['width','0.254'],['type','default']],['fill',['type','background']]]],['symbol','PCA9517AD_1_1',pin(1,'VCCA','power_in',-2.54,10.16,270),pin(8,'VCCB','power_in',2.54,10.16,270),pin(4,'GND','power_in',0,-10.16,90),pin(2,'SCLA','bidirectional',-10.16,2.54,0),pin(3,'SDAA','bidirectional',-10.16,-2.54,0),pin(7,'SCLB','bidirectional',10.16,2.54,180),pin(6,'SDAB','bidirectional',10.16,-2.54,180),pin(5,'EN','input',-10.16,-5.08,0)]]
    if libid=='Poofer:74HC32':
        src=get_symbol('74xx:74LS32');src[1]=libid
        for s in find_all(src,'symbol'):s[1]=s[1].replace('74LS32','74HC32')
        return src
    if libid=='Poofer:MJD350T4G':
        src=get_symbol('Transistor_BJT:Q_PNP_BCE');src[1]=libid
        for s in find_all(src,'symbol'):s[1]=s[1].replace('Q_PNP_BCE','MJD350T4G')
        return src
    if libid=='Poofer:TLV803EA30DBZR':
        def pin(n,name,kind,x,y,a):return ['pin',kind,'line',['at',str(x),str(y),str(a)],['length','2.54'],['name',name,['effects',['font',['size','1.0','1.0']]]],['number',str(n),['effects',['font',['size','1.0','1.0']]]]]
        return ['symbol',libid,['pin_names',['offset','0.508']],['in_bom','yes'],['on_board','yes'],['property','Reference','U',['at','0','7.62','0'],['effects',['font',['size','1.27','1.27']]]],['property','Value','TLV803EA30DBZR',['at','0','-7.62','0'],['effects',['font',['size','1.27','1.27']]]],['symbol','TLV803EA30DBZR_0_1',['rectangle',['start','-5.08','5.08'],['end','5.08','-5.08'],['stroke',['width','0.254'],['type','default']],['fill',['type','background']]]],['symbol','TLV803EA30DBZR_1_1',pin(3,'VDD','power_in',0,7.62,270),pin(1,'GND','power_in',0,-7.62,90),pin(2,'RESET_N','open_collector',7.62,0,180)]]
    if libid in ['Poofer:TLV431AIDBZR','Poofer:MJD340T4G']:
        parent='Reference_Voltage:TL431DBZ' if 'TLV431' in libid else 'Transistor_BJT:Q_NPN_BCE'
        src=get_symbol(parent);src[1]=libid
        for s in find_all(src,'symbol'):
            s[1]=libid.split(':')[1]+s[1][s[1].rfind('_',0,s[1].rfind('_')):]
            for p in find_all(s,'pin'):
                if 'TLV431' in libid:find_first(p,'number')[1]={'REF':'1','K':'2','A':'3'}[find_first(p,'name')[1]]
        return src
    if libid=='Poofer:BAT54_215':
        src=get_symbol('Device:D_Schottky');src[1]=libid
        for s in find_all(src,'symbol'):
            s[1]=s[1].replace('D_Schottky','BAT54_215')
            for p in find_all(s,'pin'):
                number=find_first(p,'number');number[1]={'1':'3','2':'1'}[number[1]]
        return src
    lib,name=libid.split(':')
    if lib not in libs: libs[lib]={s[1]:s for s in find_all(parse_file(LIB/f'{lib}.kicad_sym'),'symbol')}
    src=copy.deepcopy(libs[lib][name]); parent=find_first(src,'extends')
    if parent:
        base=get_symbol(lib+':'+parent[1]); own={p[1] for p in find_all(src,'property')}
        body=[]
        for item in base[2:]:
            if isinstance(item,list) and item[0]=='property' and item[1] in own: continue
            if isinstance(item,list) and item[0]=='symbol': item[1]=name+item[1][item[1].rfind('_',0,item[1].rfind('_')):]
            body.append(item)
        src=['symbol',libid]+body+[x for x in src[2:] if isinstance(x,list) and x[0] not in {'extends','embedded_fonts'}]
    src[1]=libid
    return src

class Sheet:
    def __init__(self,name,title,path=None):
        self.name=name; self.title=title; self.uuid=uid(name); self.path=path or '/'+self.uuid
        self.items=[];self.symbols={};self.counter=0;self.components=[];self.wires=[];self.points=set();self.group='misc';self.channel=None;self.bank=None;self.page='1'
    def add(self,txt): self.items.append(txt)
    def nextid(self):
        self.counter+=1; return uid(self.name+':item:'+str(self.counter))
    def text(self,s,x,y,size=1.27):
        self.add(f'(text {q(s)} (at {f(x)} {f(y)} 0) (effects (font (size {size} {size})) (justify left top)) (uuid {q(self.nextid())}))')
    def block(self,title,x,y,w,h,subtitle=''):
        self.add(f'(rectangle (start {f(x)} {f(y)}) (end {f(x+w)} {f(y+h)}) (stroke (width 0.254) (type default)) (fill (type none)) (uuid {q(self.nextid())}))')
        self.text(title,x+4,y+4,1.45)
        if subtitle:self.text(subtitle,x+4,y+10,1.0)
    def local(self,net,x,y,angle=0):
        self.points.add((snap(x),snap(y)))
        self.add(f'(label {q(net)} (at {f(x)} {f(y)} {angle}) (effects (font (size 1 1)) (justify left bottom)) (uuid {q(self.nextid())}))')
    def wire(self,a,b):
        a=tuple(snap(v) for v in a);b=tuple(snap(v) for v in b)
        if a==b:return
        self.wires.append((a,b));self.points.update([a,b])
    def junction(self,x,y):
        self.add(f'(junction (at {f(x)} {f(y)}) (diameter 0) (color 0 0 0 0) (uuid {q(self.nextid())}))')
    def label(self,net,x,y,angle=0):
        # Local wire stubs and global labels make sheet-to-sheet connections explicit.
        self.points.add((snap(x),snap(y)));just='right' if angle in [0,90] else 'left'
        self.add(f'(global_label {q(net)} (shape passive) (at {f(x)} {f(y)} {angle}) (effects (font (size 1.0 1.0)) (justify {just})) (uuid {q(self.nextid())}) (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {f(x)} {f(y)} {angle}) (effects (font (size 1 1)) (hide yes))))')
    def part(self,libid,ref,code,x,y,angle=0,unit=1,value=None,footprint=None,notes='',props=True):
        symbol=get_symbol(libid);self.symbols[libid]=symbol
        p=PARTS.get(code,{})
        value=value or p.get('mpn',libid.split(':')[1]); sf=find_first(symbol,'property')
        sourceprops={a[1]:a[2] for a in find_all(symbol,'property')}
        footprint=footprint if footprint is not None else sourceprops.get('Footprint','')
        key=uid(self.name+ref+str(unit))
        properties={'Reference':ref,'Value':value,'Footprint':footprint,'Datasheet':p.get('datasheet_url',sourceprops.get('Datasheet',''))}
        if code:
            properties.update({'MPN':p.get('mpn',value),'Manufacturer':p.get('manufacturer',''),'LCSC':code,'JLCPCB Class':'Basic' if p.get('is_basic') else 'Extended','JLCPCB Stock':str(p.get('stock','Unknown')),'Stock checked':'2026-10-03','BOM Comments':notes})
        # Place text independently of symbol angle so passive values remain readable.
        refxy=(x,y-4.8);valxy=(x,y+4.8)
        if libid.startswith('Connector_'):refxy=(x+2,y-5);valxy=(x+2,y-3)
        if libid=='Connector_Generic:Conn_01x20':refxy=(x+3,y-28);valxy=(x+3,y-25.5)
        if libid in ['Device:R','Device:C'] and angle==0:refxy=(x+3.5,y-1.3);valxy=(x+3.5,y+1.3)
        if libid.startswith('RF_Module:'):refxy=(x-29,y-38);valxy=(x-29,y-35.5)
        if libid.startswith('74xx:'):refxy=(x+15,y-28);valxy=(x+15,y-25.5)
        gate_units={'74xx:74HC00':4,'74xx:74HC02':4,'74xx:74HC14':6,'Poofer:74HC32':4,'74xx:74HC74':2}
        if libid in gate_units:
            if unit<=gate_units[libid]:
                refxy=(x,y-(12 if libid=='74xx:74HC74' else 8));valxy=(x,y-(9.5 if libid=='74xx:74HC74' else 5.5))
            else:refxy=(x+9,y-2);valxy=(x+9,y+2)
        if libid.startswith('Comparator:'):refxy=(x,y-7);valxy=(x,y+7)
        if libid in ['Comparator:LM339','Amplifier_Operational:LM2902'] and unit==5:refxy=(x+16,y-2);valxy=(x+16,y+2)
        if libid=='Comparator:LM393' and unit==3:refxy=(x+16,y-2);valxy=(x+16,y+2)
        if libid.startswith('Relay:'):refxy=(x+23,y-8);valxy=(x+23,y-5.5)
        if libid.startswith('Regulator_Linear:'):refxy=(x,y-9);valxy=(x,y-6.5)
        if libid.startswith(('Transistor_FET:','Transistor_BJT:','Poofer:MJD')):refxy=(x+7.5,y-3);valxy=(x+7.5,y+3)
        if libid=='Poofer:TLV431AIDBZR':refxy=(x+6,y-2);valxy=(x+6,y+2)
        if libid=='Poofer:PCA9517AD':refxy=(x-30,y-17);valxy=(x-30,y-14.5)
        if libid=='Poofer:TLV803EA30DBZR':refxy=(x+25,y-20);valxy=(x+25,y-17.5)
        if libid.startswith('Device:D') and angle in [90,270]:refxy=(x+8,y-2);valxy=(x+8,y+2)
        ps=[]
        for name,v in properties.items():
            visible=name in ['Reference','Value'] and props
            xy=refxy if name=='Reference' else valxy if name=='Value' else (x,y)
            field_angle=angle if angle in [90,270] else 0
            left=visible and ((libid in ['Device:R','Device:C'] and angle==0) or libid.startswith(('Transistor_FET:','Poofer:MJD','Poofer:TLV431')) or (libid.startswith('Device:D') and angle in [90,270]))
            ps.append(f'(property {q(name)} {q(v)} (at {f(xy[0])} {f(xy[1])} {field_angle}) (effects (font (size 1.0 1.0))'+(' (justify left)' if left else '')+('' if visible else ' (hide yes)')+'))')
        pins={}; pinobjs=[]
        for s in find_all(symbol,'symbol'):
            m=re.search(r'_(\d+)_(\d+)$',s[1])
            if m and (int(m[1]) not in [0,unit] or int(m[2])>1):continue
            for pin in find_all(s,'pin'):
                n=find_first(pin,'number')[1];a=find_first(pin,'at');px,py,pa=map(float,a[1:4]);t=math.radians(angle)
                pins[n]=(snap(x+px*math.cos(t)-py*math.sin(t)),snap(y-px*math.sin(t)-py*math.cos(t)),(pa+angle)%360)
                self.points.add(pins[n][:2])
                pinobjs.append(f'(pin {q(n)} (uuid {q(uid(key+n))}))')
        power=libid.startswith('power:')
        self.add(f'(symbol (lib_id {q(libid)}) (at {f(x)} {f(y)} {angle}) (unit {unit}) (in_bom {"no" if power else "yes"}) (on_board {"no" if power else "yes"}) (dnp no) (uuid {q(key)}) '+''.join(ps+pinobjs)+f' (instances (project {q(PROJECT)} (path {q(self.path)} (reference {q(ref)}) (unit {unit})))))')
        if not power and unit==1:
            self.components.append({'ref':ref,'value':value,'footprint':footprint,'code':code,'notes':notes,'pins':{},'group':self.group,'channel':self.channel,'bank':self.bank,'uuid':key,'sheet':self.name})
        return pins
    def net(self,pins,n,net,length=6):
        x,y,a=pins[str(n)];t=math.radians(a);ex=round(x-length*math.cos(t),5);ey=round(y+length*math.sin(t),5)
        self.wire((x,y),(ex,ey));self.label(net,ex,ey,int(a))
    def nc(self,pins,n):
        x,y,_=pins[str(n)];self.add(f'(no_connect (at {f(x)} {f(y)}) (uuid {q(self.nextid())}))')
    def connect(self,pins,n,xy):self.wire(pins[str(n)][:2],xy)
    def resistor(self,ref,code,x,y,net1=None,net2=None,angle=0,value=None,notes=''):
        if code=='C25804':code='C17414'
        fp='Resistor_SMD:R_0805_2012Metric' if code=='C17414' else 'Resistor_SMD:R_0603_1608Metric'
        p=self.part('Device:R',ref,code,x,y,angle,value=value,footprint=fp,notes=notes)
        if net1:self.net(p,1,net1,3)
        if net2:self.net(p,2,net2,3)
        return p
    def capacitor(self,ref,code,x,y,net1,net2,value,fp='Capacitor_SMD:C_0603_1608Metric',notes=''):
        p=self.part('Device:C',ref,code,x,y,value=value,footprint=fp,notes=notes)
        self.net(p,1,net1,3);self.net(p,2,net2,3);return p
    def header(self,ref,x,y,nets,notes=''):
        count=len(nets);code={2:'C124375',3:'C124376',20:'C50981'}[count]
        p=self.part('Connector_Generic:Conn_01x'+str(count).zfill(2),ref,code,x,y,value=f'{count}P / 2.54mm',footprint=f'Connector_PinHeader_2.54mm:PinHeader_1x{count:02d}_P2.54mm_Vertical',notes=notes)
        for i,net in enumerate(nets,1):self.net(p,i,net,6)
    def child(self,child,x,y,w=88,h=25):
        self.add(f'(sheet (at {f(x)} {f(y)}) (size {f(w)} {f(h)}) (fields_autoplaced) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {q(uid(child.name+"sheet"))}) (property "Sheetname" {q(child.title)} (at {f(x)} {f(y-1)} 0) (effects (font (size 1.25 1.25)) (justify left bottom))) (property "Sheetfile" {q(child.name+".kicad_sch")} (at {f(x)} {f(y+h+1)} 0) (effects (font (size 1 1)) (justify left top))) (instances (project {q(PROJECT)} (path {q('/'+uid(PROJECT))} (page {q(child.page)})))))')
    def save(self):
        # KiCad connectivity requires explicit segment endpoints at branches.
        segments=set()
        for a,b in self.wires:
            points=[a,b]
            for p in self.points:
                if a[0]==b[0]==p[0] and min(a[1],b[1])<p[1]<max(a[1],b[1]):points.append(p)
                elif a[1]==b[1]==p[1] and min(a[0],b[0])<p[0]<max(a[0],b[0]):points.append(p)
            points=sorted(set(points))
            for v,w in zip(points,points[1:]):segments.add((v,w))
        for a,b in sorted(segments):
            self.add(f'(wire (pts (xy {f(a[0])} {f(a[1])}) (xy {f(b[0])} {f(b[1])})) (stroke (width 0) (type default)) (uuid {q(self.nextid())}))')
        data=f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "10.0") (uuid {q(self.uuid)}) (paper "A3") (title_block (title {q(self.title)}) (date "2026-10-03") (rev "A.3") (company "Universal Poofer Control | Engineering") (comment 1 "Grounded contacts / 20mA wetting / +/-100V faults") (comment 2 "Hardware stop latch | 12V / 1A NO valve outputs")) (lib_symbols '+''.join(sexp(s) for s in self.symbols.values())+') '+''.join(self.items)+' (sheet_instances (path "/" (page '+q(self.page)+'))) (embedded_fonts no))'
        (ROOT/(self.name+'.kicad_sch')).write_text(data)
