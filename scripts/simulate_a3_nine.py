#!/usr/bin/env python3
"""Nine-loop simultaneous-contact check; clones only independently verified nativecells.

Shared reference divider, follower, isolator and capacitor remain a single network.
A synthetic candidate is marked when the native export predates those additions.
"""
import gzip,json,re,subprocess
import simulate_a3_inputs as s

def run_nine(name='nine_final',shutdown=None):
 s.deck('nine_base',mode='switched_contact',compensate=True,comp_cap='100n',limiter=True,emit_only=True)
 base=(s.WORK/'nine_base.cir').read_text().splitlines()
 generic_local={'CTRL','NC_CONTACT','PNPCOL_DEVICE','LIM_BASE','LOCAL_AMP_MINUS','AMPSTATE','AMPHI','AMPSOURCE','wet_i','pnp_p','shunt_p','driver_i','amp_minus'}
 known_local={f'R{i}' for i in range(1000,1021)}|{'D101','D111','D121','Q101','Q111','Q121','MQ131','C101'}
 mods=[];out=['Nine A3 fieldloops; shared circuitry is instantiatedonce']
 used=[]
 for ch in range(1,10):
  nodemap={}
  mappings=[(f'R{1000+k}',f'R{1000+30*(ch-1)+k}') for k in range(21)]+[(f'{a}{b+1}',f'{a}{b+ch}') for a,b in [('Q',100),('Q',110),('Q',120),('Q',130),('D',100),('D',110),('D',120),('C',100)]]
  for old,new in mappings:
   for (ref,pin),net in s.PINS.items():
    if ref==old and (new,pin) in s.PINS:nodemap[s.sp(net)]=s.node(new,pin)
  # Use only local node mappings; common5V,3V3,12V/GND names remain shared.
  nodemap={k:v for k,v in nodemap.items() if k not in ['0',s.V5,s.V33,s.V12]}
  nodemap.update({s.FIELD:s.sp('ESTOP_FIELD' if ch==9 else f'IN{ch}_FIELD'),s.OUT:s.sp('ESTOP_CLOSED_N' if ch==9 else f'IN{ch}_N'),s.FAULT:s.sp('ESTOP_UV_FAULT' if ch==9 else f'IN{ch}_FAULT')})
  for line in base[1:]:
   if line=='.control':break
   if not line or line.startswith('*'):continue
   if line.startswith('.model'):
    if line not in mods:mods.append(line)
    continue
   if line.startswith('.temp') or line.startswith('.options'):
    if ch==1:out.append(line)
    continue
   ref=line.split()[0]
   islocal=ref in known_local or 'IN1_' in line or any(re.search(r'\b'+n+r'\b',line) for n in generic_local)
   if not islocal:
    if ch==1:out.append(line)
    continue
   for old,new in sorted(nodemap.items(),key=lambda p:-len(p[0])):line=re.sub(r'\b'+re.escape(old)+r'\b',new,line)
   line=line.replace('IN1_',f'IN{ch}_')
   for old in sorted(generic_local,key=len,reverse=True):line=re.sub(r'\b'+old+r'\b',old+f'_CH{ch}',line)
   if not line.startswith('.'):
    ref=line.split()[0];new=ref[0]+f'CH{ch}_'+ref[1:];line=line.replace(ref,new,1)
    line=line.replace('I(VWET)',f'I(VCH{ch}_WET)')
   if shutdown and line.startswith('VCH') and '_CTRL ' in line:line=line.split(' PWL')[0]+' 0'
   out.append(line)
  used.append({'channel':ch,'native_node_map_entries':len(nodemap)})
 if shutdown:
  cut={'all':['V5','V33','V12'],'12':['V12'],'5':['V5']}[shutdown]
  for i,line in enumerate(out):
   if line.split()[0] in cut:
    q=line.split();v=q[-1];out[i]=' '.join(q[:3])+f' PWL(0 {v} 2m {v} 2.0001m 0 30m 0)'
  stop='30m';window=(.025,.029)
 else:stop='31m';window=(.025,.029)
 out+=mods+['.control','set wr_vecnames','set wr_singlescale',f'tran 1u {stop} 0 1u','wrdata '+name+'.dat '+ ' '.join(f'v(wet_i_CH{ch})' for ch in range(1,10))+f' v({s.CRE}) v(amp_minus_CH1)','quit','.endc','.end']
 p=s.WORK/(name+'.cir');p.write_text('\n'.join(out)+'\n');r=subprocess.run(['ngspice','-b',str(p)],cwd=s.WORK,text=True,capture_output=True,timeout=60);(s.WORK/(name+'.log')).write_text(r.stdout+'\n'+r.stderr)
 if r.returncode or 'Error:' in r.stderr:raise RuntimeError(r.stderr[-2500:])
 raw=(s.WORK/(name+'.dat')).read_bytes();rows=[list(map(float,l.split())) for l in raw.decode().splitlines()[1:]]
 (s.WORK/(name+'.dat.gz')).write_bytes(gzip.compress(raw));(s.WORK/(name+'.dat')).unlink()
 result={'case':name,'topology':'Verified repeated native cells, shared reference instantiated once, all nine emitter filters and UV capacitors included from current export.','native_sha256':s.hashlib.sha256(s.NET.read_bytes()).hexdigest(),'native_components':len(s.COMP),'native_emitter_filter':s.pn('U20',3).split('/')[-1]=='IN1_EMIT_F','native_uv_caps':('C161','1') in s.PINS,'native_node_maps':used,'window_s':list(window),'channels':{},'minimum_global_reference_v':min(z[10] for z in rows),'minimum_local_reference_v':min(z[11] for z in rows)}
 for ch in range(1,10):
  vals=[z[ch]*1000 for z in rows if window[0]<z[0]<window[1]]
  result['channels'][str(ch)]={'late_min_ma':min(vals),'late_max_ma':max(vals),'max_after_first1us_ma':max(z[ch]*1000 for z in rows if .001002<z[0]<.03)}
 (s.WORK/(name+'_summary.json')).write_text(json.dumps(result,indent=2)+'\n')
 return result

if __name__=='__main__':print(json.dumps(run_nine(),indent=2))
