"""Reviewed functional placement plan; package origins are on a0.5mm grid."""
import re
import pcbnew as p

def fallback_group(ref):
    """Legacy A.2 IDs; A.3 functional metadata takes precedence."""
    n=int(re.search(r'\d+',ref).group())
    if ref[0]=='K' and 1<=n<=8:return 'relay',n
    if ((ref[0]=='Q' and 1<=n<=8) or (ref[0]=='R' and (201<=n<=208 or 211<=n<=218)) or
        (ref[0]=='D' and (11<=n<=18 or 21<=n<=28)) or (ref[0]=='J' and (31<=n<=38 or 41<=n<=48))):return 'relay',n%10
    if ref[0]=='J' and 11<=n<=18:return 'input',n-10
    if ref[0]=='D' and 1<=n<=8:return 'input',n
    if ref[0]=='R' and 100<=n<=178:return 'input',(n-100)//10+1
    if ref[0]=='R' and 300<=n<=377:return 'input',(n-300)//10+1
    if ref[0]=='C' and 101<=n<=108:return 'input',n-100
    if ref[0]=='C' and 201<=n<=208:return 'input',n-200
    if ref[0]=='Q' and 101<=n<=108:return 'input',n-100
    if ref[0]=='Q' and 111<=n<=118:return 'input',n-110
    if ref[0]=='D' and 101<=n<=108:return 'input',n-100
    if ref[0]=='U' and 21<=n<=28:return 'input',n-20
    if ref in ['U5','U6','U7','U8','C111','C115','C221','C225']:return 'input_shared',0
    if ref in ['U1','J3','J4','J6','J7','C4','C5','C6','R2','R3']:return 'controller',0
    if ref in ['U3','U4','J5','J8','C7','C8','R4','R5','R6','R7','R8','R9']:return 'serial_io',0
    if ref in ['U2','J1','J2','C1','C2','C3']:return 'power',0
    return 'emergency_stop',0

def classify(ref,meta):
    group,ch=fallback_group(ref)
    c=meta.get(ref,{})
    proposed=c.get('group','')
    aliases={'mcu':'controller','serial':'serial_io','io':'serial_io','relay_driver':'relay','relay_output':'relay','inputs':'input','input_conditioning':'input','input_frontend':'input','wetting':'input','estop':'emergency_stop','safety':'emergency_stop','input_reference':'input_shared','reference':'input_shared','chain':'daisy_chain','expansion':'daisy_chain'}
    if proposed:
        proposed=aliases.get(proposed,proposed)
        if proposed in ['controller','power','serial_io','emergency_stop','input','relay','input_shared','daisy_chain']:
            group=proposed;ch=0
    if c.get('channel') is not None:ch=int(c['channel'])
    return group,ch

def layout_groups(layout,meta,mapping):
    groups={}
    for ref in layout.fp:
        if ref.startswith(('H','FID')):continue
        group,ch=classify(ref,meta)
        groups.setdefault((group,ch),[]).append(ref)

    # ESP32 antenna points out of the upper edge. The footprint's native
    # RF rule area includes15mm in front/at the sides of the antenna.
    layout.place('U1',28,13.5,group='01 Controller')
    for ref,x,y,a in [('J3',12,32.5,0),('J4',44,32.5,0),('J6',22,44,90),('J7',22,51,90)]:layout.place(ref,x,y,a,'01 Controller')
    for i in range(6):layout.place('R%d'%(130+i),39,31+4.5*i,90,'03 Daisy chain')
    for ref,x,y,angle in [('C5',15.5,9,180),('C4',15.5,12.5,180),('R2',14,16,0),('C6',14,19.5,0)]:layout.place(ref,x,y,angle,group='01 Controller')
    layout.pack([r for r in groups.get(('controller',0),[]) if 'PinHeader_1x20' not in layout.fp[r].GetFPIDAsString() and r not in ['C90','C91','C92']],(18,29,38,79),'01 Controller')
    layout.text('ESP32-S3',17,28,1.1,bold=True)
    layout.text('UART / 3.3V',20,55,0.8)
    layout.text('EN GND BOOT',20,40,0.8)
    layout.text('TX GND RX',20,47,0.8)
    layout.text('MOD 1-20',9.5,28.5,0.8)
    layout.text('MOD 21-40',38,28.5,0.8)

    for ref,x,y,a in [('U3',55,42,0),('U4',55,65,0),('J5',82.5,30.5,0),('J8',86.5,30.5,0),('C7',62,37.5,0),('C8',62,60.5,0)]:layout.place(ref,x,y,a,'02 Serial I-O')
    fault_regs=[r for (g,ch),refs in groups.items() if g=='serial_io' for r in refs if r!='U4' and '165' in layout.fp[r].GetValue() and r not in layout.positions]
    if len(fault_regs)>1:raise ValueError('More than one additional165 register needs an explicit placement plan.')
    for ref in fault_regs:
        layout.place(ref,55,78.5,group='02 Serial I-O')
        layout.text('165 FLT',51,85.5,0.8,bold=True)
    if fault_regs and 'C9' in groups.get(('serial_io',0),[]):layout.place('C9',62,74,group='02 Serial I-O')
    extraheaders=[r for (g,ch),refs in groups.items() if g in ['controller','serial_io'] for r in refs if r not in layout.positions and 'PinHeader_1x20' in layout.fp[r].GetFPIDAsString()]
    if len(extraheaders)>1:raise ValueError('More than one additional20-pin header needs an explicit placement plan.')
    for ref in extraheaders:
        layout.place(ref,90,27,90,'02 Serial I-O')
        legend='FAULT BREAKOUT' if any('FAULT' in name for (r,pin),name in mapping.items() if r==ref) else 'I/O BREAKOUT'
        layout.text(legend,90,23.5,0.8)
    layout.pack(groups.get(('serial_io',0),[]),(49,28,62,89.5),'02 Serial I-O')
    layout.text('595 OUT',51,50,0.9,bold=True)
    layout.text('165 IN',51,72,0.9,bold=True)
    if 'J5' in layout.fp:layout.text('DBG',84.5,83,0.8)
    if 'J8' in layout.fp:layout.text('TEST',86,83,0.8)

    chain=[r for (g,ch),refs in groups.items() if g=='daisy_chain' for r in refs]
    chain_headers=[r for r in chain if 'PinHeader_2x08' in layout.fp[r].GetFPIDAsString()]
    chain_headers.sort(key=lambda r:int(re.search(r'\d+',r).group()))
    if len(chain_headers)>2:raise ValueError('More than two chain headers need a revised placement plan.')
    for ref,y,legend in zip(chain_headers,[24,53],['UP / IN','DOWN / OUT']):
        layout.place(ref,4.5,y,group='03 Daisy chain')
        layout.text(legend,1.5,y-3,0.8)
        layout.text('15:SDA 16:SCL',1.5,y+22,0.8)
    layout.place('JP1',32,40,90,'03 Daisy chain')
    if 'JP1' in layout.fp:
        layout.text('MASTER',30,36.5,0.8)
        layout.text('OPEN: EXP',30,44,0.8)
    for ref,x,y in [('U50',24,63),('U51',24,77.5),('U52',24,92),('C70',33,57.5),('C71',33,72),('C72',33,86.5)]:layout.place(ref,x,y,group='03 Daisy chain')
    i2c_refs=['U54','JP2','R120','R121','R122','R123','C74','C75']
    for ref,x,y,angle in [('U54',51.5,94,0),('C74',45,92,180),('C75',58,92,0),('JP2',59.5,99,90)]:layout.place(ref,x,y,angle,'03 I2C isolation')
    layout.pack(i2c_refs,(44,86.5,63.5,100.5),'03 I2C isolation',gap=1)
    if 'U54' in layout.fp:
        layout.text('I2C',44,85.5,0.8,bold=True)
        layout.text('JP2 HOST PU',44,99.5,0.8)
    layout.pack([r for r in chain if r not in i2c_refs],(18,56,40.5,100.5),'03 Daisy chain',gap=1)

    for ref,x,y,a in [('J1',59,5.5,90),('J2',75,5.5,90),('U2',64,16,0),('U40',74.5,22,0),('C40',79.5,22,0)]:layout.place(ref,x,y,a,'03 Power')
    for ref,x,y in [('R137',65,25),('R138',69.5,25),('R139',74.5,26),('R140',79.5,26)]:layout.place(ref,x,y,group='03 Power')
    layout.pack(groups.get(('power',0),[]),(54,10,84,27),'03 Power')
    layout.text('5V  GND',57,9,0.8)
    layout.text('12V GND',73,9,0.8)
    layout.text('POWER',58,27.5,1,bold=True)

    safetylogic=[r for (g,c),refs in groups.items() if g=='emergency_stop' and c!=9 for r in refs]
    for ref,y in [('U30',36),('U31',49),('U32',62),('U33',75),('U34',75),('U35',88.5)]:layout.place(ref,70.5,y,group='04 Hardware stop latch and coil gate')
    for ref,y in [('C110',32),('C111',45),('C112',58),('C113',71)]:layout.place(ref,77,y,group='04 Hardware stop latch and coil gate')
    layout.place('C154',77,86.5,0,'04 Hardware stop latch and coil gate')
    layout.place('R136',77.5,50.5,0,'04 Hardware stop latch and coil gate')
    layout.pack(safetylogic,(64,29.5,86.5,99.5),'04 Hardware stop latch and coil gate',gap=1)
    layout.text('HW LATCH',64,28,0.85,bold=True)
    safety=[r for (g,c),refs in groups.items() if g=='emergency_stop' and c==9 for r in refs]
    safety += [r for (g,c),refs in groups.items() if g=='input_shared' for r in refs if int(meta.get(r,{}).get('bank',0) or 0)==3]
    layout.place('J9',166,5.5,90,'05 Protected emergency-stop loop')
    layout.place('J10',166,12.5,90,'05 Protected emergency-stop loop')
    layout.text('NC LOOP',164,9,0.8)
    layout.text('LAST: TERM',164,16,0.8)
    for ref,x,y in [('Q109',95,10.5),('U22',112,10.5),('U12',130,10.5)]:layout.place(ref,x,y,group='05 Protected emergency-stop loop')
    layout.place('C92',105.5,10.5,180,'05 Protected emergency-stop loop')
    layout.place('C82',123.5,9,180,'05 Protected emergency-stop loop')
    layout.place('C149',105.5,7,180,'05 Protected emergency-stop loop')
    layout.place('R1264',105.5,3,270,'05 Protected emergency-stop loop')
    layout.place('Q129',137,11,0,'05 Protected emergency-stop loop')
    layout.place('C169',137,15,0,'05 Protected emergency-stop loop')
    layout.pack(safety,(85,4.5,161,22),'05 Protected emergency-stop loop',gap=1)
    layout.text('PROTECTED E-STOP / NC LOOP',85,24.5,0.9,bold=True)

    # Eight identical relay cells, with contacts/valve headers above the
    # relay and the low-voltage coil driver below. Contact supplies remain
    # isolated from logic/coil ground; do not join returns accidentally.
    for channel in range(1,9):
        col=(channel-1)%4;row=(channel-1)//4
        x=89+26.5*col;y=28+42*row
        name='Relay %02d'%channel
        for ref,dx,dy,a in [
            ('K%d'%channel,1.5,13.5,0),('J%d'%(30+channel),2,2.5,90),('J%d'%(40+channel),14,2.5,90),
            ]:layout.place(ref,x+dx,y+dy,a,name)
        layout.pack(groups.get(('relay',channel),[]),(x,y+23,x+24.5,y+38),name,gap=1)
        layout.text('COM NO NC',x+4.5,y-0.5,0.8,justify='center')
        layout.text('V+ V-',x+15,y-0.5,0.8,justify='center')
        layout.text('RLY %d'%channel,x+14,y+39.5,0.85,justify='center',bold=True)
    top=25.5
    layout.rect(88,top,194.5,110.5)
    for x in [114.5,141,167.5]:layout.line(x,top,x,110.5)
    layout.line(88,68.5,194.5,68.5)

    for bank,chips,positions,capmap,region in [
        (1,['U10','U20','U13'],[(16,106.5),(40,106.5),(64,106.5)],{'C80':(9.5,105),'C90':(33.5,106.5),'C83':(57.5,105)},(9,101.5,79,115.5)),
        (2,['U11','U21','U14'],[(120,116.5),(147,116.5),(175,116.5)],{'C81':(113.5,115),'C91':(140.5,116.5),'C84':(168.5,115)},(109,111.5,189,121.5))]:
        name='Input analog bank %d'%bank
        for ref,(x,y) in zip(chips,positions):layout.place(ref,x,y,group=name)
        for ref,(x,y) in capmap.items():layout.place(ref,x,y,180,group=name)
        channels=range(1,5) if bank==1 else range(5,9)
        xs=(33.5,46.5) if bank==1 else (140.5,153.5)
        ys=(103,110) if bank==1 else (113,120)
        # Receiver filters sit beside the actual opamp IN+ pins. The
        # capacitor's signal pad faces the IC; series resistors stay next
        # to the capacitor, keeping the filtered node local.
        for channel,x,y,side in [
            (channels[0],xs[0],ys[0],'left'),(channels[1],xs[0],ys[1],'left'),
            (channels[2],xs[1],ys[1],'right'),(channels[3],xs[1],ys[0],'right')]:
            rb=1000+(channel-1)*30
            layout.place('C%d'%(140+channel),x,y,180 if side=='left' else 0,name)
            layout.place('R%d'%(rb+24),x-4.5 if side=='left' else x+4.5,y,0 if side=='left' else 180,name)
        shared=[r for (g,c),refs in groups.items() if g=='input_shared' for r in refs if int(meta.get(r,{}).get('bank',0) or 0)==bank]
        layout.pack(shared,region,name,gap=1)
    layout.text('INPUTS / ACTIVE LOW / 20mA / +/-100V',8,120,0.8,bold=True)

    # One coherent bottom row of inputs. Headers sit at the field edge;
    # each cell contains its own fault protection and wetting source.
    for channel in range(1,9):
        x=5+24*(channel-1);name='Input %02d'%channel
        layout.place('J%d'%(10+channel),x+8,157,90,name)
        layout.place('Q%d'%(120+channel),x+7.5,133,0,name)
        layout.place('C%d'%(160+channel),x+7.5,137,0,name)
        layout.pack(groups.get(('input',channel),[]),(x+0.5,122.5,x+23.5,154),name,gap=1)
        layout.text('IN %d'%channel,x+11.5,154.5,0.8,justify='center',bold=True)
        if channel<8:layout.line(x+23.5,122,x+23.5,154.5)
    layout.line(4.5,122,197,122)
    layout.text('INPUT HEADER: 1 SWITCH / 2 GND',8,118,0.8)
    layout.text('UNIVERSAL POOFER CONTROL',86,112,1.1,bold=True,layer=p.B_SilkS)
    layout.text('REV A.3 | 12VDC VALVES | 1A / CHANNEL',86,116,0.9,layer=p.B_SilkS)
    layout.text('NC = AUXILIARY CONTACT / VALVES USE NO',86,120,0.9,layer=p.B_SilkS)
    layout.text('E-STOP CUTS RELAY COIL POWER',86,124,0.9,layer=p.B_SilkS)
