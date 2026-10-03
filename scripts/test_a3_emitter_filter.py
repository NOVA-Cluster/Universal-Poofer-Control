#!/usr/bin/env python3
"""Candidate10k/100nHF plantattenuation, nativebase plus explicit proposed filter."""
import gzip,json,subprocess
import simulate_a3_inputs as s

def run(name='candidate_emitter_filter',limit=.005):
 s.deck(name+'_base',mode='switched_contact',emit_only=True,amp_limit=limit)
 out=[]
 for line in (s.WORK/(name+'_base.cir')).read_text().splitlines():
  if line.startswith('BGM '):line=line.replace('V('+s.E+')-V(','V(EMITTER_FILTER)-V(')
  if line.startswith('IAMPIN '):line=line.replace(s.E,'EMITTER_FILTER')
  if line=='.control':out+=[f'REFILTER {s.E} EMITTER_FILTER 10k','CEFILTER EMITTER_FILTER 0 100n','.ic V(EMITTER_FILTER)=4.89']
  if line.startswith('wrdata '):line=line.replace(name+'_base.dat',name+'.dat')
  out.append(line)
 p=s.WORK/(name+'.cir');p.write_text('\n'.join(out)+'\n');r=subprocess.run(['ngspice','-b',str(p)],cwd=s.WORK,text=True,capture_output=True,timeout=60);(s.WORK/(name+'.log')).write_text(r.stdout+'\n'+r.stderr)
 if r.returncode or 'Error:' in r.stderr:raise RuntimeError(r.stderr[-3000:])
 raw=(s.WORK/(name+'.dat')).read_bytes();rows=[{'scale':z[0],**dict(zip(s.OBS,z[1:]))} for z in [list(map(float,l.split())) for l in raw.decode().splitlines()[1:]]]
 (s.WORK/(name+'.dat.gz')).write_bytes(gzip.compress(raw));(s.WORK/(name+'.dat')).unlink()
 v=[x['wet_i']*1000 for x in rows if .025<x['scale']<.029]
 result={'proposal':'NativeE->10k->opampIN+,100n toGND; local10k/100nOUT-toIN− compensation retained.','not_in_native_netlist':True,'output_current_limit_A':limit,'late_min_ma':min(v),'late_max_ma':max(v),'final':s.metrics(rows[-1])};(s.A/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 return result

if __name__=='__main__':run()
