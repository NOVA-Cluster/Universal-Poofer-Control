#!/usr/bin/env python3
"""Build the deliberately unrouted PCB from the native schematic netlist.

Run with KiCad's bundled Python (pcbnew is version-dependent):
 /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 scripts/build_pcb.py

This builder imports every schematic pin/net/property and sheet UUID, places
functional groups on a 0.5 mm grid, and creates mechanical/RF rule areas.
It intentionally creates no copper tracks, vias, or copper-pour zones.
"""
import argparse
import collections
import json
import math
import os
import re
import sys
import uuid
from pathlib import Path

import wx
APP = wx.App(False)
import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
from pcb_netlist_reader import parse_file,find_all,find_first

FP_CANDIDATES=[Path(os.environ[k]) for k in ['KICAD10_FOOTPRINT_DIR','KICAD9_FOOTPRINT_DIR'] if os.environ.get(k)]
FP_CANDIDATES += [Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'),Path('/usr/share/kicad/footprints'),Path('/usr/local/share/kicad/footprints')]
FP_ROOT=next((path for path in FP_CANDIDATES if path.is_dir()),FP_CANDIDATES[0])
NS = uuid.UUID('a00aeab6-4980-40a2-9dd8-798e042c3ffc')
WIDTH, HEIGHT, GRID = 200.0, 160.0, 0.5

def mm(v): return p.FromMM(float(v))
def v(x, y): return p.VECTOR2I(mm(x), mm(y))
def snap(x): return round(round(float(x) / GRID) * GRID, 5)
def ceilgrid(x): return math.ceil((x - 1e-7) / GRID) * GRID
def uid(s): return p.KIID(str(uuid.uuid5(NS, s)))
def value(node, key, default=''):
    entry = find_first(node, key)
    return entry[1] if entry and len(entry) > 1 else default
def numeric(ref): return (re.sub(r'\d+', '', ref), int(re.search(r'\d+', ref).group()))

def bbox(fp):
    fp.BuildCourtyardCaches()
    shape = fp.GetCourtyard(p.F_CrtYd)
    bb = shape.BBox() if shape.OutlineCount() else fp.GetBoundingBox(False, False)
    return [p.ToMM(bb.GetLeft()), p.ToMM(bb.GetTop()), p.ToMM(bb.GetRight()), p.ToMM(bb.GetBottom())]

def overlaps(a, b, gap=0.4):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])

def read_design(netpath):
    document = parse_file(netpath)
    components = {}
    for c in find_all(find_first(document, 'components'), 'comp'):
        ref = value(c, 'ref')
        props = {}
        for entry in find_all(c, 'property'):
            props[value(entry, 'name')] = value(entry, 'value')
        props['Datasheet']=value(c,'datasheet')
        components[ref] = {'ref': ref, 'value': value(c, 'value'), 'footprint': value(c, 'footprint'), 'properties': props,
                           'sheetpath': value(find_first(c, 'sheetpath'), 'tstamps', '/'),
                           'uuid': value(c, 'tstamps')}
    nets = {}
    mapping = {}
    for n in find_all(find_first(document, 'nets'), 'net'):
        name = value(n, 'name')
        nets[name] = int(value(n, 'code'))
        for node in find_all(n, 'node'):
            mapping[value(node, 'ref'), value(node, 'pin')] = name
    return components, nets, mapping

class Layout:
    def __init__(self, board, footprints, metadata):
        self.board, self.fp, self.meta = board, footprints, metadata
        self.positions, self.occupied, self.groups = {}, [], {}

    def group(self, name):
        if name not in self.groups:
            group = p.PCB_GROUP(self.board)
            group.SetName(name)
            self.board.Add(group)
            self.groups[name] = group
        return self.groups[name]

    def place(self, ref, x, y, angle=0, group=None):
        if ref not in self.fp: return
        if ref in self.positions: raise ValueError('Repeated placement: ' + ref)
        fp = self.fp[ref]
        fp.SetOrientationDegrees(angle)
        fp.SetPosition(v(snap(x), snap(y)))
        bounds = bbox(fp)
        collision=[]
        for name,other in self.occupied:
            if overlaps(bounds,other,0.25):
                a=fp.GetCourtyard(p.F_CrtYd);b=self.fp[name].GetCourtyard(p.F_CrtYd)
                if not a.OutlineCount() or not b.OutlineCount() or a.Collide(b,mm(0.25)):
                    collision.append(name)
        if collision:
            raise ValueError('Courtyard collision placing %s: %s' % (ref, collision))
        rf_antenna=fp.GetFPIDAsString()=='RF_Module:ESP32-S3-WROOM-1'
        if bounds[0] < 1 or (bounds[1] < 0 and not rf_antenna) or bounds[2] > WIDTH - 1 or bounds[3] > HEIGHT - 1:
            raise ValueError('Footprint outside placement envelope: %s %s' % (ref, bounds))
        self.positions[ref] = {'x': snap(x), 'y': snap(y), 'angle': angle, 'group': group or self.meta.get(ref, {}).get('group', 'other'), 'courtyard': bounds}
        self.occupied.append((ref, bounds))
        if group: self.group(group).AddItem(fp)
        fp.SetField('Placement group', self.positions[ref]['group'])
        fp.GetField('Placement group').SetVisible(False)

    def pack(self, refs, region, group, gap=1.0):
        """Order-preserving aligned rows; prefer larger packages before passives."""
        refs = [r for r in refs if r in self.fp and r not in self.positions]
        def area(ref):
            fp=self.fp[ref];fp.SetPosition(v(0,0));fp.SetOrientationDegrees(0)
            b=bbox(fp);return (b[2]-b[0])*(b[3]-b[1])
        refs.sort(key=lambda r: (-round(area(r),2),numeric(r)))
        x0, y0, x1, y1 = region
        for ref in refs:
            fp = self.fp[ref]
            fp.SetOrientationDegrees(0)
            fp.SetPosition(v(0, 0))
            rel = bbox(fp)
            # All package origins remain on the placement grid, including
            # asymmetric footprint origins (headers, DPAK, SOT-223).
            found = None
            for yi in range(int(ceilgrid(y0 - rel[1]) / GRID), int((y1 - rel[3]) / GRID) + 1):
                y = yi * GRID
                for xi in range(int(ceilgrid(x0 - rel[0]) / GRID), int((x1 - rel[2]) / GRID) + 1):
                    x = xi * GRID
                    bounds = [x + rel[0], y + rel[1], x + rel[2], y + rel[3]]
                    if not any(overlaps(bounds, other, gap) for _, other in self.occupied):
                        found = (x, y)
                        break
                if found: break
            if not found: raise ValueError('No space for %s in %s: %s' % (ref, group, region))
            self.place(ref, found[0], found[1], group=group)

    def text(self, text, x, y, size=1, layer=p.F_SilkS, bold=False, justify='left',angle=0):
        item = p.PCB_TEXT(self.board)
        item.SetText(text)
        item.SetPosition(v(x, y))
        item.SetTextSize(v(size, size))
        item.SetTextThickness(mm(max(0.12, size / 7)))
        item.SetLayer(layer)
        item.SetMirrored(layer==p.B_SilkS)
        item.SetBold(bold)
        item.SetTextAngleDegrees(angle)
        item.SetHorizJustify(p.GR_TEXT_H_ALIGN_LEFT if justify == 'left' else p.GR_TEXT_H_ALIGN_CENTER)
        self.board.Add(item)

    def line(self, x1, y1, x2, y2, layer=p.F_SilkS, width=0.15):
        item = p.PCB_SHAPE(self.board)
        item.SetShape(p.SHAPE_T_SEGMENT)
        item.SetStart(v(x1, y1)); item.SetEnd(v(x2, y2))
        item.SetWidth(mm(width)); item.SetLayer(layer)
        self.board.Add(item)

    def rect(self, x1, y1, x2, y2, layer=p.F_SilkS, width=0.15):
        for a, b in [((x1,y1),(x2,y1)),((x2,y1),(x2,y2)),((x2,y2),(x1,y2)),((x1,y2),(x1,y1))]: self.line(*a, *b, layer=layer, width=width)

def import_board(components, nets, mapping):
    board = p.BOARD()
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().m_CopperEdgeClearance = mm(0.5)
    title = board.GetTitleBlock()
    title.SetTitle('Universal Poofer Control / placement study')
    title.SetRevision('A.3')
    title.SetDate('2026-10-03')
    title.SetCompany('Universal Poofer Control')
    netobjects = {}
    for name, code in nets.items():
        ni = p.NETINFO_ITEM(board, name, code)
        board.Add(ni); netobjects[name] = ni
    footprints = {}
    pin_errors = []
    for ref, c in sorted(components.items(), key=lambda x: numeric(x[0])):
        lib, name = c['footprint'].split(':')
        libpath = ROOT / 'Poofer.pretty' if lib == 'Poofer' else FP_ROOT / (lib + '.pretty')
        fp = p.FootprintLoad(str(libpath), name)
        if not fp: raise RuntimeError('Missing footprint ' + c['footprint'])
        fp.SetFPIDAsString(c['footprint'])
        fp.SetReference(ref); fp.SetValue(c['value'])
        fp.SetPath(p.KIID_PATH(c['sheetpath'] + c['uuid']))
        fp.SetSheetname(c['properties'].get('Sheetname', ''))
        fp.SetSheetfile(c['properties'].get('Sheetfile', ''))
        fp.SetFields(c['properties'])
        for field in fp.GetFields():
            field.SetVisible(False)
        # Small references live on the assembly layer so the functional
        # labels and connector pin functions remain legible on silkscreen.
        fp.Reference().SetLayer(p.F_Fab)
        fp.Reference().SetVisible(True)
        fp.Reference().SetTextSize(v(0.7,0.7))
        fp.Reference().SetTextThickness(mm(0.1))
        fp.Value().SetLayer(p.F_Fab)
        fp.Value().SetVisible(False)
        padnums = set()
        for pad in fp.Pads():
            number = pad.GetNumber(); padnums.add(number)
            netname = mapping.get((ref, number))
            if netname: pad.SetNet(netobjects[netname])
        for (checkref, number), name in mapping.items():
            if checkref == ref and number not in padnums: pin_errors.append([ref, number, name])
        board.Add(fp); footprints[ref] = fp
    if pin_errors: raise RuntimeError('Schematic pins missing footprint pads: ' + repr(pin_errors))
    return board, footprints

def mechanical(layout):
    # Lower-left/upper-left holes sit outside the antenna's native keepout.
    for i, (x, y) in enumerate([(5,15),(WIDTH-5,5),(5,HEIGHT-5),(WIDTH-5,HEIGHT-5)], 1):
        fp = p.FootprintLoad(str(FP_ROOT / 'MountingHole.pretty'), 'MountingHole_3.2mm_M3')
        fp.SetFPIDAsString('MountingHole:MountingHole_3.2mm_M3')
        fp.SetReference('H' + str(i)); fp.SetValue('M3 / 3.2mm')
        fp.SetAttributes(fp.GetAttributes() | p.FP_BOARD_ONLY | p.FP_EXCLUDE_FROM_BOM | p.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        layout.board.Add(fp); layout.fp['H' + str(i)] = fp
        layout.place('H' + str(i), x, y, group='Mechanical')
    for i,(x,y) in enumerate([(5,90),(WIDTH-5,20),(WIDTH-5,115)],1):
        fp=p.FootprintLoad(str(FP_ROOT/'Fiducial.pretty'),'Fiducial_1mm_Mask2mm')
        fp.SetFPIDAsString('Fiducial:Fiducial_1mm_Mask2mm')
        fp.SetReference('FID'+str(i));fp.SetValue('1mm Cu / 2mm mask')
        fp.SetAttributes(fp.GetAttributes()|p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
        layout.board.Add(fp);layout.fp['FID'+str(i)]=fp
        layout.place('FID'+str(i),x,y,group='Mechanical')
    layout.rect(0,0,WIDTH,HEIGHT,p.Edge_Cuts,0.05)
    layout.text('%g x %g mm | 4 layers | 1.6 mm | 0.5 mm placement grid'%(WIDTH,HEIGHT),8,HEIGHT+7,1.1,p.Dwgs_User)
    layout.text('PLACEMENT ONLY - NO ROUTING - NOT FOR FABRICATION',8,HEIGHT+11,1.2,p.Dwgs_User,True)

def configure_project(nets,write_project=False,mapping=None):
    path = ROOT / 'Universal_Poofer_Control.kicad_pro'
    data = json.loads(path.read_text())
    def nc(name, clearance, width, desc):
        return {'name':name,'clearance':clearance,'track_width':width,'via_diameter':0.7,'via_drill':0.3,'microvia_diameter':0.3,'microvia_drill':0.1,'diff_pair_width':0.2,'diff_pair_gap':0.2,'diff_pair_via_gap':0.25,'wire_width':6,'bus_width':12,'line_style':0,'pcb_color':'rgba(0, 0, 0, 0.000)','schematic_color':'rgba(0, 0, 0, 0.000)','description':desc}
    classes = [nc('Default',0.25,0.25,'3.3V logic and protected signals'),nc('HV_Field',0.6,0.4,'Continuous +/-100V input fault domains; 0.6mm minimum clearance'),nc('Valve_1A',0.5,1.0,'12VDC valve contact domains, 1A continuous design target'),nc('Coil_12V',0.25,0.6,'Relay coils and hardware switched coil supply'),nc('Power',0.25,0.6,'5V and 3.3V logic power; master wetting current total up to180mA')]
    hv_domains={}
    hv_basis=[]
    if mapping:
        for channel in range(1,10):
            domain='IN%d'%channel if channel<9 else 'ESTOP'
            rb=1000+(channel-1)*30
            points=[('Q%d'%(100+channel),'2','HV PNP collector after source reverse-block diode'),
                    ('D%d'%(120+channel),'1','Negative-fault branch diode endpoint'),
                    ('R%d'%(rb+4),'2','Negative-fault divider intermediate1'),
                    ('R%d'%(rb+5),'2','Negative-fault divider intermediate2'),
                    ('D%d'%(110+channel),'3','Positive-fault branch after reverse-block diode'),
                    ('R%d'%(rb+14),'2','Positive-fault divider intermediate1'),
                    ('R%d'%(rb+15),'2','Positive-fault divider intermediate2')]
            names={domain+'_FIELD'}
            if channel==9:names.add('ESTOP_CHAIN_OUT')
            for ref,pin,reason in points:
                name=mapping.get((ref,pin))
                if name:
                    names.add(name);hv_basis.append({'domain':domain,'ref':ref,'pin':pin,'net':name,'basis':reason})
            hv_domains[domain]=sorted(name for name in names if name in nets)
    else:
        hv_domains={('IN%d'%i):['IN%d_FIELD'%i]for i in range(1,9)}
        hv_domains['ESTOP']=['ESTOP_FIELD']
    hv_names={name for names in hv_domains.values()for name in names}
    assignments = []
    for name in nets:
        kind = 'Default'
        if name in hv_names: kind='HV_Field'
        elif re.search(r'(CONTACT|VALVE|RLY[1-8]_(COM|NO|NC|RETURN)|OUT[1-8]_(COM|NO|NC|RETURN))',name): kind='Valve_1A'
        elif re.search(r'(12V|COIL|DRAIN)',name): kind='Coil_12V'
        elif name in ['+5V_LOGIC','+3V3','+5V','5V_WETTING']: kind='Power'
        assignments.append({'netclass':kind,'pattern':name})
    net_settings={'meta':{'version':4},'classes':classes,'netclass_assignments':{},'netclass_patterns':assignments}
    settings={}
    rules=settings.setdefault('rules', {})
    rules.update({'min_clearance':0.2,'min_track_width':0.2,'min_via_diameter':0.6,'min_through_hole_diameter':0.2,'min_hole_clearance':0.25,'min_hole_to_hole':0.25,'min_copper_edge_clearance':0.5})
    proposal={'net_settings':net_settings,'board':{'design_settings':settings},'basis':{'fabricator_capabilities':'https://jlcpcb.com/capabilities/pcb-capabilities/','custom_rule_syntax':'https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#custom-design-rules','note':'0.6mm field-to-other clearance;1.25mm between different raw field nets for simultaneous +100V/-100V faults. Functional fault tolerance spacing; no safety isolation claim.'}}
    (ROOT/'analysis/pcb_setup_proposal.json').write_text(json.dumps(proposal,indent=2)+'\n')
    if write_project:
        data['net_settings']=net_settings
        data.setdefault('board',{}).setdefault('design_settings',{}).setdefault('rules',{}).update(rules)
        path.write_text(json.dumps(data,indent=2)+'\n')
    (ROOT/'analysis/pcb_hv_node_classification.json').write_text(json.dumps({'domains':hv_domains,'pin_evidence':hv_basis,'basis':'Explicit physical pin/net maps: high-voltage PNP collector and early fault-divider nodes. Protected SENSE/reference/MCU nodes stay in logic classes.'},indent=2)+'\n')
    def condition(obj,names):return '('+' || '.join("%s.NetName == '%s'"%(obj,name) for name in names)+')'
    rules_text='(version 1)\n# Different input domains can differ by200V under simultaneous+100V/-100V faults.\n'
    domain_names=sorted(hv_domains)
    for i,a in enumerate(domain_names):
        for b in domain_names[i+1:]:
            if not hv_domains[a] or not hv_domains[b]:continue
            rule_condition='('+condition('A',hv_domains[a])+' && '+condition('B',hv_domains[b])+') || ('+condition('A',hv_domains[b])+' && '+condition('B',hv_domains[a])+')'
            rules_text+='(rule '+json.dumps('Fault domains '+a+' / '+b+':200V')+'\n  (condition '+json.dumps(rule_condition)+')\n  (constraint clearance (min 1.25mm))\n)\n'
    (ROOT/'Universal_Poofer_Control.kicad_dru').write_text(rules_text)

def summarize(layout, components, nets, mapping):
    mismatches=[]
    for ref,c in components.items():
        for pad in layout.fp[ref].Pads():
            num=pad.GetNumber(); expected=mapping.get((ref,num),'')
            actual=pad.GetNetname()
            if actual!=expected: mismatches.append({'ref':ref,'pad':num,'expected':expected,'actual':actual})
    native_zones=[z for z in layout.board.Zones()]
    footprint_zones=[z for f in layout.board.GetFootprints() for z in f.Zones()]
    result={'stage':'unrouted placement study','revision':'A.3','dimensions_mm':[WIDTH,HEIGHT],'copper_layers':4,'placement_grid_mm':GRID,'schematic_footprints':len(components),'mechanical_footprints':4,'fiducials':3,'schematic_nets':len(nets),'tracks':len(list(layout.board.GetTracks())),'vias':sum(isinstance(t,p.PCB_VIA) for t in layout.board.GetTracks()),'copper_pour_zones':sum(not z.GetIsRuleArea() for z in native_zones+footprint_zones),'rule_areas':sum(z.GetIsRuleArea() for z in native_zones+footprint_zones),'pad_net_mismatches':mismatches,'positions':layout.positions,'notes':['All ratsnest/unconnected nets are intentional at this placement-only stage.','Routing, planes, return paths, thermal copper, solder mask and final current/creepage qualification are pending.','Native ESP32 module antenna rule area forbids copper/tracks/vias/pads/footprints on all layers.','All footprint origins use a0.5mm grid; native internal pad pitch retains manufacturer dimensions.']}
    (ROOT/'analysis/pcb_placement.json').write_text(json.dumps(result,indent=2)+'\n')
    if mismatches:raise RuntimeError('Pad/net mismatch')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--netlist',default=str(ROOT/'analysis/Universal_Poofer_Control.net'))
    parser.add_argument('--no-project',action='store_true',help='Compatibility alias:project writes are disabled by default.')
    parser.add_argument('--write-project',action='store_true',help='Merge only proposed PCB rules/netclasses into existing project;ERC and schematic settings are preserved.')
    args=parser.parse_args()
    project_path=ROOT/'Universal_Poofer_Control.kicad_pro'
    project_source=project_path.read_text() if project_path.exists() else None
    p.KIID.SeedGenerator(8321139)
    components,nets,mapping=read_design(Path(args.netlist))
    meta={c['ref']:c for c in json.loads((ROOT/'bom/design-components.json').read_text())}
    board,footprints=import_board(components,nets,mapping)
    layout=Layout(board,footprints,meta)
    mechanical(layout)
    # layout_groups is kept independently reviewable from the import logic.
    from pcb_placement_plan import layout_groups
    layout_groups(layout,meta,mapping)
    missing=set(components)-set(layout.positions)
    if missing: raise RuntimeError('Unplaced schematic components: '+repr(sorted(missing,key=numeric)))
    board.BuildListOfNets()
    p.SaveBoard(str(ROOT/'Universal_Poofer_Control.kicad_pcb'),board)
    # pcbnew.SaveBoard also writes a default .kicad_pro for a freshly
    # constructed BOARD. Restore the caller's exact project before merging
    # optional PCB rules so schematic/ERC configuration is not discarded.
    if project_source is not None:project_path.write_text(project_source)
    configure_project(nets,write_project=args.write_project and not args.no_project,mapping=mapping)
    result=summarize(layout,components,nets,mapping)
    print(json.dumps({k:result[k] for k in ['dimensions_mm','schematic_footprints','tracks','vias','copper_pour_zones','rule_areas','pad_net_mismatches']},indent=2))

if __name__=='__main__':main()
