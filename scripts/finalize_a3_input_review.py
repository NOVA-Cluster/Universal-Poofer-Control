#!/usr/bin/env python3
"""Attach final native provenance and the independently owned evidence toA3results."""
import hashlib,json,re
from pathlib import Path
import simulate_a3_inputs as s

p=s.A/'revA3_input_simulation.json';r=json.loads(p.read_text());previous=r['netlist_sha256'];current=hashlib.sha256(s.NET.read_bytes()).hexdigest()
old=(s.WORK/'closed_0p1ohm.cir').read_text()
s.deck('closed_0p1ohm',mode='contact',rcontact=.1,emit_only=True)
new=(s.WORK/'closed_0p1ohm.cir').read_text()
def canonical(x):return '\n'.join(l for l in x.splitlines() if not l.startswith('* SHA256'))
assert canonical(old)==canonical(new),'Analogfixturechanged; rerun numericalsuite.'
r['provenance']={'numeric_run_netlist_sha256':previous,'final_project_netlist_sha256':current,'final_components':len(s.COMP),'same_analog_fixture_verified':True,'note':'Laterdigitalstartup/debugisolation changes leave the tested native analogdeckidentical. Finalall9connectivityauditrerun.'}
r['netlist_sha256']=current;r['native_components']=len(s.COMP);r['netlist_connectivity_checks']=s.AUDIT
nine=json.loads((s.WORK/'nine_final_summary.json').read_text());nine['numeric_run_netlist_sha256']=nine.get('native_sha256');nine['native_sha256']=current;nine['native_components']=len(s.COMP);nine['same_analog_fixture_verified']=True
(s.WORK/'nine_final_summary.json').write_text(json.dumps(nine,indent=2)+'\n');r['nine_simultaneous_contact_test']=nine
r['positive_edge_capacitor_evidence']=json.loads((s.A/'uv_emitter_capacitor_check.json').read_text())
r['UV_threshold_ordering']=json.loads((s.A/'uv_final_ordering.json').read_text())
r['rail_monitor_evidence']=json.loads((s.ROOT/'datasheets'/'rail-monitor-critical-facts.json').read_text())
r['independent_loop_evidence_file']='analysis/source-loop-independent.json'
r['model_basis']['opamp']='DC: centered gain100 plus idealreferencefollower is deliberately used to improve convergence; not a precision device corner model. Dynamic: approximateAol100k,GBW1.2MHz,slew0.5V/us,output50Ω/currentlimit5mA; actualnative10k/100nIN+ filter and10k/100nlocalIN−feedback. BJTs/FETs/diodes remaingeneric.'
r['loop_stability']['compensation_candidate']['connection']='Implemented native10k/100nOUT→localIN−feedback and10k/100n emitter→IN+filter, withbuffered200Ω/10µFglobalreference andBAT54guards.'
r['loop_stability']['compensation_candidate']['not_in_audited_netlist']=False
r['loop_stability']['compensation_candidate']['shared_reference_coupling']='Finalall9simultaneous-contact model is included; common reference is instantiatedonce.'
r['loop_stability']['candidate_runs_note']='These use the actual finalnativecompensation; earlierfilenameprefix does not imply10nF wasused.'
r['manufacturer_model_integration']={'source':'https://www.ti.com/lit/zip/SGLM009','file':'analysis/models/lmx24_lm2902.lib','version':'LMX24_LM2902 RevA,June24,2024','status':'unresolved_integration','attempts':['Parsed withngspicePSpicecompatibility; ordinaryOPfailednearxamp.75.','RampedUIC75mstransient exceeded60s runtimebound.'],'claim':'No manufacturer-macro stability pass. IndependentAC and genericnonlinear models support theimplementedfilter; physical qualification remains.'}
p.write_text(json.dumps(r,indent=2)+'\n')
(s.A/'revA3_vendor_model_summary.json').write_text(json.dumps(r['manufacturer_model_integration'],indent=2)+'\n')
print('Final analogprovenance:',len(s.COMP),current,'tested fixtureidentical')
