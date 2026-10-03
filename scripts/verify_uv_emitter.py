#!/usr/bin/env python3
"""Audit proposed negative-emitter status; native-base/candidate-wiring are explicit."""
import gzip,itertools,json,subprocess
import simulate_a3_inputs as s

def corner(rt=33000,tol=.01,sense_r=1e6):
 trips=[];marg=[]
 for f in itertools.product([1-tol,1+tol],repeat=6):
  g=[1/(sense_r*x) for x in f[:4]];t=rt*f[4];b=10000*f[5];th=1/(1/t+1/b)
  for v,off,isns,iref in itertools.product([3.201,3.399],[-.0055,.0055],[0,50e-9],[0,9*50e-9]):
   ref=v*b/(t+b)+iref*th
   trip=((ref+off)*sum(g)-v*g[1]-isns)/g[0]
   healthy=(v*g[1]+isns)/sum(g)-ref-off
   trips.append((trip,f,v,off,isns,iref));marg.append(healthy)
 return {'min_trip_v':min(trips)[0],'max_trip_v':max(trips)[0],'minimum_healthy_margin_v':min(marg),'worst_late_parameters':min(trips)[1:]}

def sim(name,temp=27,vto=-.9,uvbf=150,rt=33000,worst=None,sense_r=1e6):
 s.deck(name+'_base',mode='external',sweep=(0,-100,-.1),temp=temp,vto=vto,uvbf=uvbf,emit_only=True)
 lines=(s.WORK/(name+'_base.cir')).read_text().splitlines();out=[]
 for line in lines:
  if line.startswith('BAMP '):line=f'BAMP AMPSOURCE 0 V={{V({s.V12})<3 ? 0 : 10.5}}'
  if line.startswith('BREFOUT '):line=f'BREFOUT REFSOURCE 0 V={{V({s.V12})<3 ? 0 : 4.333}}'
  if line.startswith('R1009 '):line=line.replace(s.GATE,s.UE)
  if line.split()[0] in ['R1009','R1010','R1011','R1012']:line=line.rsplit(' ',1)[0]+' '+str(sense_r)
  if line.startswith('R60 '):line=line.rsplit(' ',1)[0]+' '+str(rt)
  if worst:
   factors,v33,off,bias,refbias=worst
   if line.startswith('V33 '):line=line.rsplit(' ',1)[0]+' '+str(v33)
   for ref,mul in zip(['R1009','R1010','R1011','R1012','R60','R61'],factors):
    if line.startswith(ref+' '):
     val=sense_r if ref in ['R1009','R1010','R1011','R1012'] else rt if ref=='R60' else 10000
     line=line.rsplit(' ',1)[0]+' '+str(val*mul)
   if line.startswith('BUV '):line=line.replace('V('+s.UVSNS+')-V('+s.UREF+')','V('+s.UVSNS+')-V('+s.UREF+')-('+str(off)+')')
   if line=='.control':out+=[f'IUVSENSE 0 {s.UVSNS} {bias}',f'IUVREF 0 {s.UREF} {refbias}']
  if line.startswith('wrdata '):line=line.replace(name+'_base.dat',name+'.dat')
  out.append(line)
 p=s.WORK/(name+'.cir');p.write_text('\n'.join(out)+'\n');r=subprocess.run(['ngspice','-b',str(p)],cwd=s.WORK,text=True,capture_output=True,timeout=30);(s.WORK/(name+'.log')).write_text(r.stdout+'\n'+r.stderr)
 if r.returncode or 'Error:' in r.stderr:raise RuntimeError(r.stderr[-2500:])
 raw=(s.WORK/(name+'.dat')).read_bytes();rows=[{'field':z[0],**dict(zip(s.OBS,z[1:]))} for z in [list(map(float,l.split())) for l in raw.decode().splitlines()[1:]]]
 (s.WORK/(name+'.dat.gz')).write_bytes(gzip.compress(raw));(s.WORK/(name+'.dat')).unlink()
 off=next((x for x in rows if x['wet_i']<.001),None);fault=next((x for x in rows if x[s.FAULT]>1.65),None)
 gaps=[x for x in rows if x['field']<-.5 and x['wet_i']<.001 and x[s.FAULT]<.7]
 possible=next((x for x in rows if x[s.GATE] < 4.5),None)
 return {'amp_model_for_ordering':'Held saturatedHIGH; source regulator is not being characterized bythisfixture. Compare earliestpossibleVGS=-0.5 clamp onset aswell as fullcutoff.','first_possible_pmos_on_field_v':possible['field'] if possible else None,'first_source_under1ma_field_v':off['field'] if off else None,'source_cutoff_uv_emitter_v':off[s.UE] if off else None,'first_flag_high_field_v':fault['field'] if fault else None,'flag_emitter_v':fault[s.UE] if fault else None,'source_off_flag_low_field_interval_v':[gaps[0]['field'],gaps[-1]['field']] if gaps else [],'healthy_fault_v':rows[0][s.FAULT]}

if __name__=='__main__':
 report={'candidate':'Move R1009 firstterminalfromUV_GATE toUV_EMITTER onallninecells; R60 top33k/R61 bottom10k. Retains4x1M attenuation, supplies12V/3.3V.','native_basis_sha256':s.hashlib.sha256(s.NET.read_bytes()).hexdigest(),'corners':{'1pct':corner(),'1pct_plus_65C_100ppm':corner(tol=.0165)},'runs':{}}
 report['runs']['nominal']=sim('uv_emitter_nominal')
 for t in [-40,85]:
  report['runs']['worst_'+str(t)]=sim('uv_emitter_worst_'+str(t).replace('-','m'),temp=t,vto=-.5,uvbf=300,worst=report['corners']['1pct_plus_65C_100ppm']['worst_late_parameters'])
 p=s.A/'uv_emitter_candidate.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
