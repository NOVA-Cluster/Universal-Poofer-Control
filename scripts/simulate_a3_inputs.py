#!/usr/bin/env python3
"""Native-netlist-derived A.3 field circuit tests, with explicitly approximate models.

Run: python3 scripts/simulate_a3_inputs.py
Only reads schematic/netlist/BOM. Writes owned simulation/report outputs.
"""
from pathlib import Path
import gzip,hashlib,json,math,re,subprocess,sys
from kicad_sexp import parse_file
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'analysis';WORK=A/'revA3_input_spice';WORK.mkdir(exist_ok=True)
NET=A/'Universal_Poofer_Control.net'

def child(x,k):return next((a for a in x[1:] if isinstance(a,list) and a and a[0]==k),None)

def read_native():
 r=parse_file(str(NET));comp={child(c,'ref')[1]:c for c in child(r,'components')[1:]};pins={}
 for net in child(r,'nets')[1:]:
  name=child(net,'name')[1]
  for nod in net:
   if isinstance(nod,list) and nod and nod[0]=='node':pins[(child(nod,'ref')[1],child(nod,'pin')[1])]=name
 return comp,pins
COMP,PINS=read_native()
def pn(ref,pin):return PINS[(ref,str(pin))]
def value(ref):return child(COMP[ref],'value')[1]
def sp(n):
 if n=='GND':return '0'
 return 'n_'+re.sub('[^a-zA-Z0-9_]','_',n)
def node(ref,pin):return sp(pn(ref,pin))
def assert_connection(ref,pin,name):
 assert pn(ref,pin)==name or pn(ref,pin).endswith('/'+name),(ref,pin,pn(ref,pin),name)

def audit_native():
 checked=[]
 for ch in range(1,10):
  rb=1000+30*(ch-1);raw='ESTOP_FIELD' if ch==9 else f'IN{ch}_FIELD'
  checks={f'Q{100+ch}':{1:f'IN{ch}_WET_BASE',3:f'IN{ch}_WET_EMIT'},f'Q{110+ch}':{1:f'IN{ch}_DRV_BASE',2:'GND',3:f'IN{ch}_DRV_COL'},f'Q{120+ch}':{1:'GND',2:f'IN{ch}_UV_EMITTER',3:f'IN{ch}_UV_GATE'},f'Q{130+ch}':{1:f'IN{ch}_UV_GATE',2:'+5V_LOGIC',3:f'IN{ch}_WET_BASE'},f'R{rb}':{1:'+5V_LOGIC',2:f'IN{ch}_WET_EMIT'},f'R{rb+2}':{1:f'IN{ch}_WET_BASE',2:f'IN{ch}_DRV_COL'},f'R{rb+3}':{1:'+5V_LOGIC',2:f'IN{ch}_WET_BASE'},f'R{rb+8}':{1:'+5V_LOGIC',2:f'IN{ch}_UV_GATE'},f'R{rb+9}':{1:pn(f'R{rb+9}',1),2:f'IN{ch}_UV_SENSE'},f'R{rb+10}':{1:'+3V3',2:f'IN{ch}_UV_SENSE'},f'R{rb+11}':{1:f'IN{ch}_UV_SENSE',2:'GND'},f'R{rb+12}':{1:f'IN{ch}_UV_SENSE',2:'GND'},f'D{100+ch}':{3:raw},f'D{110+ch}':{1:raw},f'D{120+ch}':{3:raw}}
  for ref,m in checks.items():
   for pin,n in m.items():assert_connection(ref,pin,n)
  assert pn(f'Q{100+ch}',2)==pn(f'D{100+ch}',1)
  assert pn(f'R{rb+2}',2)==pn(f'Q{110+ch}',3)
  amp_ref='U20' if ch<=4 else 'U21' if ch<=8 else 'U22';amp_pin=[1,7,8,14][(ch-1)%4]
  assert {pn(f'R{rb+1}',1),pn(f'R{rb+1}',2)}=={pn(amp_ref,amp_pin),pn(f'Q{110+ch}',1)}
  # Three series resistors and correct diode direction for both HV branches.
  assert pn(f'R{rb+4}',1)==f'IN{ch}_UV_EMITTER'
  assert pn(f'R{rb+4}',2)==pn(f'R{rb+5}',1)
  assert pn(f'R{rb+5}',2)==pn(f'R{rb+6}',1)
  assert pn(f'R{rb+6}',2)==pn(f'D{120+ch}',1)
  assert pn(f'D{110+ch}',3)==pn(f'R{rb+14}',1)
  assert pn(f'R{rb+14}',2)==pn(f'R{rb+15}',1)
  assert pn(f'R{rb+15}',2)==pn(f'R{rb+16}',1)
  assert pn(f'R{rb+16}',2)==f'IN{ch}_SENSE'
  assert pn(f'R{rb+18}',2)==pn(f'R{rb+19}',1)
  assert pn(f'R{rb+18}',1)==f'IN{ch}_SENSE'
  assert pn(f'R{rb+19}',2)==('ESTOP_CLOSED_N' if ch==9 else f'IN{ch}_N')
  for k in range(21):
   expected=['33R','2.2k','1k','1k','100k','100k','100k','100k','68k','1M','1M','1M','1M','10k','100k','100k','100k','6.8k','1M','1M','10k'][k]
   if k in [9,10,11,12]:expected=value(f'R{rb+9}')
   assert value(f'R{rb+k}')==expected
  assert value(f'R{rb+9}') in ['1M','100k']
  assert pn(f'R{rb+9}',1).split('/')[-1] in [f'IN{ch}_UV_GATE',f'IN{ch}_UV_EMITTER']
  if (f'R{rb+24}','1') in PINS:
   ap=[3,5,10,12][(ch-1)%4];ef=pn(amp_ref,ap)
   assert {pn(f'R{rb+24}',1),pn(f'R{rb+24}',2)}=={f'IN{ch}_WET_EMIT',ef}
   assert {pn(f'C{140+ch}',1),pn(f'C{140+ch}',2)}=={ef,'GND'}
   assert value(f'R{rb+24}')=='10k' and value(f'C{140+ch}').startswith('100n')
  if (f'C{160+ch}','1') in PINS:
   assert {pn(f'C{160+ch}',1),pn(f'C{160+ch}',2)}=={f'IN{ch}_UV_EMITTER','GND'}
   assert value(f'C{160+ch}').startswith('1nF')
  checked.append({'channel':ch,'components_checked':[f'R{rb+k}' for k in range(21)]+[f'Q{x+ch}' for x in [100,110,120,130]]+[f'D{x+ch}' for x in [100,110,120]]})
 for ref,a,b,val in [('R50','+3V3',pn('R51',1),'200k'),('R51',pn('R50',2),'CONTACT_REF','200k'),('R52','CONTACT_REF','GND','3.3k'),('R55','+5V_LOGIC',pn('R55',2),'1k'),('R56',pn('R55',2),'GND','6.8k'),('R57',pn('R55',2),'CURRENT_REF_PAR','75k'),('R58','CURRENT_REF_PAR','GND','75k'),('R60','+3V3','UV_REF',value('R60')),('R61','UV_REF','GND','10k')]:
  assert_connection(ref,1,a);assert_connection(ref,2,b);assert value(ref)==val
 assert pn('U20',3).split('/')[-1] in ['IN1_WET_EMIT','IN1_EMIT_F'];assert_connection('U20',1,'IN1_AMP_OUT');assert_connection('U20',4,'+12V_IN');assert_connection('U20',11,'GND')
 assert_connection('U10',5,'IN1_SENSE');assert_connection('U10',4,'CONTACT_REF');assert_connection('U10',2,'IN1_N')
 assert_connection('U13',5,'UV_REF');assert_connection('U13',4,'IN1_UV_SENSE');assert_connection('U13',2,'IN1_FAULT')
 assert_connection('Q149',1,'LOCAL_MASTER_N');assert_connection('Q149',2,'GND');assert_connection('Q149',3,'IN9_DRV_BASE')
 return checked
AUDIT=audit_native()
SIM_WARNINGS=[]

RS={'30k':'30k','33k':'33k','33R':'33','2.2k':'2.2k','1k':'1k','100k':'100k','68k':'68k','1M':'1Meg','10k':'10k','100R':'100','6.8k':'6.8k','200k':'200k','3.3k':'3.3k','75k':'75k'}
V5=node('R1000',1);V33=node('R1020',1);V12=node('U20',4);FIELD=node('D101',3);E=node('Q101',3);BASE=node('Q101',1);COL=node('Q101',2);GATE=node('Q131',1);SNS=node('U10',5);UVSNS=node('U13',4);CRE=node('R1021',1) if ('R1021','1') in PINS else sp('CURRENT_REF');OUT=node('U10',2);FAULT=node('U13',2);UE=node('Q121',2);AMP=node('U20',1);DRVCOL=node('Q111',3)
CREF=node('U10',4);UREF=node('U13',5)
OBS=[FIELD,SNS,OUT,FAULT,GATE,E,BASE,COL,UE,UVSNS,CRE,AMP,V5,V33,V12,'wet_i','pnp_p','shunt_p','driver_i','amp_minus']

def deck(name,*,mode='open',field=0,rcontact=.1,v5=5.0,v33=3.3,v12=12,bf=100,uvbf=150,vto=-.9,cscale=1,temp=27,leak=0,vos=0,ibias=0,transient=None,sweep=None,compensate=False,comp_cap='10n',limiter=False,emit_only=False,amp_limit=.005):
 lines=[f'A3 field test {name}; native exported netlist topology',f'* SHA256 {hashlib.sha256(NET.read_bytes()).hexdigest()}',f'.temp {temp}',f'V5 {V5} 0 {v5}',f'V33 {V33} 0 {v33}',f'V12 {V12} 0 {v12}']
 if transient:
  for key,val in transient.get('supplies',{}).items():
   ix={'5':3,'3.3':4,'12':5}[key];lines[ix]=f'V{key.replace(".","")} '+{'5':V5,'3.3':V33,'12':V12}[key]+' 0 '+val
 if mode=='external':lines.append(f'VFIELD {FIELD} 0 '+(transient.get('field',str(field)) if transient else str(field)))
 elif mode=='contact':lines.append(f'RCONTACT {FIELD} 0 {rcontact}')
 elif mode=='switched_contact':
  lines+= [f'RCONTACT {FIELD} NC_CONTACT {rcontact}','Scontact NC_CONTACT 0 CTRL 0 CONTACT', 'VCTRL CTRL 0 PWL(0 -5 1m -5 1.001m 5 30m 5 30.001m -5 31m -5)', '.model CONTACT SW(Ron=.001 Roff=1e12 Vt=2 Vh=.1)']
 elif mode=='open_fault':
  lines+= ['VF_SOURCE NEGFAULT 0 PWL(0 0 1m 0 1.0001m -100 2m -100)', f'Sfault {FIELD} NEGFAULT CTRL 0 FAULTSW','VCTRL CTRL 0 PWL(0 -5 1m -5 1.0001m 5 2m 5)', '.model FAULTSW SW(Ron=.001 Roff=1e12 Vt=2 Vh=.1)']
 else:lines.append(f'ROPEN {FIELD} 0 1e12')
 for ref in [f'R{i}' for i in range(1000,1021)]+['R50','R51','R52','R55','R56','R57','R58','R60','R61']:
  lines.append(f'{ref} {node(ref,1)} {node(ref,2)} {RS[value(ref)]}')
 for ref in ['C101','C50','C55','C60']:lines.append(f'{ref} {node(ref,1)} {node(ref,2)} 10n')
 for ref in ['D101','D111','D121']:
  lines.append(f'{ref} {node(ref,1)} {node(ref,3)} BAS21APPROX')
  if leak and ((field<0 and ref=='D111') or (field>0 and ref in ['D101','D121'])):lines.append(f'I{ref}_LEAK {node(ref,3)} {node(ref,1)} {leak}')
 for ref,model in [('Q101','MJD350APPROX'),('Q111','NPNDRIVER'),('Q121','NPNDETECT')]:
  bp,ep,cp=(1,3,2) if ref=='Q101' else (1,2,3)
  lines.append(f'{ref} '+('PNPCOL_DEVICE' if ref=='Q101' else node(ref,cp))+f' {node(ref,bp)} {node(ref,ep)} {model}')
  if ref=='Q101':lines.append(f'VWET PNPCOL_DEVICE {COL} 0')
 lines += [f'MQ131 {node("Q131",3)} {node("Q131",1)} {node("Q131",2)} {node("Q131",2)} PMOSAPPROX',f'CGS {GATE} {V5} {590*cscale}p',f'CGD {GATE} {BASE} {55*cscale}p',f'CDS {V5} {BASE} 25p',f'DPMOSBODY {BASE} {V5} BODYAPPROX']
 PLUS=node('U20',3);MINUS=node('U20',2)
 if PLUS!=E:
  rr=[r for r in COMP if r.startswith('R') and (r,'1') in PINS and (r,'2') in PINS and {node(r,1),node(r,2)}=={E,PLUS}]
  cc=[r for r in COMP if r.startswith('C') and (r,'1') in PINS and (r,'2') in PINS and {node(r,1),node(r,2)}=={PLUS,'0'}]
  assert len(rr)==len(cc)==1 and value(rr[0])=='10k' and value(cc[0]).startswith('100n'),(rr,cc)
  lines += [f'{rr[0]} {node(rr[0],1)} {node(rr[0],2)} 10k',f'{cc[0]} {PLUS} 0 100n']
 if MINUS!=CRE:
  rr=[r for r in COMP if r.startswith('R') and (r,'1') in PINS and (r,'2') in PINS and {node(r,1),node(r,2)}=={CRE,MINUS}]
  cc=[r for r in COMP if r.startswith('C') and (r,'1') in PINS and (r,'2') in PINS and {node(r,1),node(r,2)}=={AMP,MINUS}]
  assert len(rr)==len(cc)==1,(rr,cc)
  lines += [f'{rr[0]} {node(rr[0],1)} {node(rr[0],2)} {RS[value(rr[0])]}',f'{cc[0]} {node(cc[0],1)} {node(cc[0],2)} '+('100n' if value(cc[0]).startswith('100nF') else '10n')]
 if compensate and MINUS==CRE:
  MINUS='LOCAL_AMP_MINUS'
  lines += [f'RCOMP {CRE} {MINUS} 10k',f'CCOMP {AMP} {MINUS} {comp_cap}']
 native_limits=[r for r in COMP if value(r)=='MMBT3906' and (r,'2') in PINS and pn(r,2)=='+5V_LOGIC' and pn(r,3)=='IN1_WET_BASE']
 if native_limits:
  ql=native_limits[0];ln=node(ql,1)
  rr=[r for r in COMP if r.startswith('R') and (r,'1') in PINS and (r,'2') in PINS and ln in {node(r,1),node(r,2)} and ({V5,E} & {node(r,1),node(r,2)})]
  assert len(rr)==2 and all(value(r)=='1k' for r in rr),rr
  lines += [f'{r} {node(r,1)} {node(r,2)} 1k' for r in rr]+[f'{ql} {BASE} {ln} {V5} PNPLIMITER','.model PNPLIMITER PNP(Is=1e-14 Bf=150 Br=3 Vaf=100 Cje=8p Cjc=4p Tf=.5n Tr=200n)']
 local_clamps=[r for r in COMP if r.startswith('D') and value(r)=='BAT54' and (r,'3') in PINS and pn(r,1)=='CURRENT_REF' and node(r,3)==MINUS]
 for dc in local_clamps:lines += [f'{dc} {CRE} {MINUS} SCHOTTKYAPPROX']
 if limiter and not native_limits:
  lines += [f'RLIM1 {V5} LIM_BASE 1k',f'RLIM2 LIM_BASE {E} 1k',f'QLIM {BASE} LIM_BASE {V5} PNPLIMITER','.model PNPLIMITER PNP(Is=1e-14 Bf=150 Br=3 Vaf=100 Cje=8p Cjc=4p Tf=.5n Tr=200n)']
 RAWREF=node('R55',2)
 if RAWREF!=CRE:
  assert pn('U22',5)==pn('R55',2) and pn('U22',6)==pn('U22',7)
  DRIVE=node('U22',7)
  if DRIVE!=CRE:
   r1=[r for r in COMP if r.startswith('R') and (r,'1') in PINS and (r,'2') in PINS and value(r)=='100R' and DRIVE in {node(r,1),node(r,2)}]
   assert len(r1)==1,r1
   MID=next(n for n in [node(r1[0],1),node(r1[0],2)] if n!=DRIVE)
   r2=[r for r in COMP if r.startswith('R') and (r,'1') in PINS and (r,'2') in PINS and value(r)=='100R' and {node(r,1),node(r,2)}=={MID,CRE}]
   assert len(r2)==1,r2
   cc=[r for r in COMP if r.startswith('C') and (r,'1') in PINS and (r,'2') in PINS and value(r).startswith('10uF') and {node(r,1),node(r,2)}=={CRE,'0'}]
   assert len(cc)==1,cc
   lines += [f'{r} {node(r,1)} {node(r,2)} 100' for r in r1+r2]+[f'{cc[0]} {CRE} 0 10u']
  lines += [f'BREFGM 0 REFSTATE I={{max(-.5,min(.5,7.539822*(V({RAWREF})-V({DRIVE})-V(REFSTATE)/100000)))}}','CREFSTATE REFSTATE 0 1u','BREFCLIP REFSTATE 0 I={10*(max(0,V(REFSTATE)-10.5)+min(0,V(REFSTATE)-.02))}',f'BREFOUT REFSOURCE 0 V={{V({V12}) < 3 ? 0 : max(.02,min(V({V12})-1.5,V(REFSTATE)))}}',f'BREFSTAGE REFSOURCE {DRIVE} I={{V({V12})<3 ? (V(REFSOURCE)-V({DRIVE}))/50 : max(-{amp_limit},min({amp_limit},(V(REFSOURCE)-V({DRIVE}))/50))}}',f'.nodeset V(REFSTATE)={v5*.8668} V({DRIVE})={v5*.8668} V({CRE})={v5*.8668}',f'IREFBUFFER {RAWREF} 0 {ibias}']
 uvcaps=[r for r in COMP if r.startswith('C') and (r,'1') in PINS and (r,'2') in PINS and value(r).startswith('1nF') and {node(r,1),node(r,2)}=={UE,'0'}]
 for uc in uvcaps:lines.append(f'{uc} {UE} 0 1n')
 # Finite gain / GBW / slew opamp; output/load, saturated recovery and power-off clamps approximate.
 lines += [f'BGM 0 AMPSTATE I={{max(-.5,min(.5,7.539822*(V({PLUS})-V({MINUS})+({vos})-V(AMPSTATE)/100000)))}}','CAMP AMPSTATE 0 1u',f'BAMPRESET AMPSTATE 0 I={{V({V12}) < 3 ? V(AMPSTATE) : 0}}',f'VHIGH AMPHI 0 {max(v12-1.5,.02)}','BAMPCLIP AMPSTATE 0 I={10*(max(0,V(AMPSTATE)-V(AMPHI))+min(0,V(AMPSTATE)-.02))}',f'BAMP AMPSOURCE 0 V={{V({V12}) < 3 ? 0 : max(.02,min(V({V12})-1.5,V(AMPSTATE)))}}',f'BAMPSTAGE AMPSOURCE {AMP} I={{V({V12})<3 ? (V(AMPSOURCE)-V({AMP}))/50 : max(-{amp_limit},min({amp_limit},(V(AMPSOURCE)-V({AMP}))/50))}}',f'IAMPIN {PLUS} 0 {ibias}',f'IREFINPUTS {CRE} 0 {9*ibias}']
 # Output collector current, powered by 12 V. Vol=0.12 V, finite transition band.
 lines += [f'BCONTACT {OUT} 0 I={{V({V12}) < 3 ? 0 : max(0,V({OUT})-.12)*.1*(1+tanh((V({CREF})-V({SNS}))/0.0002))/2}}',f'BUV {FAULT} 0 I={{V({V12}) < 3 ? 0 : max(0,V({FAULT})-.12)*.1*(1+tanh((V({UVSNS})-V({UREF}))/0.0002))/2}}',f'BWET wet_i 0 V={{I(VWET)}}',f'BPOWER pnp_p 0 V={{max(0,(V({E})-V({COL}))*(I(VWET)))}}',f'BSHUNT shunt_p 0 V={{(V({V5})-V({E}))^2/33}}',f'BDRIVER driver_i 0 V={{(V({BASE})-V({DRVCOL}))/1000}}',f'BMINUS amp_minus 0 V={{V({MINUS})}}']
 lines += [f'.model MJD350APPROX PNP(Is=1e-14 Bf={bf} Br=2 Vaf=150 Ikf=.5 Cje=60p Cjc=20p Tf=30n Tr=1u)', '.model NPNDRIVER NPN(Is=1e-14 Bf=150 Br=3 Vaf=100 Cje=8p Cjc=4p Tf=.5n Tr=200n)', f'.model NPNDETECT NPN(Is=1e-14 Bf={uvbf} Br=3 Vaf=100 Cje=8p Cjc=4p Tf=.5n Tr=200n)',f'.model PMOSAPPROX PMOS(Level=1 Vto={vto} Kp=5 Lambda=.01)', '.model BAS21APPROX D(Is=1e-10 N=1.6 Rs=2 Bv=250 Ibv=1u Cjo=5p Tt=20n)', '.model BODYAPPROX D(Is=1e-10 N=1.3 Rs=.1)', '.model SCHOTTKYAPPROX D(Is=1e-8 N=1.1 Rs=2 Cjo=10p Bv=30 Ibv=1u Eg=.69 Xti=2)', '.model AMPLIMIT D(Is=1e-5 N=.05 Rs=.01 Eg=0 Xti=0)', f'.nodeset V({E})={v5*.8668} V({BASE})={max(0,v5*.8668-.7)} V({GATE})={v5*.96} V(AMPSTATE)=.7 V({SNS})=.0004 V({OUT})=.12', '.options reltol=1e-4 abstol=1p vntol=1n itl1=1000 itl2=1000 method=gear', '.control','set wr_vecnames','set wr_singlescale']
 dynamic=bool(transient or mode in ['switched_contact','open_fault'])
 if not dynamic:
  removed=('BGM ','CAMP ','BAMPRESET ','VHIGH ','BAMPCLIP ','BREFGM ','CREFSTATE ','BREFCLIP ','.nodeset ')
  filtered=[]
  for line in lines:
   if line.startswith(removed):continue
   if line.startswith('BAMP '):line=f'BAMP AMPSOURCE 0 V={{V({V12}) < 3 ? 0 : max(.02,min(V({V12})-1.5,.7+100*(V({PLUS})-V({MINUS})+({vos}))))}}'
   if line.startswith('BREFOUT '):line=f'BREFOUT REFSOURCE 0 V={{V({V12}) < 3 ? 0 : max(.02,min(V({V12})-1.5,V({RAWREF})))}}'
   filtered.append(line)
  lines=filtered
  at=lines.index('.control')
  lines.insert(at,f'.nodeset V({E})={v5*.8668} V({BASE})={max(0,v5*.8668-.7)} V({GATE})={v5} V({AMP})=.7 V({CRE})={v5*.8668} V({MINUS})={v5*.8668}')
  if RAWREF!=CRE:lines.insert(at,f'.nodeset V({DRIVE})={v5*.8668}')
 else:
  init5=v5;init12=v12
  for key,stim in (transient or {}).get('supplies',{}).items():
   match=re.match(r'PWL\(0\s+([\d.]+)',stim)
   if match:
    if key=='5':init5=float(match[1])
    if key=='12':init12=float(match[1])
  initial_ref=init5*.8667573 if init12>=3 else 0
  initial_amp=min(init12-1.5,10.5) if init12>=3 and init5>0 else 0
  ic=f'.ic V({PLUS})={initial_ref+.5 if initial_amp>0 else 0} V({CRE})={initial_ref} V({MINUS})={initial_ref} V(AMPSTATE)={initial_amp}'
  if RAWREF!=CRE:ic+=f' V(REFSTATE)={initial_ref} V({DRIVE})={initial_ref}'
  at=lines.index('.control');lines.insert(at,ic)
 if sweep:lines.append(f'dc VFIELD {sweep[0]} {sweep[1]} {sweep[2]}')
 elif transient:lines.append('tran '+transient.get('step','100n')+' '+transient.get('stop','2m')+' 0 '+transient.get('maxstep','100n'))
 elif mode=='switched_contact':lines.append('tran 1u 31m 0 1u')
 elif mode=='open_fault':lines.append('tran 50n 2m 0 50n')
 else:lines.append('op')
 lines += [f'wrdata {name}.dat '+' '.join('v('+n+')' for n in OBS),'quit','.endc','.end']
 p=WORK/(name+'.cir');p.write_text('\n'.join(lines)+'\n')
 if emit_only:return []
 proc=subprocess.run(['ngspice','-b',str(p)],text=True,capture_output=True,timeout=30,cwd=WORK)
 log=proc.stdout+'\n'+proc.stderr;(WORK/(name+'.log')).write_text(log)
 if proc.returncode or 'Error:' in log or 'no such' in log.lower():raise RuntimeError(name+' '+log[-2500:])
 rows=[]
 if 'simulation(s) aborted' in log or 'Timestep too small' in log:SIM_WARNINGS.append({'case':name,'status':'partial_transient','note':'ngspice stopped at a nonlinear transition; use only completed time windows. Stored-trace end must be checked.'})
 raw_data=(WORK/(name+'.dat')).read_bytes()
 for line in raw_data.decode().splitlines()[1:]:
  nums=list(map(float,line.split()));rows.append({'scale':nums[0],**dict(zip(OBS,nums[1:]))})
 (WORK/(name+'.dat.gz')).write_bytes(gzip.compress(raw_data))
 (WORK/(name+'.dat')).unlink()
 return rows

def metrics(row):return {'field_v':row[FIELD],'sense_v':row[SNS],'contact_n_v':row[OUT],'fault_v':row[FAULT],'uv_gate_v':row[GATE],'emitter_v':row[E],'base_v':row[BASE],'uv_emitter_v':row[UE],'uv_sense_v':row[UVSNS],'ref_v':row[CRE],'amp_out_v':row[AMP],'wetting_ma':row['wet_i']*1000,'pnp_power_w':row['pnp_p'],'r33_power_w':row['shunt_p'],'driver_current_ma':row['driver_i']*1000,'local_reference_v':row['amp_minus']}

def main():
 report={'revision':'A.3','netlist_sha256':hashlib.sha256(NET.read_bytes()).hexdigest(),'native_components':len(COMP),'native_features':{'emitter_sense_filter':pn('U20',3).split('/')[-1]=='IN1_EMIT_F','UV_emitter_1nF_guard':('C161','1') in PINS,'UV_emitter_monitoring':pn('R1009',1).split('/')[-1]=='IN1_UV_EMITTER','local_compensation':pn('U20',2)!='CURRENT_REF','reference_buffer':pn('R55',2)!='CURRENT_REF','backup_limiter':bool([r for r in COMP if value(r)=='MMBT3906' and (r,'2') in PINS and pn(r,2)=='+5V_LOGIC' and pn(r,3)=='IN1_WET_BASE'])},'netlist_connectivity_checks':AUDIT,'model_basis':{'passives':'Native netlist, actual values; exact ideal resistor/capacitor analysis.','opamp':'DCuses centered gain100andidealreferencefollower for numericalconvergence; dynamicusesapproximatelegacy LM2902: Aol100k, GBW1.2MHz, slew0.5V/us,50ohm output, rail clipping. Not manufacturer transistor macro-model; no guaranteed recovery or power-off input clamp model.','semiconductors':'Generic Gummel-Poon MJD350/MMBT3904; generic level-1 AO3401. Datasheet-typical645pF gate capacitance, parameter variations illustrative only. BAS21 generic diode; separate leakage injection tests.','comparator':'Behavioral open collector,120mVnominalLOW,200uV transition band. No propagation-time guarantee.','limits':'Simulation is nominal/illustrative evidence; temperature changes generic models and does not establish manufacturer corner behavior.'},'dc':{},'negative_sweep':{},'transients':{},'power_sequences':{},'qualification':[]}
 for name,kwargs in [('open',{}),('closed_0p1ohm',{'mode':'contact','rcontact':.1}),('closed_10ohm',{'mode':'contact','rcontact':10}),('plus100',{'mode':'external','field':100}),('minus100',{'mode':'external','field':-100})]:report['dc'][name]=metrics(deck(name,**kwargs)[0])
 for tag,kwargs in [('nominal',{}),('low_gain',{'uvbf':10,'vto':-1.3}),('cold_low_gain',{'uvbf':10,'vto':-1.3,'temp':-40}),('hot',{'temp':85})]:
  rows=deck('negative_'+tag,mode='external',sweep=(0,-100,-.1),**kwargs)
  peak=max(rows,key=lambda x:x['pnp_p']);quench=next((r for r in rows if r['wet_i']<.001),None)
  report['negative_sweep'][tag]={'peak_power_point':metrics(peak),'first_under_1ma_field_v':quench[FIELD] if quench else None,'minus100':metrics(rows[-1])}
 for tag,kwargs in [('nominal',{}),('slow_detector_cap5',{'uvbf':10,'vto':-1.3,'cscale':5,'temp':-40}),('high_pnp_gain',{'bf':240,'uvbf':10,'vto':-1.3,'cscale':5})]:
  rows=deck('fault_'+tag,mode='open_fault',**kwargs);f=[r for r in rows if r['scale']>=.0010001];off=next((r for r in f if abs(r['wet_i'])<.001),None)
  peak=max(f,key=lambda x:x['pnp_p']);energy=sum((b['scale']-a['scale'])*(a['pnp_p']+b['pnp_p'])/2 for a,b in zip(f,f[1:]))
  report['transients']['open_to_minus100_'+tag]={'time_to_under_1ma_us':(off['scale']-.001)*1e6 if off else None,'peak_pnp_power_w':peak['pnp_p'],'peak_wetting_ma':max(r['wet_i'] for r in f)*1000,'peak_r33_power_w':max(r['shunt_p'] for r in f),'pnp_energy_j':energy,'final':metrics(f[-1])}
 rows=deck('contacts',mode='switched_contact');report['transients']['contact_open_close_open']={str(t):metrics(min(rows,key=lambda r:abs(r['scale']-t))) for t in [.0009,.0299,.0309] if t<=rows[-1]['scale']}
 # Independent rail-loss scenarios expose biased input common modes; 12V-powered models are inactive at zero.
 for rails in [('all_off',0,0,0),('logic_off_12_on',0,0,12),('12_off_logic_on',5,3.3,0),('3v3_off',5,0,12),('5_off',0,3.3,12)]:
  name,v5,v33,v12=rails
  for field in [-100,100]:
   report['power_sequences'][name+('_neg' if field<0 else '_pos')]=metrics(deck(name+str(field).replace('-','m'),mode='external',field=field,v5=v5,v33=v33,v12=v12)[0])
 # Explicit10uA hot leakage envelope applies to reverse-biased BAS21s, independent of generic model.
 for field in [-100,100]:
  report['power_sequences']['all_off_leak10u_'+str(field)]=metrics(deck('leak_'+str(field).replace('-','m'),mode='external',field=field,v5=0,v33=0,v12=0,leak=10e-6,temp=27)[0])
 for name,supplies in [('12_last',{'12':'PWL(0 0 1m 0 2m 12 4m 12)'}),('logic_last',{'5':'PWL(0 0 1m 0 2m 5 4m 5)','3.3':'PWL(0 0 1m 0 2m 3.3 4m 3.3)'})]:
  for f in [-100,100]:
   rows=deck('startup_'+name+str(f).replace('-','m'),mode='external',field=f,transient={'supplies':supplies,'stop':'4m','maxstep':'1u','step':'1u'})
   report['power_sequences']['startup_'+name+'_'+str(f)]={'peak_pnp_power_w':max(r['pnp_p'] for r in rows),'minimum_sense_v':min(r[SNS] for r in rows),'minimum_uv_sense_v':min(r[UVSNS] for r in rows),'minimum_local_reference_v':min(r['amp_minus'] for r in rows),'peak_wetting_ma':max(r['wet_i'] for r in rows)*1000,'final':metrics(rows[-1])}
 contact_rows=deck('contacts_full',mode='switched_contact')
 steady=[x['wet_i'] for x in contact_rows if .025<x['scale']<.029]
 report['loop_stability']={'actual_topology_nominal':{'steady_window_s':[.025,.029],'wetting_min_ma':min(steady)*1000,'wetting_max_ma':max(steady)*1000,'status':'warn_model_oscillation_or_recovery' if max(steady)-min(steady)>.002 else 'nominal_model_settled'},'compensation_candidate':{'not_in_audited_netlist':not report['native_features']['local_compensation'],'connection':'Per channel: CURRENT_REF ->10k-> local LM2902 IN−;100nF from local AMP_OUT to that IN−. Keep IN+ on emitter.','shared_reference_coupling':'The representative channel model includes native shared reference divider but does not model all nine opamps dynamically; full-channel and bench qualification remain.'},'candidate_runs':{}}
 for tag,kw in [('nominal',{}),('cold_beta30',{'temp':-40,'bf':30}),('beta240',{'bf':240})]:
  rr=deck('final_compensated_'+tag,mode='switched_contact',compensate=True,comp_cap='100n',**kw)
  ss=[x['wet_i'] for x in rr if .025<x['scale']<.029]
  report['loop_stability']['candidate_runs'][tag]={'wetting_min_ma':min(ss)*1000,'wetting_max_ma':max(ss)*1000,'status':'settled_or_still_settling_illustrative_model','peak_after_1us_ma':max(x['wet_i'] for x in rr if .001002<x['scale']<.03)*1000}
 report['backup_limiter_candidate']={'connection':'MMBT3906 E=5V, C=main PNP BASE; base midpoint of two1k resistors from5V to main PNP EMITTER; includes1k-divider bypass contribution.','illustrative_cases':{},'implemented_in_netlist':report['native_features']['backup_limiter']}
 for t in [-40,27,85]:
  for b in [30,100,240]:
   tag=f'limiter_{t}_{b}'.replace('-','m')
   d=metrics(deck(tag+'_dc',mode='contact',compensate=True,limiter=True,temp=t,bf=b)[0])
   rr=deck(tag+'_contact',mode='switched_contact',compensate=True,limiter=True,temp=t,bf=b)
   ss=[x['wet_i'] for x in rr if .025<x['scale']<.029]
   report['backup_limiter_candidate']['illustrative_cases'][tag]={'dc_wetting_ma':d['wetting_ma'],'late_min_ma':min(ss)*1000,'late_max_ma':max(ss)*1000,'peak_after_first_1us_ma':max(x['wet_i'] for x in rr if .001002<x['scale']<.03)*1000}
 for tag,kw in [('nominal',{}),('cold_slow',{'temp':-40,'uvbf':10,'vto':-1.3,'cscale':5}),('high_gain',{'bf':240,'uvbf':10,'vto':-1.3,'cscale':5})]:
  rr=deck('limited_fault_'+tag,mode='open_fault',compensate=True,limiter=True,**kw);ff=[x for x in rr if x['scale']>=.0010001];off=next((x for x in ff if x['wet_i']<.001),None)
  report['backup_limiter_candidate']['illustrative_cases']['negative_fault_'+tag]={'time_to_under1ma_us':(off['scale']-.001)*1e6 if off else None,'peak_current_ma':max(x['wet_i'] for x in ff)*1000,'peak_pnp_power_w':max(x['pnp_p'] for x in ff),'peak_r33_power_w':max(x['shunt_p'] for x in ff)}
 report['qualification']=['Original direct-emitter loop had inadequate illustrativephase margin. Finalnative10k/100n emitter filter plus localcompensation settles in nonlinearandindependentAC tests. Physicalstability/corners remainqualification.','UV transistor gain at sub-mA current/cold temperature and AO3401 capacitance have no guaranteed matching corner, so the simulated quench times are not formal worst-case bounds.','Hot powered-off leakage and logic-rail backpower must be measured with rails discharged and floating; ideal supply sources clamp rails in these tests.','Only 12V-on comparator cases have valid input common-mode operation; logic-powered/12V-off positive faults exceed comparator supply common mode even if below absolute input voltage.','Compare actual MJD350 SOA against prototype peak current/time and qualify short R33 overload; no routing thermal validation exists.','Expansion role clamp and multi-board open NC-loop voltage must be checked with all receivers and independent module supplies.']
 report['simulation_warnings']=SIM_WARNINGS
 (A/'revA3_input_simulation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['dc','negative_sweep','transients','power_sequences']},indent=2))

if __name__=='__main__':main()
