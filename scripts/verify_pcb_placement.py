#!/usr/bin/env python3
"""Independently reload the saved native board and check placement-stage scope.

Uses KiCad's bundled Python, as build_pcb.py does. Native DRC is run
separately: this check covers complete source/pad parity, the placement
grid and the deliberate absence of routing after serialization/reload.
"""
import itertools
import json
import math
import re
from pathlib import Path
from build_pcb import ROOT, read_design, bbox, overlaps, mm, GRID, WIDTH, HEIGHT
import pcbnew as p

def main():
    board=p.LoadBoard(str(ROOT/'Universal_Poofer_Control.kicad_pcb'))
    components,nets,mapping=read_design(ROOT/'analysis/Universal_Poofer_Control.net')
    actual=list(board.GetFootprints())
    references=[fp.GetReference() for fp in actual]
    duplicate_refs=sorted({ref for ref in references if references.count(ref)>1})
    fpmap={fp.GetReference():fp for fp in actual}
    missing=sorted(set(components)-set(fpmap))
    extras=sorted(set(fpmap)-set(components))
    undeclared_extras=[ref for ref in extras if not fpmap[ref].GetAttributes()&p.FP_BOARD_ONLY]
    mismatches=[]
    source_pnp_shorts=[]
    monitor_isolation=[]
    for ref,c in components.items():
        if ref not in fpmap:continue
        fp=fpmap[ref]
        if fp.GetFPIDAsString()!=c['footprint']:mismatches.append({'ref':ref,'field':'Footprint','expected':c['footprint'],'actual':fp.GetFPIDAsString()})
        if fp.GetValue()!=c['value']:mismatches.append({'ref':ref,'field':'Value','expected':c['value'],'actual':fp.GetValue()})
        pad_numbers=set()
        for pad in fp.Pads():
            n=pad.GetNumber();pad_numbers.add(n)
            expected=mapping.get((ref,n),'')
            if pad.GetNetname()!=expected:mismatches.append({'ref':ref,'pad':n,'expected':expected,'actual':pad.GetNetname()})
        for (expected_ref,n),net in mapping.items():
            if expected_ref==ref and n not in pad_numbers:mismatches.append({'ref':ref,'missing_pad':n,'net':net})
        if 'MJD350' in c['value'] or 'MJD350' in c['properties'].get('MPN',''):
            collector=mapping.get((ref,'2'));emitter=mapping.get((ref,'3'))
            if collector and collector==emitter:source_pnp_shorts.append({'ref':ref,'collector_pin':'2','emitter_pin':'3','shorted_net':collector})
    off_grid=[]
    undersized_passives=[]
    for pin,hw,resistor in [('10','SAFE_PERMIT','R4'),('23','HW_RUN_LATCH','R5')]:
        monitor=mapping.get(('U1',pin))
        ends={mapping.get((resistor,'1')),mapping.get((resistor,'2'))}
        ok=bool(monitor) and monitor!=hw and ends=={monitor,hw}
        monitor_isolation.append({'mcu_pin':pin,'hardware_net':hw,'monitor_net':monitor,'series_resistor':resistor,'isolated':ok})
    debug_oe=mapping.get(('J5','9'))
    debug_oe_ends={mapping.get(('R136','1')),mapping.get(('R136','2'))}
    debug_oe_isolated=bool(debug_oe) and debug_oe!='RLY_OE_ACTUAL_N' and debug_oe_ends=={debug_oe,'RLY_OE_ACTUAL_N'}
    for fp in actual:
        xy=[p.ToMM(fp.GetPosition().x),p.ToMM(fp.GetPosition().y)]
        if any(abs(x/GRID-round(x/GRID))>1e-6 for x in xy):off_grid.append({'ref':fp.GetReference(),'xy':xy})
        if fp.GetReference().startswith(('R','C')):
            match=re.search(r'_(\d{4})_',fp.GetFPIDAsString())
            if match and int(match.group(1))<805:undersized_passives.append({'ref':fp.GetReference(),'footprint':fp.GetFPIDAsString()})
    courtyards={fp.GetReference():bbox(fp) for fp in actual}
    collisions=[]
    close_courtyards=[]
    for a,b in itertools.combinations(actual,2):
        if overlaps(courtyards[a.GetReference()],courtyards[b.GetReference()],0):
            ashape=a.GetCourtyard(p.F_CrtYd);bshape=b.GetCourtyard(p.F_CrtYd)
            if ashape.OutlineCount() and bshape.OutlineCount() and ashape.Collide(bshape,0):collisions.append([a.GetReference(),b.GetReference()])
        if overlaps(courtyards[a.GetReference()],courtyards[b.GetReference()],1):
            ashape=a.GetCourtyard(p.F_CrtYd);bshape=b.GetCourtyard(p.F_CrtYd)
            if ashape.OutlineCount() and bshape.OutlineCount() and ashape.Collide(bshape,mm(1)):
                close_courtyards.append([a.GetReference(),b.GetReference()])
    all_zones=list(board.Zones())+[z for fp in actual for z in fp.Zones()]
    rule_areas=[z for z in all_zones if z.GetIsRuleArea()]
    copper_zones=[z for z in all_zones if not z.GetIsRuleArea()]
    tracks=list(board.GetTracks())
    outline=[d for d in board.GetDrawings() if d.GetLayer()==p.Edge_Cuts]
    endpoints=[]
    for d in outline:
        endpoints.extend([(d.GetStart().x,d.GetStart().y),(d.GetEnd().x,d.GetEnd().y)])
    closed=len(outline)==4 and len(set(endpoints))==4 and all(endpoints.count(point)==2 for point in set(endpoints))
    antenna=[z for z in fpmap['U1'].Zones() if z.GetIsRuleArea()]
    antenna_complete=bool(antenna) and all(z.GetDoNotAllowTracks() and z.GetDoNotAllowVias() and z.GetDoNotAllowPads() and z.GetDoNotAllowZoneFills() and z.GetDoNotAllowFootprints() for z in antenna)
    decoupling=[]
    pairs=[('U1','C5','2'),('U3','C7','16'),('U4','C8','16'),('U5','C9','16'),
           ('U10','C80','3'),('U11','C81','3'),('U12','C82','3'),('U13','C83','3'),('U14','C84','3'),
           ('U20','C90','4'),('U21','C91','4'),('U22','C92','4'),
           ('U30','C110','14'),('U31','C111','14'),('U32','C112','14'),('U34','C113','14'),
           ('U35','C154','8'),('U40','C40','3'),('U50','C70','20'),('U51','C71','20'),('U52','C72','20'),
           ('U54','C74','1'),('U54','C75','8')]
    for ic,cap,pin in pairs:
        if ic not in fpmap or cap not in fpmap:continue
        a=next((pad for pad in fpmap[ic].Pads() if pad.GetNumber()==pin),None)
        c=next((pad for pad in fpmap[cap].Pads() if pad.GetNumber()=='1'),None)
        if not a or not c:continue
        av,cv=a.GetPosition(),c.GetPosition()
        centre=math.hypot(p.ToMM(av.x-cv.x),p.ToMM(av.y-cv.y))
        ab,cb=a.GetBoundingBox(),c.GetBoundingBox()
        dx=max(0,ab.GetLeft()-cb.GetRight(),cb.GetLeft()-ab.GetRight())
        dy=max(0,ab.GetTop()-cb.GetBottom(),cb.GetTop()-ab.GetBottom())
        edge=math.hypot(p.ToMM(dx),p.ToMM(dy))
        decoupling.append({'ic':ic,'vcc_pin':pin,'cap':cap,'vcc_net':a.GetNetname(),'cap_supply_net':c.GetNetname(),'same_net':a.GetNetname()==c.GetNetname(),'pad_centres_mm':round(centre,3),'pad_edges_mm':round(edge,3),'basis':'Actual native copper-pad positions/bounds. Edge distance is a shortest-route opportunity; routing/return loop are still pending.'})
    (ROOT/'analysis/pcb_decoupling_placement.json').write_text(json.dumps({'decoupling_pairs':decoupling,'stage':'unrouted; geometry only'},indent=2)+'\n')
    input_filters=[]
    for channel in range(1,10):
        ic='U20' if channel<=4 else 'U21' if channel<=8 else 'U22'
        pin=['3','5','10','12'][(channel-1)%4]
        cap='C%d'%(140+channel);res='R%d'%(1024+(channel-1)*30)
        if ic not in fpmap or cap not in fpmap or res not in fpmap:continue
        a=next(pad for pad in fpmap[ic].Pads() if pad.GetNumber()==pin)
        c=next(pad for pad in fpmap[cap].Pads() if pad.GetNumber()=='1')
        ab,cb=a.GetBoundingBox(),c.GetBoundingBox()
        dx=max(0,ab.GetLeft()-cb.GetRight(),cb.GetLeft()-ab.GetRight())
        dy=max(0,ab.GetTop()-cb.GetBottom(),cb.GetTop()-ab.GetBottom())
        edge=math.hypot(p.ToMM(dx),p.ToMM(dy))
        centre=math.hypot(p.ToMM(a.GetPosition().x-c.GetPosition().x),p.ToMM(a.GetPosition().y-c.GetPosition().y))
        ends={pad.GetNetname()for pad in fpmap[res].Pads()}
        filtered=a.GetNetname()
        input_filters.append({'channel':channel,'opamp':ic,'in_plus_pin':pin,'series_resistor':res,'local_capacitor':cap,'filtered_net':filtered,'same_filtered_node':filtered==c.GetNetname() and filtered in ends,'pad_centres_mm':round(centre,3),'pad_edges_mm':round(edge,3),'basis':'Actual native IN+ and local RC-filter capacitor pads. No trace routing exists yet.'})
    (ROOT/'analysis/pcb_input_filter_placement.json').write_text(json.dumps({'input_filters':input_filters,'stage':'unrouted; local filtered-node placement'},indent=2)+'\n')
    uv_absorbers=[]
    for channel in range(1,10):
        transistor='Q%d'%(120+channel);cap='C%d'%(160+channel)
        if transistor not in fpmap or cap not in fpmap:continue
        a=next(pad for pad in fpmap[transistor].Pads() if pad.GetNumber()=='2')
        c=next(pad for pad in fpmap[cap].Pads() if pad.GetNumber()=='1')
        g=next(pad for pad in fpmap[cap].Pads() if pad.GetNumber()=='2')
        ab,cb=a.GetBoundingBox(),c.GetBoundingBox()
        dx=max(0,ab.GetLeft()-cb.GetRight(),cb.GetLeft()-ab.GetRight())
        dy=max(0,ab.GetTop()-cb.GetBottom(),cb.GetTop()-ab.GetBottom())
        uv_absorbers.append({'channel':channel,'transistor':transistor,'emitter_pin':'2','absorber_capacitor':cap,'emitter_net':a.GetNetname(),'same_emitter_node':a.GetNetname()==c.GetNetname(),'ground_return':g.GetNetname()=='GND','pad_edges_mm':round(math.hypot(p.ToMM(dx),p.ToMM(dy)),3),'basis':'Actual native emitter/absorber pad geometry; capacitors sit beside the detector, before routing.'})
    (ROOT/'analysis/pcb_uv_absorber_placement.json').write_text(json.dumps({'uv_absorbers':uv_absorbers,'stage':'unrouted; local fault-step absorber placement'},indent=2)+'\n')
    result={'stage':'placement only / deliberately unrouted','native_board_reloaded':True,'schematic_components':len(components),'pcb_footprints':len(actual),'board_only_footprints':extras,'duplicate_refs':duplicate_refs,'missing_schematic_components':missing,'undeclared_board_only_footprints':undeclared_extras,'pad_and_component_mismatches':mismatches,'off_grid_components':off_grid,'placement_grid_mm':GRID,'courtyard_collisions':collisions,'closed_rectangular_outline':closed,'dimensions_mm':[WIDTH,HEIGHT],'track_count':len(tracks),'via_count':sum(isinstance(t,p.PCB_VIA) for t in tracks),'copper_pour_zone_count':len(copper_zones),'rule_area_count':len(rule_areas),'native_antenna_keepout_enforced':antenna_complete,'validation_basis':['Native board reloaded through pcbnew; all imported pad nets compared with KiCad schematic netlist.','Actual native courtyard polygons checked, including the ESP module L-shaped RF courtyard.','Native footprint antenna rule area inspected, which the generic PCB analyzer does not include in its top-level keepout list.','Native DRC and schematic parity run separately; unconnected items are expected at this stage.']}
    result['passed']=not(duplicate_refs or missing or undeclared_extras or mismatches or off_grid or collisions or tracks or copper_zones) and closed and antenna_complete
    result['source_pnp_collector_emitter_shorts']=source_pnp_shorts
    result['hardware_status_monitor_isolation']=monitor_isolation
    result['debug_oe_monitor_isolation']={'header':'J5','pin':'9','monitor_net':debug_oe,'series_resistor':'R136','isolated':debug_oe_isolated}
    result['undersized_passives']=undersized_passives
    result['courtyard_spacing_under_1mm']=close_courtyards
    result['decoupling_pairs']=decoupling
    result['local_opamp_input_filters']=input_filters
    result['local_uv_emitter_absorbers']=uv_absorbers
    result['passed']=result['passed'] and not source_pnp_shorts and not undersized_passives and all(item['isolated'] for item in monitor_isolation)
    result['passed']=result['passed'] and debug_oe_isolated
    result['passed']=result['passed'] and all(item['same_filtered_node'] for item in input_filters)
    result['passed']=result['passed'] and all(item['same_emitter_node'] and item['ground_return'] for item in uv_absorbers)
    (ROOT/'analysis/pcb_placement_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
