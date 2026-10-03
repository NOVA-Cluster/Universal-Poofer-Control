#!/usr/bin/env python3
"""Export exact native schematic-component selections into JLC and sourcing CSVs."""
import csv,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'bom'
parts=json.loads((B/'parts.json').read_text());design=json.loads((B/'design-components.json').read_text());groups=collections.defaultdict(list)
for c in design:groups[c['code']].append(c)
with (B/'JLCPCB_BOM.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['Comment','Designator','Footprint','LCSC Part #'])
    for code,cs in sorted(groups.items()):w.writerow([parts[code]['mpn'],','.join(c['ref'] for c in cs),cs[0]['footprint'],code])
with (B/'assembly_availability.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['LCSC','MPN','Manufacturer','Package','Qty/board','JLC Class','Assembly stock','Checked','Source','Datasheet','Notes'])
    for code,cs in sorted(groups.items()):
        p=parts[code];w.writerow([code,p['mpn'],p['manufacturer'],p['package'],len(cs),'Basic' if p['is_basic'] else 'Extended',p['stock'],p['checked_date'],p['assembly_inventory_source'],p['datasheet_url'],' | '.join(sorted({c['notes'] for c in cs if c['notes']}))])
rows=list(csv.DictReader((B/'bom.csv').open()))
for r in rows:r['LC_Stock']=str(parts[r['LCSC']]['stock']);r['Chosen_Distributor']='LCSC';r['Validated']='Package/pin-map checked; prototype pending'
with (B/'bom.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
assert sum(int(r['Qty']) for r in rows)==len(design)
print('BOM:',len(groups),'types;',len(design),'components;',sum(parts[c]['is_basic'] for c in groups),'Basic types')
