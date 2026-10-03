#!/usr/bin/env python3
"""Manufacturer LM2902 transient fixture derived from current native A3 nodes."""
import gzip,json,subprocess
import simulate_a3_inputs as s

def run_vendor(name='vendor_contact',mode='switched_contact'):
 s.deck(name+'_base',mode=mode,emit_only=True)
 lines=(s.WORK/(name+'_base.cir')).read_text().splitlines();out=[]
 remove=('BGM ','CAMP ','BAMPRESET ','VHIGH ','BAMPCLIP ','BAMP ','RAMP ','BAMPSTAGE ','BREFGM ','CREFSTATE ','BREFCLIP ','BREFOUT ','RREFOUT ','BREFSTAGE ','.ic ')
 minus=s.node('U20',2);raw=s.node('R55',2);drive=s.node('U22',7)
 for line in lines:
  if line.startswith(remove):continue
  if line.startswith('.nodeset'):
   if 'AMPSTATE' in line or 'REFSTATE' in line:continue
  if line=='.control':
   out+=[f'XAMP {s.E} {minus} {s.V12} 0 {s.AMP} LMX24_LM2902',f'XBUF {raw} {drive} {s.V12} 0 {drive} LMX24_LM2902','.include ../models/lmx24_lm2902.lib']
  if line.startswith('VCTRL '):line='VCTRL CTRL 0 PWL(0 0 20m 0 20.001m 5 70m 5 70.001m 0 75m 0)'
  if line.startswith('tran '):line='tran 2u 75m 0 2u uic'
  if line.startswith('V5 '):line=f'V5 {s.V5} 0 PWL(0 0 0.1m 5 75m 5)'
  if line.startswith('V33 '):line=f'V33 {s.V33} 0 PWL(0 0 0.1m 3.3 75m 3.3)'
  if line.startswith('V12 '):line=f'V12 {s.V12} 0 PWL(0 0 0.1m 12 75m 12)'
  if line.startswith('wrdata '):line=line.replace(name+'_base.dat',name+'.dat')
  out.append(line)
 p=s.WORK/(name+'.cir');p.write_text('\n'.join(out)+'\n')
 (s.WORK/'.spiceinit').write_text('set ngbehavior=ps\n')
 r=subprocess.run(['ngspice','-b',str(p)],cwd=s.WORK,text=True,capture_output=True,timeout=60);(s.WORK/(name+'.log')).write_text(r.stdout+'\n'+r.stderr)
 if r.returncode or 'Error:' in r.stderr:raise RuntimeError(r.stderr[-5000:])
 raw=(s.WORK/(name+'.dat')).read_bytes();rows=[{'scale':z[0],**dict(zip(s.OBS,z[1:]))} for z in [list(map(float,l.split())) for l in raw.decode().splitlines()[1:]]]
 (s.WORK/(name+'.dat.gz')).write_bytes(gzip.compress(raw));(s.WORK/(name+'.dat')).unlink()
 vals=[x['wet_i']*1000 for x in rows if .065<x['scale']<.069]
 result={'native_sha256':s.hashlib.sha256(s.NET.read_bytes()).hexdigest(),'source':'https://www.ti.com/lit/zip/SGLM009','manufacturer_model':'TI LMX24_LM2902 RevA,June24,2024; SGLM009D. ModelincludesAol/phase,Zo/output-currentlimiting,slew,overloadrecovery. Modelnotfulltemp/manufacturer-cornerguarantee. GenericBJT/FET/diodes retained.','late_min_ma':min(vals),'late_max_ma':max(vals),'peak_after1us_ma':max(x['wet_i']*1000 for x in rows if .020002<x['scale']<.07),'final':s.metrics(rows[-1])}
 (s.A/'revA3_vendor_model_summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 return result

if __name__=='__main__':run_vendor()
