#!/usr/bin/env python3
"""Native A.3 schematic, grouped by function with durable engineering metadata."""
from schematic_lib import *
SO14='Package_SO:SOIC-14_3.9x8.7mm_P1.27mm';SO16='Package_SO:SOIC-16_3.9x9.9mm_P1.27mm';SOT='Package_TO_SOT_SMD:SOT-23'
RM={'C23140':'C17634','C21190':'C17513','C4190':'C17520','C23162':'C17673','C25803':'C149504','C25811':'C17539','C22978':'C26010','C23212':'C17772','C23242':'C17819','C23231':'C17801','C22935':'C17514','C22775':'C17408'}
CM={'C14663':'C49678','C57112':'C1710','C1588':'C51210','C15849':'C28323'}
root=Sheet(PROJECT,'01 | System architecture');root.page='1';sheets=[root]
def new(name,title,group):
 s=Sheet(name,title,'/'+root.uuid+'/'+uid(name+'sheet'));s.page=str(len(sheets)+1);s.group=group;sheets.append(s)
 s.text('UNIVERSAL POOFER CONTROL  |  '+title,15,16,1.7);s.text('REV A.3  |  Dry contacts  |  Latched hardware stop  |  Buffered expansion',15,25,1.05);return s
def P(s,lib,ref,code,x,y,**kw):return s.part(lib,ref,code,x,y,**kw)
def N(s,p,n,net,l=3.81):s.net(p,n,net,l)
def R(s,ref,code,x,y,a=None,b=None,val='',ang=0,note=''):
 code=RM.get(code,code);p=P(s,'Device:R',ref,code,x,y,angle=ang,value=val,footprint='Resistor_SMD:R_0805_2012Metric',notes=note)
 if a:N(s,p,1,a)
 if b:N(s,p,2,b)
 return p
def C(s,ref,x,y,a,b,val='100nF',code='C14663',fp='Capacitor_SMD:C_0805_2012Metric'):return s.capacitor(ref,CM.get(code,code),x,y,a,b,val,fp.replace('C_0603_1608Metric','C_0805_2012Metric'))
def IC(s,lib,ref,code,x,y,unit=1,note='',fp=SO14,val=None):return P(s,lib,ref,code,x,y,unit=unit,value=val or PARTS.get(code,{}).get('mpn',lib.split(':')[1]),footprint=fp,notes=note)
def powerunit(s,lib,ref,code,unit,x,y,rail='+3V3',note='',fp=SO14):
 p=IC(s,lib,ref,code,x,y,unit,note,fp=fp)
 for u in find_all(get_symbol(lib),'symbol'):
  m=re.search(r'_(\d+)_(\d+)$',u[1])
  if not m or int(m[1])!=unit or int(m[2])>1:continue
  for a in find_all(u,'pin'):N(s,p,find_first(a,'number')[1],'GND' if find_first(a,'name')[1] in ['GND','V-'] else rail)
 return p
def gate(s,lib,ref,code,unit,x,y,ins,out,note=''):
 p=IC(s,lib,ref,code,x,y,unit,note);ii=[];oo=[]
 for u in find_all(get_symbol(lib),'symbol'):
  m=re.search(r'_(\d+)_(\d+)$',u[1])
  if not m or int(m[1])!=unit or int(m[2])>1:continue
  for a in find_all(u,'pin'):
   if a[1]=='input':ii.append(find_first(a,'number')[1])
   elif a[1]=='output':oo.append(find_first(a,'number')[1])
 for n,v in zip(ii,ins):N(s,p,n,v)
 for n in oo:
  if out:N(s,p,n,out)
  else:s.nc(p,n)
 return p
cp=[(4,5,2),(6,7,1),(10,11,13),(8,9,14)];op=[(2,3,1),(6,5,7),(9,10,8),(13,12,14)]
CN='LM2901BIDR quad;12 V raw,3.3V open-collector status;unit properties identical.'
ON='LM2902DR quad current servo;12 V raw supply;emitter+ CURRENT_REF-;unit properties identical.'
ctrl=new('Controller','02 | Processor and service interfaces','controller');pw=new('Power','03 | Power and analog references','power');sr=new('Serial_IO','04 | Register chains','serial_io');ex=new('Expansion','05 | Buffered expansion interface','daisy_chain');st=new('Hardware_Stop','06 | Hardware stop latch and coil gate','emergency_stop')
rx=[new('Input_Receivers_'+str(i+1),f'{len(sheets)+1:02d} | Contact receivers {2*i+1}-{2*i+2}','input') for i in range(4)]
src=[new('Contact_Sources_'+str(i+1),f'{len(sheets)+1:02d} | Wetting sources {2*i+1}-{2*i+2}','input') for i in range(4)]
ef=new('Stop_Field',f'{len(sheets)+1:02d} | NC emergency-stop field loop','emergency_stop');rp=[new('Relay_Outputs_'+str(i+1),f'{len(sheets)+1:02d} | Valve outputs {4*i+1}-{4*i+4}','relay') for i in range(2)]

root.text('UNIVERSAL POOFER CONTROL',15,16,2.2);root.text('REV A.3  |  Functional architecture  |  2026-10-03',15,26,1.3)
root.block('INTERFACE CONTRACT',15,39,188,47);root.block('HARDWARE SAFETY CONTRACT',217,39,188,47)
for i,t in enumerate(['8 grounded contacts; nominal 20 mA supplied by board.','Continuous +/-100V field faults; negative faults masked.','8 NO valve outputs:12 VDC, 1 A design load per channel.','Buffered host/expander chain; separate module power.','Physical role jumper; no MCU control of role/source.']):root.text(t,20,52+6*i,1.05)
for i,t in enumerate(['NC loop open/disconnected sets hardware stop latch.','Loop restored does not re-energize retained outputs.','Fresh ARM edge and power-good required to enable.','GPIO18 = loop healthy; GPIO21 = hardware RUN feedback.','NC relay contacts auxiliary; valve connectors are NO.']):root.text(t,222,52+6*i,1.05)

ctrl.block('ESP32-S3 / RESET',15,38,187,202,'WROOM-1-N8 | 8MB flash | no PSRAM');ctrl.block('PROGRAMMING',217,38,188,84);ctrl.block('GPIO BREAKOUTS',217,134,188,106,'Module pin order; interface functions named')
gpio={'1':'GND','2':'+3V3','3':'ESP_EN','27':'BOOT_GPIO0','36':'UART_RX_GPIO44','37':'UART_TX_GPIO43','10':'ESTOP_SAFE_MON_GPIO18','23':'HW_RUN_MON_GPIO21','38':'ROLE_GPIO2_MON','4':'MCU_MOSI_GPIO4','5':'SPI_MISO_GPIO5','6':'MCU_CLK_GPIO6','7':'MCU_LATCH_GPIO7','8':'MCU_INHIBIT_N_GPIO15','9':'MCU_CLR_N_GPIO16','11':'MCU_LOAD_N_GPIO17','12':'I2C_SDA_GPIO8','17':'I2C_SCL_GPIO9'}
for u in find_all(get_symbol('RF_Module:ESP32-S3-WROOM-1'),'symbol'):
 for p in find_all(u,'pin'):
  n=find_first(p,'number')[1];name=find_first(p,'name')[1]
  if n not in gpio:gpio[n]='GND' if name=='GND' else {'USB_D-':'USB_DM_GPIO19','USB_D+':'USB_DP_GPIO20'}.get(name,name.replace('IO','GPIO'))
m=P(ctrl,'RF_Module:ESP32-S3-WROOM-1','U1','C2913198',83.82,132.08,footprint='RF_Module:ESP32-S3-WROOM-1',notes='GPIO2rolemonitoronly;18SAFE;21RUN. Antenna keepout mandatory.');seen=set()
for n,v in gpio.items():
 if m[n][:2] not in seen:N(ctrl,m,n,v,5.08);seen.add(m[n][:2])
ctrl.header('J3',280.67,191.77,[gpio[str(i)] for i in range(1,21)]);ctrl.header('J4',374.65,191.77,[gpio[str(i)] for i in range(21,41)])
ctrl.header('J6',276.86,76.2,['ESP_EN','GND','BOOT_GPIO0'],'Reset1-2;BOOT3-2 heldduringresetforROMdownload.');ctrl.header('J7',374.65,76.2,['UART_TX_GPIO43','UART_RX_GPIO44','GND'],'3.3VUART,self-poweredboard.')
C(ctrl,'C4',137,83,'+3V3','GND','10uF / 25V','C15850','Capacitor_SMD:C_0805_2012Metric');C(ctrl,'C5',172,83,'+3V3','GND');R(ctrl,'R2','C17414',48,210,'+3V3','ESP_EN','10k');C(ctrl,'C6',79,210,'ESP_EN','GND','1uF / 50V','C15849');R(ctrl,'R3','C17414',143,210,'+3V3','BOOT_GPIO0','10k')
R(ctrl,'R4','C17414',266,111,'SAFE_PERMIT','ESTOP_SAFE_MON_GPIO18','10k',90,note='MCU/header cannot back-drivehardware safety permission.')
R(ctrl,'R5','C17414',367,111,'HW_RUN_LATCH','HW_RUN_MON_GPIO21','10k',90,note='MCU/header cannot back-drivehardware stop latch.')
C(ctrl,'C10',284,113,'ESTOP_SAFE_MON_GPIO18','GND','1nF / 50V','C1588');C(ctrl,'C11',385,113,'HW_RUN_MON_GPIO21','GND','1nF / 50V','C1588')
ctrl.text('GPIO0/3/45/46 arestraps. NativeUSB pins exposed;useprotected short-wireadapter.',15,250,1.0)

pw.block('POWER INPUTS / 3.3V',15,38,188,126,'5.0-5.25V>=1A;12V>=0.5A; independent modules');pw.block('SUPERVISED STARTUP',217,38,188,126,'3.08Vthreshold;130-270msresetdelay');pw.block('SHARED REFERENCES',15,175,390,65)
pw.header('J1',58,71,['+5V_LOGIC','GND'],'5.0-5.25Vregulated,>=1A.');pw.header('J2',58,128,['+12V_IN','GND'],'12 V raw,>=0.5A;externalvalvefeedsseparate.')
p=P(pw,'Regulator_Linear:AMS1117-3.3','U2','C15578',119,71,value='TLV1117LV33',footprint='Package_TO_SOT_SMD:SOT-223-3_TabPin2',notes='Ceramicstable;0.85W at500mA needsPCB copperheatspread.')
for n,v in [(3,'+5V_LOGIC'),(2,'+3V3'),(1,'GND')]:N(pw,p,n,v)
for ref,x,v in [('C1',85,'+5V_LOGIC'),('C2',133,'+3V3'),('C3',174,'+3V3')]:C(pw,ref,x,116,v,'GND','10uF / 25V','C15850','Capacitor_SMD:C_0805_2012Metric')
for i,v in enumerate(['+5V_LOGIC','+12V_IN','GND']):p=P(pw,'power:PWR_FLAG',f'#FLG0{i+1}',None,79+i*37,150,props=False);N(pw,p,1,v,2.54)
p=P(pw,'Poofer:TLV803EA30DBZR','U40','C5218924',274,85,value='TLV803EA30',footprint=SOT,notes='1GND2RESET_N3VDD;3.08Vthreshold,130-270ms delay.')
for n,v in [(3,'+3V3'),(1,'GND'),(2,'PG_RESET_N')]:N(pw,p,n,v)
R(pw,'R40','C4190',351,76,'+3V3','PG_RESET_N','2.2k');C(pw,'C40',351,126,'+3V3','GND');R(pw,'R65','C21190',389,126,'+5V_LOGIC','GND','1k')
for base,x,codes,vals,bval,bcode,rail,net in [(50,52,['C25811','C25811'],['200k','200k'],'3.3k','C22978','+3V3','CONTACT_REF'),(55,176,['C21190'],['1k'],'6.8k','C23212','+5V_LOGIC','CURRENT_REF_RAW'),(60,307,['C17621'],['30k'],'10k','C17414','+3V3','UV_REF')]:
 prev=None
 for k,(code,val) in enumerate(zip(codes,vals)):
  a=R(pw,f'R{base+k}',code,x,196+k*13,val=val)
  if not prev:N(pw,a,1,rail,2.54)
  else:pw.wire(prev['2'][:2],a['1'][:2])
  prev=a
 b=R(pw,f'R{base+len(codes)}',bcode,x+30,223,val=bval);mid=(x,prev['2'][1]+3.81);pw.wire(prev['2'][:2],mid);pw.wire(mid,(x+30,mid[1]));pw.wire((x+30,mid[1]),b['1'][:2]);pw.label(net,x+15,mid[1],180);N(pw,b,2,'GND',2.54);C(pw,f'C{base}',x+(91 if base==55 else 61),223,net,'GND','10nF / 50V','C57112')
R(pw,'R57','C23242',237,210,'CURRENT_REF_RAW','CURRENT_REF_PAR','75k')
R(pw,'R58','C23242',237,234,'CURRENT_REF_PAR','GND','75k')
pw.text('CURRENT_REF=5V x (6.8k||150k)/(1k+(6.8k||150k)); collector target~20mA.',15,248,1.0)


sr.block('595 RELAY COMMAND LATCH',15,38,181,199,'QA=valve1; latch commits afterfullshift');sr.block('CONTACT / FAULT CAPTURE',210,38,195,199,'16bits/module:FAULTthenCONTACTS_N')
p=IC(sr,'74xx:74HC595','U3','C5947',99,122,fp=SO16)
for n,v in {14:'BUS_SER_IN',11:'BUS_CLK',12:'BUS_LATCH',13:'RLY_OE_ACTUAL_N',10:'BUS_CLR_N',16:'+3V3',8:'GND',9:'LOCAL_SER_OUT'}.items():N(sr,p,n,v)
for n,ch in [(15,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8)]:N(sr,p,n,f'RLY{ch}_CMD')
a=IC(sr,'74xx:74HC165','U4','C5613',274,105,fp=SO16);b=IC(sr,'74xx:74HC165','U5','C5613',361,177,fp=SO16)
for p in [a,b]:
 for n,v in [(16,'+3V3'),(8,'GND'),(1,'BUS_LOAD_N'),(2,'BUS_CLK'),(15,'GND')]:N(sr,p,n,v)
 sr.nc(p,7)
for n,ch in [(11,1),(12,2),(13,3),(14,4),(3,5),(4,6),(5,7),(6,8)]:N(sr,a,n,f'IN{ch}_N');N(sr,b,n,f'IN{ch}_FAULT')
N(sr,a,10,'NEXT_SERIAL_IN');N(sr,b,9,'SPI_MISO_GPIO5');sr.wire(a['9'][:2],(310,a['9'][1]));sr.wire((310,a['9'][1]),(310,b['10'][1]));sr.wire((310,b['10'][1]),b['10'][:2])
for ref,x,y in [('C7',42,203),('C8',239,215),('C9',394,215)]:C(sr,ref,x,y,'+3V3','GND')
sr.text('SampleQ7beforeclock. TailpulledHIGH fillsabsentmoduleswithFAULTFF,notfalseclosures.',15,252,1.0)

ex.block('PHYSICAL MASTER / EXPANDER ROLE',15,38,390,41,'GPIO2 monitors through100k; cannot override hardware jumper')
ex.header('JP1',65,64,['LOCAL_MASTER_N','GND'],'Closed=master;open=expander. Exactlyonehost.')
R(ex,'R70','C17414',116,62,'+3V3','LOCAL_MASTER_N','10k');R(ex,'R71','C25803',191,62,'LOCAL_MASTER_N','ROLE_GPIO2_MON','100k',90)
ex.block('UP / DOWN PORTS',15,89,121,153,'2x8male,2.54mm; independentmodulepower');ex.block('ISOLATED LOCAL / UP DRIVERS',145,89,260,83);ex.block('REGENERATED CHAIN OUTPUTS',145,182,260,60)
up=['GND','GND','UP_CLK','UP_SER','UP_RETURN','UP_LATCH','UP_ARM_N','UP_CLR_N','UP_LOAD_N','GND','ESTOP_FIELD','GND','GND','GND','I2C_SDA_BUS','I2C_SCL_BUS'];down=['GND','GND','DOWN_CLK','DOWN_SER','DOWN_RETURN','DOWN_LATCH','DOWN_ARM_N','DOWN_CLR_N','DOWN_LOAD_N','GND','ESTOP_CHAIN_OUT','GND','GND','GND','I2C_SDA_BUS','I2C_SCL_BUS']
for ref,x,y,nets in [('J20',56,138,up),('J21',113,202,down)]:
 p=P(ex,'Connector_Generic:Conn_02x08_Odd_Even',ref,'C68234',x,y,value='EXP_UP' if ref=='J20' else 'EXP_DOWN',footprint='Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical',notes='NOPOWERPINS;independentlocalsupplies. Pin11NCcontinuity,terminateonlylast.')
 for n,v in enumerate(nets,1):N(ex,p,n,v)
mp=[(2,18),(4,16),(6,14),(8,12),(17,3),(15,5),(13,7),(11,9)];dst=['BUS_CLK','BUS_SER_IN','BUS_LATCH','BUS_LOAD_N','BUS_CLR_N','BUS_ARM_N',None,None]
li=['MCU_CLK_GPIO6','MCU_MOSI_GPIO4','MCU_LATCH_GPIO7','MCU_LOAD_N_GPIO17','MCU_CLR_N_GPIO16','MCU_INHIBIT_N_GPIO15','GND','GND'];ri=['UP_CLK','UP_SER','UP_LATCH','UP_LOAD_N','UP_CLR_N','UP_ARM_N','GND','GND'];BN='LVC244A3.3V,Ioff,5Vtolerantinputs;unusedinputsGND.'
for ref,x,inputs,en in [('U50',206,li,'LOCAL_MASTER_N'),('U51',330,ri,'ROLE_RX_OE_N')]:
 p=IC(ex,'74xx:74HC244',ref,'C507250',x,135,note=BN,fp='Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm',val='SN74LVC244A')
 for n,v in [(1,en),(19,en),(10,'GND'),(20,'+3V3')]:N(ex,p,n,v)
 for (i,o),a,b in zip(mp,inputs,dst):
  N(ex,p,i,a)
  if b:N(ex,p,o,b)
  else:ex.nc(p,o)
p=IC(ex,'74xx:74HC244','U52','C507250',264,211,note=BN,fp='Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm',val='SN74LVC244A')
for n,v in [(1,'GND'),(19,'GND'),(10,'GND'),(20,'+3V3')]:N(ex,p,n,v)
for k,((i,o),a,b) in enumerate(zip(mp,['BUS_CLK','LOCAL_SER_OUT','BUS_LATCH','BUS_LOAD_N','BUS_CLR_N','RLY_OE_ACTUAL_N','SPI_MISO_GPIO5','DOWN_RETURN'],['DOWN_CLK','DOWN_SER','DOWN_LATCH','DOWN_LOAD_N','DOWN_CLR_N','DOWN_ARM_N','UP_RETURN','NEXT_SERIAL_IN'])):
 N(ex,p,i,a)
 if b:N(ex,p,o,f'CHAIN_TX_{k}');R(ex,f'R{80+k}','C23140',375,192+k*6.35,f'CHAIN_TX_{k}',b,'33R',90)
 else:ex.nc(p,o)




def nn(ch):return ('ESTOP_FIELD' if ch==9 else f'IN{ch}_FIELD','ESTOP_CLOSED_N' if ch==9 else f'IN{ch}_N','ESTOP_UV_FAULT' if ch==9 else f'IN{ch}_FAULT')
def source(s,ch,x=0):
 s.channel=ch;s.bank=(ch-1)//4+1;raw,dig,flt=nn(ch);rb=1000+(ch-1)*30;E=f'IN{ch}_WET_EMIT';B=f'IN{ch}_WET_BASE';DB=f'IN{ch}_DRV_BASE';DC=f'IN{ch}_DRV_COL';G=f'IN{ch}_UV_GATE';UE=f'IN{ch}_UV_EMITTER'
 s.block(f'INPUT {ch} | PRECISION WETTING SOURCE',15+x,38,185,119,'Nominal 20 mA; compensated servo and backup limiter');s.block('AUTONOMOUS NEGATIVE-FAULT CLAMP',15+x,160,185,80)
 rs=R(s,f'R{rb}','C23140',70+x,67,'+5V_LOGIC',None,'33R',note='Compensated current servo; backup PNP limits short transients. Qualify pulse energy.')
 q=P(s,'Poofer:MJD350T4G',f'Q{100+ch}','C145514',67.46+x,93,angle=180,value='MJD350T4G',footprint='Package_TO_SOT_SMD:TO-252-3_TabPin2',notes='300VPNP;1B2/tabC3E;collectorremainsHVinfault.')
 e=(q['3'][0],snap(75));s.wire(rs['2'][:2],(rs['2'][0],e[1]));s.wire((rs['2'][0],e[1]),e);s.wire(e,q['3'][:2]);s.label(E,*e,180)
 d=P(s,'Diode:BAS21',f'D{100+ch}','C8661',q['2'][0],112,angle=90,value='BAS21',footprint=SOT);s.wire(q['2'][:2],d['1'][:2]);N(s,d,3,raw);s.local(f'IN{ch}_WET_COLLECTOR',q['2'][0],104)
 eb=R(s,f'R{rb+3}','C21190',105+x,80,'+5V_LOGIC',None,'1k',note='5VpullupBEFOREshunt preservescontactcurrent.');s.wire(eb['2'][:2],(eb['2'][0],q['1'][1]));s.wire((eb['2'][0],q['1'][1]),q['1'][:2]);s.label(B,eb['2'][0],q['1'][1],180)
 dv=P(s,'Transistor_BJT:MMBT3904',f'Q{110+ch}','C20526',153+x,116,value='MMBT3904',footprint=SOT);N(s,dv,2,'GND')
 cr=R(s,f'R{rb+2}','C21190',153+x,87,val='1k',note='MANDATORY: limits clamp versus driver current to <=5.4mA with resistor tolerance.')
 s.wire(cr['1'][:2],(115+x,cr['1'][1]));s.wire((115+x,cr['1'][1]),(115+x,q['1'][1]));s.wire((115+x,q['1'][1]),(eb['2'][0],q['1'][1]))
 s.wire(cr['2'][:2],(dv['3'][0],cr['2'][1]));s.wire((dv['3'][0],cr['2'][1]),dv['3'][:2]);s.local(DC,dv['3'][0],104)
 ref='U20' if ch<=4 else 'U21' if ch<=8 else 'U22';u=(ch-1)%4+1;p=IC(s,'Amplifier_Operational:LM2902',ref,'C350545',45+x,132,u,ON,val='LM2902DR');mi,pl,ou=op[u-1];N(s,p,pl,f'IN{ch}_EMIT_F')
 br=R(s,f'R{rb+1}','C4190',136+x,131,val='2.2k')
 s.wire(br['1'][:2],(br['1'][0],dv['1'][1]));s.wire((br['1'][0],dv['1'][1]),dv['1'][:2]);(s.label if ch==9 else s.local)(DB,br['1'][0],121)
 s.wire(p[str(ou)][:2],(118+x,p[str(ou)][1]));s.wire((118+x,p[str(ou)][1]),(118+x,br['2'][1]));s.wire((118+x,br['2'][1]),br['2'][:2]);s.local(f'IN{ch}_AMP_OUT',103+x,p[str(ou)][1])
 iso=R(s,f'R{rb+21}','C17414',44+x,141,'CURRENT_REF',None,'10k',90,note='Local isolation prevents nine compensated loops sharing an input node.')
 comp=P(s,'Device:C',f'C{130+ch}','C49678',82+x,137,value='100nF',footprint='Capacitor_SMD:C_0805_2012Metric',notes='Dominant compensation: OUT to isolated local IN-; do not connect directly to global reference.')
 s.wire(p[str(ou)][:2],(comp['1'][0],p[str(ou)][1]));s.wire((comp['1'][0],p[str(ou)][1]),comp['1'][:2]);s.wire(iso['2'][:2],comp['2'][:2]);lo=(comp['2'][0],snap(154));s.wire(comp['2'][:2],lo);s.wire(lo,(snap(32+x),lo[1]));s.wire((snap(32+x),lo[1]),(snap(32+x),p[str(mi)][1]));s.wire((snap(32+x),p[str(mi)][1]),p[str(mi)][:2]);s.label(f'IN{ch}_AMP_REF',32+x,149)
 dc=P(s,'Poofer:BAT54_215',f'D{140+ch}','C85084',25+x,104,angle=90,value='BAT54',footprint=SOT,notes='Reference-relative clamp protects compensation input during rail loss.')
 N(s,dc,1,'CURRENT_REF');N(s,dc,3,f'IN{ch}_AMP_REF')
 limit=P(s,'Transistor_BJT:MMBT3906',f'Q{150+ch}','C2143',168+x,61,angle=180,value='MMBT3906',footprint=SOT,notes='Fast backup limiter; senses half of33Rdrop, typically30-50mA surge bound.')
 for n,v in [(2,'+5V_LOGIC'),(1,f'IN{ch}_LIMIT_BASE'),(3,B)]:N(s,limit,n,v)
 R(s,f'R{rb+22}','C21190',124+x,61,'+5V_LOGIC',f'IN{ch}_LIMIT_BASE','1k')
 R(s,f'R{rb+23}','C21190',124+x,108,f'IN{ch}_LIMIT_BASE',E,'1k')
 q=P(s,'Transistor_BJT:MMBT3904',f'Q{120+ch}','C20526',50+x,191,value='MMBT3904',footprint=SOT);N(s,q,1,'GND')
 prev=None
 for k,xx in enumerate([91,122,153]):
  p=R(s,f'R{rb+4+k}','C25803',xx+x,213,val='100k',ang=90)
  if prev:s.wire(prev['2'][:2],p['1'][:2])
  else:s.wire(q['2'][:2],(q['2'][0],p['1'][1]));s.wire((q['2'][0],p['1'][1]),p['1'][:2]);s.label(UE,q['2'][0],207,180)
  prev=p
 d=P(s,'Diode:BAS21',f'D{120+ch}','C8661',178+x,213,angle=180,value='BAS21',footprint=SOT);s.wire(prev['2'][:2],d['1'][:2]);N(s,d,3,raw)
 er=R(s,f'R{rb+7}','C25803',38+x,224,b='GND',val='100k');s.wire(er['1'][:2],(er['1'][0],snap(207)));s.wire((er['1'][0],snap(207)),(q['2'][0],snap(207)))
 cv=P(s,'Device:C',f'C{160+ch}','C51210',70+x,224,value='1nF / 50V',footprint='Capacitor_SMD:C_0805_2012Metric',notes='Absorbs positive FIELD-step charge through the reverse blocker; prevents detector B-E avalanche. Qualify edge timing.')
 s.wire(cv['1'][:2],(cv['1'][0],snap(213)));N(s,cv,2,'GND',2.54)
 gr=R(s,f'R{rb+8}','C23231',112+x,187,a='+5V_LOGIC',val='68k')
 s.wire(q['3'][:2],(82+x,q['3'][1]));s.wire((82+x,q['3'][1]),(82+x,gr['2'][1]));s.wire((82+x,gr['2'][1]),gr['2'][:2]);s.local(G,97+x,gr['2'][1])
 pm=P(s,'Transistor_FET:AO3401A',f'Q{130+ch}','C15127',157+x,178,angle=180,value='AO3401A',footprint=SOT,notes='Low fault gate clamps PNP base to 5V, overriding servo.')
 for n,v in [(2,'+5V_LOGIC'),(3,B)]:N(s,pm,n,v)
 s.wire(pm['1'][:2],(183+x,pm['1'][1]));s.wire((183+x,pm['1'][1]),(183+x,snap(199)));s.wire((183+x,snap(199)),(gr['2'][0],snap(199)));s.wire((gr['2'][0],snap(199)),gr['2'][:2])
def receive(s,ch,x=0):
 s.channel=ch;s.bank=(ch-1)//4+1;raw,dig,flt=nn(ch);rb=1000+(ch-1)*30;SNS=f'IN{ch}_SENSE';UVS=f'IN{ch}_UV_SENSE';G=f'IN{ch}_UV_GATE'
 s.block(f'INPUT {ch} | ACTIVE-LOW RECEIVER',15+x,38,185,94,'LOW = closed; FAULT high masks invalid closure');s.block('PROTECTED FAULT FLAG',15+x,144,185,95,'Four 100k conductances bias and attenuate emitter')
 d=P(s,'Diode:BAS21',f'D{110+ch}','C8661',44+x,64,angle=180,value='BAS21',footprint=SOT);N(s,d,1,raw);prev=d['3'][:2]
 for k,xx in enumerate([72,99,126]):
  p=R(s,f'R{rb+14+k}','C25803',xx+x,64,val='100k',ang=90);s.wire(prev,p['1'][:2]);prev=p['2'][:2]
 ref='U10' if ch<=4 else 'U11' if ch<=8 else 'U12';u=(ch-1)%4+1;p=IC(s,'Comparator:LM339',ref,'C22427890',175+x,66.54,u,CN,val='LM2901BIDR');mi,pl,ou=cp[u-1]
 s.wire(prev,p[str(pl)][:2]);s.label(SNS,139+x,64,180);N(s,p,mi,'CONTACT_REF');N(s,p,ou,dig)
 sh=R(s,f'R{rb+17}','C23212',139+x,94,b='GND',val='6.8k');s.wire(sh['1'][:2],(sh['1'][0],snap(64)))
 cap=P(s,'Device:C',f'C{100+ch}','C1710',154+x,94,value='10nF / 50V',footprint='Capacitor_SMD:C_0805_2012Metric');N(s,cap,2,'GND');s.wire(cap['1'][:2],(cap['1'][0],snap(64)))
 f1=R(s,f'R{rb+18}','C22935',60+x,115,val='1M',ang=90);f2=R(s,f'R{rb+19}','C22935',106+x,115,val='1M',ang=90)
 s.wire(f1['1'][:2],(f1['1'][0],snap(83)));s.wire((f1['1'][0],snap(83)),(sh['1'][0],snap(83)));s.wire(f1['2'][:2],f2['1'][:2]);s.local(f'IN{ch}_HYST_MID',90+x,115)
 pu=R(s,f'R{rb+20}','C17414',175+x,103,a='+3V3',val='10k');s.wire(pu['2'][:2],(193+x,pu['2'][1]));s.wire((193+x,pu['2'][1]),(193+x,p[str(ou)][1]));s.wire((193+x,p[str(ou)][1]),p[str(ou)][:2]);s.wire(f2['2'][:2],(193+x,f2['2'][1]));s.wire((193+x,f2['2'][1]),(193+x,pu['2'][1]))
 r9=R(s,f'R{rb+9}','C25803',43+x,187,a=f'IN{ch}_UV_EMITTER',val='100k')
 r10=R(s,f'R{rb+10}','C25803',43+x,212,a='+3V3',val='100k')
 r11=R(s,f'R{rb+11}','C25803',91+x,212,b='GND',val='100k');r12=R(s,f'R{rb+12}','C25803',123+x,212,b='GND',val='100k')
 ref='U13' if ch<=4 else 'U14' if ch<=8 else 'U12';u=(ch-1)%4+1 if ch<=8 else 2;p=IC(s,'Comparator:LM339',ref,'C22427890',174+x,179,u,CN,val='LM2901BIDR');mi,pl,ou=cp[u-1];N(s,p,pl,'UV_REF');N(s,p,ou,flt)
 ysum=p[str(mi)][1];s.wire(r9['2'][:2],(61+x,r9['2'][1]));s.wire((61+x,r9['2'][1]),(61+x,ysum));s.wire((61+x,ysum),p[str(mi)][:2]);s.local(UVS,94+x,ysum)
 s.wire(r10['2'][:2],(71+x,r10['2'][1]));s.wire((71+x,r10['2'][1]),(71+x,ysum))
 for r in [r11,r12]:s.wire(r['1'][:2],(r['1'][0],ysum))
 pu=R(s,f'R{rb+13}','C17414',174+x,220,a='+3V3',val='10k');s.wire(pu['2'][:2],(193+x,pu['2'][1]));s.wire((193+x,pu['2'][1]),(193+x,p[str(ou)][1]));s.wire((193+x,p[str(ou)][1]),p[str(ou)][:2])
 if ch<=8:s.header(f'J{10+ch}',38+x,125,[raw,'GND'],'DrycontacttoGND;20mAboard-sourced;fieldfaultlimit+/-100V.')
for i in range(4):
 for ch,x in [(2*i+1,0),(2*i+2,198)]:source(src[i],ch,x);receive(rx[i],ch,x)
source(ef,9);receive(ef,9,198);ef.header('J9',70,259,['ESTOP_FIELD','ESTOP_CHAIN_OUT'],'ExternalNCcontactbetween1/2,serieschain.');ef.header('J10',172,259,['ESTOP_CHAIN_OUT','GND'],'LASTMODULEterminationonly;removeintermediatejumpers.')
q=P(ef,'Transistor_FET:AO3400A','Q149','C20917',250,259,footprint=SOT,notes='PhysicalEXPjumperdisablesEStopsource;GPIO2onlyisolatedmonitor.')
for n,v in [(1,'LOCAL_MASTER_N'),(2,'GND'),(3,'IN9_DRV_BASE')]:N(ef,q,n,v)
ef.text('ExactlyoneMASTERsuppliesloopwetting; all NC contacts and chainconnectors are in series.',15,276,1.0)

# Shared supplies and unused units are explicit, on a dedicated service sheet.
support=new('Analog_Support',f'{len(sheets)+1:02d} | Analog supplies, spare units and debug port','input_shared')
support.block('COMPARATOR BANK SUPPLIES',15,38,390,79,'One 100 nF bypass per physical IC; raw12V supply')
support.block('CURRENT-SERVO SUPPLIES',15,126,210,112,'Defined unused amplifiers; no floating inputs')
support.block('DEBUG / COMMAND BREAKOUT',236,126,169,112,'Power pins identified; monitor nodes isolated')
for j,ref in enumerate(['U10','U11','U12','U13','U14']):support.bank=[1,2,3,1,2][j];powerunit(support,'Comparator:LM339',ref,'C22427890',5,42+75*j,80,'+12V_IN',CN);C(support,f'C{80+j}',55+75*j,103,'+12V_IN','GND')
for j,ref in enumerate(['U20','U21','U22']):support.bank=j+1;powerunit(support,'Amplifier_Operational:LM2902',ref,'C350545',5,45+65*j,168,'+12V_IN',ON);C(support,f'C{90+j}',57+65*j,194,'+12V_IN','GND')
support.block('DEFINED UNUSED COMPARATORS',15,245,210,35)
for u in [3,4]:p=IC(support,'Comparator:LM339','U12','C22427890',55+108*(u-3),267,u,CN,val='LM2901BIDR');mi,pl,ou=cp[u-1];N(support,p,mi,'CONTACT_REF',2.54);N(support,p,pl,'GND',2.54);support.nc(p,ou)
for u in [3,4]:
 p=IC(support,'Amplifier_Operational:LM2902','U22','C350545',43+64*(u-2),220,u,ON,val='LM2902DR');mi,pl,ou=op[u-1];N(support,p,pl,'GND',2.54);support.wire(p[str(ou)][:2],(p[str(ou)][0],p[str(ou)][1]+7.62));support.wire((p[str(ou)][0],p[str(ou)][1]+7.62),(p[str(mi)][0]-2.54,p[str(ou)][1]+7.62));support.wire((p[str(mi)][0]-2.54,p[str(ou)][1]+7.62),(p[str(mi)][0]-2.54,p[str(mi)][1]));support.wire((p[str(mi)][0]-2.54,p[str(mi)][1]),p[str(mi)][:2])
support.group='serial_io';support.bank=None
support.header('J5',340,186,['GND','+3V3','+5V_LOGIC','+12V_IN','BUS_CLK','BUS_LOAD_N','BUS_LATCH','BUS_CLR_N','OE_MONITOR_N','HW_RUN_MON_GPIO21','ESTOP_SAFE_MON_GPIO18','ROLE_GPIO2_MON']+[f'RLY{i}_CMD' for i in range(1,9)],'Debug only; pins3/4 are5V/12V. Hardware status monitors isolated. Never injectcoil power.')

st.block('NC LOOP PERMISSION',15,38,185,61);st.block('EDGE-ARMED HARDWARE LATCH',212,38,193,112,'Loop restoration cannot clock the flip-flop');st.block('SUPERVISED COIL DISCONNECT',15,161,390,78)
NN='HC00 output-enable logic; 3.3V; all unit properties identical.';NO='HC02 loop permission and asynchronous clear; 3.3V.';NI='HC14 Schmitt conditioning; 3.3V.';NF='HC74 edge-armed RUN latch; async clear on stop or power fault; 3.3V.'
for lib,ref,code,u,x,y,ii,oo,nt in [('74xx:74HC02','U31','C5588',1,86,69,['ESTOP_CLOSED_N','ESTOP_UV_FAULT'],'SAFE_PERMIT',NO),('74xx:74HC02','U31','C5588',2,170,69,['SAFE_PERMIT','SAFE_PERMIT'],'STOP_REQUEST',NO),('74xx:74HC02','U31','C5588',3,255,69,['STOP_REQUEST','PG_FAULT'],'RUN_CLEAR_DRIVE_N',NO),('74xx:74HC00','U30','C5586',4,359,178,['HW_RUN_LATCH','ARM_LEVEL'],'RLY_OE_ACTUAL_N',NN)]:gate(st,lib,ref,code,u,x,y,ii,oo,nt)
for u,x,y,ii,oo in [(1,235,124,['BUS_ARM_N'],'ARM_LEVEL'),(3,300,178,['RLY_OE_ACTUAL_N'],'COIL_EN'),(4,95,124,['PG_RESET_N'],'PG_FAULT')]:gate(st,'74xx:74HC14','U32','C5605',u,x,y,ii,oo,NI)
ff=IC(st,'74xx:74HC74','U34','C27597',347,118,1,NF)
for n,net in [(1,'RUN_CLEAR_N'),(2,'+3V3'),(3,'ARM_LEVEL'),(4,'+3V3'),(5,'HW_RUN_LATCH')]:N(st,ff,n,net)
st.nc(ff,6)
R(st,'R150','C23162',283,95,'RUN_CLEAR_DRIVE_N','RUN_CLEAR_N','4.7k',90,note='Wired-AND clear: TLV9022 overrides HIGH with <0.74mA sink; qualify LOW across rail ramps.')
st.text('Arm clock is independent of permission: a held ARM cannot restart after stop restoration.',20,145,1.0)
gate(ex,'74xx:74HC14','U32','C5605',5,300,62,['LOCAL_MASTER_N'],'ROLE_RX_OE_N',NI)
ls=new('Logic_Support',f'{len(sheets)+1:02d} | Safety logic supplies and unused gates','emergency_stop')
ls.block('SAFETY LOGIC SUPPLIES',15,38,390,85,'Local 3.3V rail; 100nF at each package')
ls.block('DEFINED SPARE GATES',15,137,390,101,'No floating CMOS inputs; unused outputs left open')
for u in [1,2,3]:gate(ls,'74xx:74HC00','U30','C5586',u,65+80*(u-1),170,['GND','GND'],None,NN)
gate(ls,'74xx:74HC02','U31','C5588',4,345,170,['GND','GND'],None,NO)
for u,x in [(2,65),(6,145)]:gate(ls,'74xx:74HC14','U32','C5605',u,x,216,['GND'],None,NI)
sp=IC(ls,'74xx:74HC74','U34','C27597',304,211,2,NF)
for n,net in [(13,'GND'),(12,'GND'),(11,'GND'),(10,'+3V3')]:N(ls,sp,n,net)
ls.nc(sp,8);ls.nc(sp,9)
R(ls,'R136','C25803',230,220,'RLY_OE_ACTUAL_N','OE_MONITOR_N','100k',90,note='High-impedance test observation; limit ordinary counterdrive to<35uA. Use a high-impedance probe.')
for i,(lib,ref,code,u,nt) in enumerate([('74xx:74HC00','U30','C5586',5,NN),('74xx:74HC02','U31','C5588',5,NO),('74xx:74HC14','U32','C5605',7,NI),('74xx:74HC74','U34','C27597',3,NF)]):powerunit(ls,lib,ref,code,u,50+i*95,79,note=nt);C(ls,f'C{110+i}',63+i*95,104,'+3V3','GND')
p=P(st,'Transistor_FET:AO3401A','Q40','C15127',56,192,angle=180,value='AO3401A',footprint=SOT)
for n,v in [(2,'+12V_IN'),(3,'+12V_COIL_SAFE'),(1,'COIL_GATE')]:N(st,p,n,v)
R(st,'R110','C23162',94,186,'+12V_IN','COIL_GATE','4.7k');p=P(st,'Device:D_Zener','D91','C84362',124,187,angle=270,value='8.2V / 1W',footprint='Diode_SMD:D_SMA');N(st,p,1,'+12V_IN',2.54);N(st,p,2,'COIL_GATE',2.54)
rg=R(st,'R111','C21190',164,186,a='COIL_GATE',val='1k',ang=90)
a=P(st,'Transistor_BJT:MMBT3904','Q41','C20526',213,189,value='MMBT3904',footprint=SOT)
b=P(st,'Transistor_BJT:MMBT3904','Q42','C20526',213,220,value='MMBT3904',footprint=SOT)
st.wire(rg['2'][:2],(a['3'][0],rg['2'][1]));st.wire((a['3'][0],rg['2'][1]),a['3'][:2]);st.local('COIL_SINK',190,rg['2'][1])
st.wire(a['2'][:2],b['3'][:2]);st.local('COIL_MID',a['2'][0],205);N(st,b,2,'GND',2.54)
ar=R(st,'R112','C21190',172,189,a='COIL_EN',val='1k',ang=90);st.wire(ar['2'][:2],a['1'][:2]);st.local('COIL_ARM_BASE',190,189)
br=R(st,'R114','C17414',172,220,a='PG_RESET_N',val='10k',ang=90);st.wire(br['2'][:2],b['1'][:2]);st.local('COIL_PG_BASE',190,220)
for ref,y,yy,base in [('R113',203,189,a),('R115',234,220,b)]:
 r=R(st,ref,'C17414',190,y,b='GND',val='10k');st.wire(r['1'][:2],(r['1'][0],snap(yy)))
r=R(st,'R116','C25803',264,227,b='GND',val='100k');st.wire(r['1'][:2],(r['1'][0],snap(205)));st.wire((r['1'][0],snap(205)),(a['2'][0],snap(205)))
st.text('GPIO18 = loop permission; GPIO21 = hardware RUN. Fresh ARM edge clears a healthy stop.',15,252,1.0)
st.text('External safety contactor must disconnect valve power if welded-contact protection is required.',15,258,1.0)

refpage=new('Current_Reference',f'{len(sheets)+1:02d} | Buffered current reference and rail sequencing','input_shared')
refpage.bank=3;refpage.block('LOW-IMPEDANCE SHARED REFERENCE',15,38,390,118,'SpareU22B isolates all nine compensated source loops')
v=IC(refpage,'Amplifier_Operational:LM2902','U22','C350545',180,90,2,ON,val='LM2902DR')
N(refpage,v,5,'CURRENT_REF_RAW');refpage.wire(v['7'][:2],(203,90));refpage.wire((203,90),(203,111));refpage.wire((203,111),(159,111));refpage.wire((159,111),(159,v['6'][1]));refpage.wire((159,v['6'][1]),v['6'][:2])
a=R(refpage,'R66','C22775',245,90,val='100R',ang=90,note='Capacitive-load isolation and power-off discharge current limit.')
b=R(refpage,'R67','C22775',283,90,val='100R',ang=90)
refpage.wire(v['7'][:2],a['1'][:2]);refpage.wire(a['2'][:2],b['1'][:2]);refpage.label('CURRENT_REF_DRIVE',214,90,180)
c=P(refpage,'Device:C','C66','C15850',325,111,value='10uF / 25V',footprint='Capacitor_SMD:C_0805_2012Metric',notes='Holds reference during compensation-cap rail transitions; qualify effective capacitance.')
refpage.wire(b['2'][:2],(c['1'][0],b['2'][1]));refpage.wire((c['1'][0],b['2'][1]),c['1'][:2]);refpage.label('CURRENT_REF',307,90,180);N(refpage,c,2,'GND')
refpage.text('200ohm total bounds initial10uF discharge near22mA. Output behavior whenunpowered requireshardwarequalification.',20,174,1.05)
refpage.text('Per-source10k/100nF compensation uses a private negative-input node; never attach it directly to the rawdivider.',20,181,1.05)
refpage.text('Backup PNP limiters bound saturation recovery current. Power-good holds coiloutputs off through settling.',20,188,1.05)

i2c=new('I2C_Expansion',f'{len(sheets)+1:02d} | I2C expansion and power-off isolation','daisy_chain')
i2c.block('COMMON A BUS / PRIVATE B BUS',15,38,390,118,'AllA sides may share the bus; B sides must remain private')
q=IC(i2c,'Poofer:PCA9517AD','U54','C2802638',205,90,fp='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',val='PCA9517AD',note='NXP A variant;A sides commonUP/DOWN, B privateMCU. Partial-power isolation.')
for n,nm in [(1,'+3V3'),(8,'+3V3'),(4,'GND'),(5,'PG_RESET_N'),(2,'I2C_SCL_BUS'),(3,'I2C_SDA_BUS'),(7,'I2C_SCL_GPIO9'),(6,'I2C_SDA_GPIO8')]:N(i2c,q,n,nm)
i2c.header('JP2',76,198,['+3V3','I2C_PULLUP_RAIL'],'Close only one common-A pullup pair, normally master. No shared power pins.')
R(i2c,'R120','C4190',124,196,'I2C_PULLUP_RAIL','I2C_SDA_BUS','2.2k');R(i2c,'R121','C4190',174,196,'I2C_PULLUP_RAIL','I2C_SCL_BUS','2.2k')
R(i2c,'R122','C23162',296,196,'+3V3','I2C_SDA_GPIO8','4.7k');R(i2c,'R123','C23162',352,196,'+3V3','I2C_SCL_GPIO9','4.7k')
C(i2c,'C74',136,125,'+3V3','GND');C(i2c,'C75',272,125,'+3V3','GND')
i2c.text('Pins15SDA,16SCL on both chain ports. Default 100 kHz; qualify totalcommon-A capacitance<=400pF.',15,236,1.05)
i2c.text('32 A ports can contribute224pF before cabling.2.2k commonpullups meet the conservativeleakage/high-levelbudget.',15,243,1.05)
i2c.text('MCU B-side LOW mustbe<=0.4V; bufferedLOW<=0.6V remainsbelowESP VIL. Testload/temperaturecorners.',15,250,1.05)

bias=new('Expansion_Bias',f'{len(sheets)+1:02d} | Expansion defaults and buffer supplies','daisy_chain')
bias.block('DEFINED COMMAND DEFAULTS',15,38,390,153,'BUS / UP / LOCAL rows: safe receiver inputs even if MCU never boots or cable is absent')
for i,v in enumerate(['BUS_CLK','BUS_LATCH','BUS_CLR_N','BUS_ARM_N','BUS_LOAD_N','BUS_SER_IN']):R(bias,f'R{90+i}','C17414',49+i*61,83,'+3V3' if v in ['BUS_ARM_N','BUS_LOAD_N'] else 'GND',v,'10k')
for i,v in enumerate(['UP_CLK','UP_LATCH','UP_CLR_N','UP_ARM_N','UP_LOAD_N','UP_SER']):R(bias,f'R{124+i}','C17414',49+i*61,126,'+3V3' if v in ['UP_ARM_N','UP_LOAD_N'] else 'GND',v,'10k')
for i,v in enumerate(['MCU_CLK_GPIO6','MCU_LATCH_GPIO7','MCU_CLR_N_GPIO16','MCU_INHIBIT_N_GPIO15','MCU_LOAD_N_GPIO17','MCU_MOSI_GPIO4']):R(bias,f'R{130+i}','C17414',49+i*61,163,'+3V3' if v in ['MCU_INHIBIT_N_GPIO15','MCU_LOAD_N_GPIO17'] else 'GND',v,'10k',note='Local LVC244 input bias; MCU reset/high-Z cannot create floating ARM or latch edges.')
bias.block('CHAIN TAIL / LOCAL BYPASS',15,202,390,46,'Tail HIGH fills missing-module fault bits with FF; firmware masks these input bytes')
R(bias,'R88','C17414',59,230,'+3V3','DOWN_RETURN','10k')
for i in range(3):C(bias,f'C{70+i}',165+i*86,230,'+3V3','GND')
bias.text('Keep each 100nF physically beside its LVC244 VCC pin; no supply is shared by the expansion connectors.',15,275,1.05)

rails=new('Rail_Supervision',f'{len(sheets)+1:02d} | Hardware monitoring of 5V and raw 12V','emergency_stop')
rails.block('LOGIC-POWERED SUPPLY LOSS DETECTION',15,38,390,127,'Asynchronous RUN clear remains powered when the coil and analog rail disappears')
RMN='TLV9022DR dual rail monitor;3.3V open drain overrides RUN clear via4.7k; fault-tolerant inputs.'
for ch,x,rail,vals,base in [(1,0,'+12V_IN',['100k','100k'],151),(2,198,'+5V_LOGIC',['100k'],154)]:
 prev=None
 for i,val in enumerate(vals):
  r=R(rails,f'R{base+i}','C25803',50+x,73+18*i,a=rail if i==0 else None,val=val)
  if prev:rails.wire(prev['2'][:2],r['1'][:2])
  prev=r
 low=R(rails,f'R{base+len(vals)}','C17414',94+x,131,b='GND',val='10k')
 v=IC(rails,'Comparator:LM393','U35','C2871718',165+x,112,ch,RMN,fp='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',val='TLV9022DR');mi,pl,ou=[(2,3,1),(6,5,7)][ch-1]
 rails.wire(prev['2'][:2],(prev['2'][0],v[str(pl)][1]));rails.wire((prev['2'][0],v[str(pl)][1]),v[str(pl)][:2]);rails.local('RAIL12_SENSE' if ch==1 else 'RAIL5_SENSE',110+x,v[str(pl)][1])
 rails.wire(low['1'][:2],(low['1'][0],v[str(pl)][1]));N(rails,v,mi,'RAIL_UV_REF');N(rails,v,ou,'RUN_CLEAR_N')
 if ch==2:
  trim=R(rails,'R158','C22935',108+x,73,val='1M',note='100k||1M =90.909k; lowers5V trip to4.269V with normal-supply corner margin.')
  rails.wire(trim['1'][:2],(prev['1'][0],trim['1'][1]));rails.wire(trim['2'][:2],(trim['2'][0],v[str(pl)][1]))
rails.block('COMMON REFERENCE / LOCAL SUPPLY',15,178,390,62,'5V trip about4.27V;12V trip about8.88V; loss and restoration cannot clock RUN')
R(rails,'R156','C23231',48,206,'+3V3','RAIL_UV_REF','68k');R(rails,'R157','C17414',94,219,'RAIL_UV_REF','GND','10k');C(rails,'C156',139,219,'RAIL_UV_REF','GND','10nF / 50V','C57112')
powerunit(rails,'Comparator:LM393','U35','C2871718',3,217,210,'+3V3',RMN,fp='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm');C(rails,'C154',248,219,'+3V3','GND')
for ref,x in [('R137',303),('R138',337),('R139',371)]:R(rails,ref,'C21190',x,204,'+5V_LOGIC','GND','1k',note='WithR65 forms250ohm5V bleed; bounds9x100uA published25C leakage case to0.225V; hot leakage still requires qualification.')
R(rails,'R140','C21190',279,219,'+3V3','GND','1k',note='Explicit unpowered3.3V rail discharge / leakage return;10.9mW at3.3V.')
rails.text('R65 + R137/R138/R139 = 250ohm total 5V bleed.',302,230,1.0)
rails.text('Comparator common-mode inputs remain below0.7V, including13.2V raw power, while the3.3V supervisor is valid.',15,251,1.05)
rails.text('Open-drain outputs sink flip-flop clear;4.7k limits HC02 source current. Real rail ramps and recovery require tests.',15,258,1.05)

efilt=new('Source_Feedback_Filters',f'{len(sheets)+1:02d} | Stable emitter feedback for all wetting sources','input')
for ch in range(1,10):
 efilt.channel=ch;efilt.bank=(ch-1)//4+1;efilt.group='emergency_stop' if ch==9 else 'input';x=((ch-1)%3)*132;y=((ch-1)//3)*72;rb=1000+(ch-1)*30
 efilt.block(f'INPUT {ch} | EMITTER FEEDBACK',15+x,38+y,121,66,'10k / 100n low-pass removes high-frequency plant gain')
 r=R(efilt,f'R{rb+24}','C17414',55+x,68+y,a=f'IN{ch}_WET_EMIT',val='10k',ang=90,note='Positive-input plant filter; place at opampIN+; add0.15mA conservative bias-error budget.')
 c=P(efilt,'Device:C',f'C{140+ch}','C49678',99+x,87+y,value='100nF',footprint='Capacitor_SMD:C_0805_2012Metric',notes='Emitter-sense filter; keeps fast transistor path out of opamp high-frequency feedback.')
 efilt.wire(r['2'][:2],(c['1'][0],r['2'][1]));efilt.wire((c['1'][0],r['2'][1]),c['1'][:2]);efilt.label(f'IN{ch}_EMIT_F',111+x,r['2'][1],180);efilt.wire((c['1'][0],r['2'][1]),(snap(111+x),r['2'][1]));N(efilt,c,2,'GND',2.54)
efilt.text('Retain the separate OUT-to-IN- compensation. These filters improve illustrative AC phase margin; real parts still require tests.',15,266,1.0)

for s,start in zip(rp,[1,5]):
 for ch in range(start,start+4):
  s.channel=ch;x=((ch-start)%2)*198;y=((ch-start)//2)*104;s.block(f'VALVE {ch} | NO OUTPUT',15+x,38+y,185,100,'12 VDC / 1 A; fast release clamps; NC auxiliary')
  k=P(s,'Relay:SANYOU_SRD_Form_C',f'K{ch}','C30431',65+x,72+y,value='SRD-12VDC-SL-C',footprint='Poofer:Relay_SPDT_Songle_SRD',notes='Songle 1COM 2/5coil 3NC 4NO; hardware-gated coils.')
  for n,v in [(5,'+12V_COIL_SAFE'),(1,f'VALVE{ch}_COM'),(3,f'VALVE{ch}_NC_AUX'),(4,f'VALVE{ch}_NO')]:N(s,k,n,v)
  q=P(s,'Transistor_FET:AO3400A',f'Q{ch}','C20917',60+x,109+y,value='AO3400A',footprint=SOT);N(s,q,2,'GND',2.54)
  s.wire(k['2'][:2],(k['2'][0],q['3'][1]));s.wire((k['2'][0],q['3'][1]),q['3'][:2]);s.local(f'RLY{ch}_DRAIN',k['2'][0],95+y)
  r=R(s,f'R{200+ch}','C22775',36+x,105+y,a=f'RLY{ch}_CMD',val='100R',ang=90);s.wire(r['2'][:2],(44+x,r['2'][1]));s.wire((44+x,r['2'][1]),(44+x,q['1'][1]));s.wire((44+x,q['1'][1]),q['1'][:2]);s.local(f'RLY{ch}_GATE',44+x,q['1'][1])
  r=R(s,f'R{210+ch}','C25803',31+x,123+y,b='GND',val='100k');s.wire(r['1'][:2],(r['1'][0],q['1'][1]));s.wire((r['1'][0],q['1'][1]),(44+x,q['1'][1]))
  d=P(s,'Device:D_Schottky',f'D{10+ch}','C2480',109+x,61+y,angle=270,value='SS14',footprint='Diode_SMD:D_SMA')
  z=P(s,'Device:D_Zener',f'D{20+ch}','C84362',136+x,61+y,angle=270,value='8.2V / 1W',footprint='Diode_SMD:D_SMA');N(s,z,2,'+12V_COIL_SAFE')
  s.wire(d['2'][:2],(d['2'][0],q['3'][1]));s.wire((d['2'][0],q['3'][1]),q['3'][:2]);s.wire(d['1'][:2],z['1'][:2]);s.local(f'RLY{ch}_COIL_CLAMP',117+x,d['1'][1])
  s.header(f'J{30+ch}',182+x,98+y,[f'VALVE{ch}_COM',f'VALVE{ch}_NO',f'VALVE{ch}_NC_AUX'],'1COM fused12V, 2NO valve, 3NC auxiliary.')
  d=P(s,'Device:D_Schottky',f'D{30+ch}','C8678',100+x,119+y,angle=180,value='SS34',footprint='Diode_SMD:D_SMA');N(s,d,2,f'VALVE{ch}_RETURN')
  z=P(s,'Device:D_Zener',f'D{40+ch}','C224028',140+x,119+y,value='SMBJ8.0A',footprint='Diode_SMD:D_SMB');N(s,z,2,f'VALVE{ch}_NO')
  s.wire(d['1'][:2],z['1'][:2]);s.local(f'VALVE{ch}_CLAMP',112+x,d['1'][1])
  s.header(f'J{40+ch}',182+x,121+y,[f'VALVE{ch}_NO',f'VALVE{ch}_RETURN'],'Valve positiveNO, negativeRETURN. Independent external fusedpower.')

purposes={'Controller':'Processor, reset and programming','Power':'Logic supplies and monitored startup','Serial_IO':'8 command bits / 16 captured input bits','Expansion':'Buffered chain and physical module role','Hardware_Stop':'Asynchronous stop / edge-controlled restart','Analog_Support':'Analog bypassing and defined spare units','Logic_Support':'Safety logic bypassing and spare units','Current_Reference':'Stable shared wetting-current reference','I2C_Expansion':'Shared A bus / isolated private MCU bus','Stop_Field':'Protected NC loop and tail termination','Expansion_Bias':'Safe control defaults and bypass','Rail_Supervision':'Logic-powered raw supply-loss protection','Source_Feedback_Filters':'Stable transistor-loop feedback'}
for i,s in enumerate(sheets[1:]):
 x=15+(i%4)*99;y=98+(i//4)*23;root.child(s,x,y,92,14)
 root.text(purposes.get(s.name,'Protected contact sensing' if 'Receivers' in s.name else '20 mA source and field fault cutoff' if 'Sources' in s.name else 'NO valve contacts and release clamps'),x+4,y+5,1.1)
root.text('PCB placement stage only: no tracks, vias or copper pours.',15,260,1.1);root.text('Routing, actual-valve tests and independent system safety qualification remain required.',15,267,1.1)
for s in sheets:s.save()
custom=[get_symbol('Poofer:MJD350T4G'),get_symbol('Poofer:TLV803EA30DBZR'),get_symbol('Poofer:74HC32'),get_symbol('Poofer:BAT54_215'),get_symbol('Poofer:PCA9517AD')]
for s in custom:s[1]=s[1].split(':')[1]
(ROOT/'Poofer.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+''.join(sexp(s) for s in custom)+')')
(ROOT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Poofer") (type "KiCad") (uri "${KIPRJMOD}/Poofer.kicad_sym") (options "") (descr "Verified source transistor and supervisor pin maps")))')
components=[c for s in sheets for c in s.components]
for c in components:
 if c['ref'] in ['U10','U11','U13','U14','U20','U21']:c.update(group='input_shared',channel=None,bank=1 if c['ref'] in ['U10','U13','U20'] else 2)
 if c['ref'] in ['U12','U22']:c.update(group='emergency_stop',channel=9,bank=3)
(ROOT/'bom/design-components.json').write_text(json.dumps(components,indent=2))
(ROOT/'analysis/hardware_contract.json').write_text(json.dumps({'revision':'A.3','module_outputs':8,'module_input_bits':16,'contacts_active_low':True,'fault_bits_active_high':True,'pins':{'clock':6,'mosi':4,'miso':5,'latch':7,'mcu_inhibit_n':15,'clear_n':16,'load_n':17,'safe_permit':18,'hardware_run':21,'physical_role_monitor':2,'i2c_sda':8,'i2c_scl':9},'expansion':{'contacts':16,'sda_pin':15,'scl_pin':16,'power_pins':[],'i2c_rate_hz':100000,'i2c_common_pullup_ohm':2200,'i2c_private_pullup_ohm':4700},'source_target_mA':20,'minimum_passive':'0805','scope':'unroutedplacement'},indent=2))
print('A.3:',len(components),'physicalcomponents;',len(sheets),'functionalpages')
