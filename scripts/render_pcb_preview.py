#!/usr/bin/env python3
"""Render native KiCad placement exports into a readable presentation sheet.

The copper/silk geometry is exported directly by KiCad; presentation only
adds a PCB background, the four native NPTH holes, title and stage legend.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
import cairosvg

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pcb'
CLI=os.environ.get('KICAD_CLI') or shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    board=ROOT/'Universal_Poofer_Control.kicad_pcb'
    native=OUT/'placement_native.svg'
    subprocess.run([CLI,'pcb','export','svg',str(board),'--layers','F.Cu,F.SilkS,Edge.Cuts','--mode-single','--page-size-mode','2','--exclude-drawing-sheet','--output',str(native)],check=True)
    subprocess.run([CLI,'pcb','export','svg',str(board),'--layers','F.Fab,F.Cu,Edge.Cuts','--mode-single','--page-size-mode','2','--exclude-drawing-sheet','--black-and-white','--output',str(OUT/'assembly_top.svg')],check=True)
    source=native.read_text()
    body=source[source.index('<g '):source.rindex('</svg>')]
    for old,new in {'#C83434':'#DAB778','#F2EDA1':'#FFF7D5','#FFFFFF':'#0B1916','#D0D2CD':'#769A8B'}.items():body=body.replace(old,new)
    placement=json.loads((ROOT/'analysis/pcb_placement.json').read_text())
    width,height=placement['dimensions_mm']
    canvas_width,canvas_height=width+40,height+43
    holes=''
    for ref,c in placement['positions'].items():
        if ref.startswith('H'):
            x,y=c['x'],c['y']
            holes+=f'<circle cx="{x}" cy="{y}" r="1.6" fill="#101F1B" stroke="#85AA9B" stroke-width="0.15"/>'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}mm" height="{canvas_height}mm" viewBox="0 0 {canvas_width} {canvas_height}">
<rect width="{canvas_width}" height="{canvas_height}" fill="#F6F4EF"/>
<text x="20" y="9" font-family="Arial,sans-serif" font-size="4.2" fill="#142C26" font-weight="bold">UNIVERSAL POOFER CONTROL</text>
<text x="20" y="15" font-family="Arial,sans-serif" font-size="2.6" fill="#557169">ESP32-S3 / eight relay outputs / active-low protected switch inputs</text>
<text x="{width+20}" y="9" text-anchor="end" font-family="Arial,sans-serif" font-size="2.9" fill="#142C26" font-weight="bold">REV A.3</text>
<text x="{width+20}" y="15" text-anchor="end" font-family="Arial,sans-serif" font-size="2.4" fill="#557169">TOP VIEW / PLACEMENT STUDY</text>
<rect x="20.8" y="21.2" width="{width}" height="{height}" rx="1.0" fill="#C9D0C9"/>
<g transform="translate(20,20)"><rect width="{width}" height="{height}" fill="#173E34" stroke="#254D43" stroke-width="0.25"/>{body}{holes}</g>
<text x="20" y="{height+27}" font-family="Arial,sans-serif" font-size="2.6" fill="#142C26">{width:g} x {height:g} mm / 4 layers / 2.54 mm headers / 0.5 mm placement grid</text>
<text x="20" y="{height+33}" font-family="Arial,sans-serif" font-size="2.7" fill="#7D452C" font-weight="bold">NO ROUTING: zero tracks, zero vias, zero copper pours.</text>
<text x="20" y="{height+39}" font-family="Arial,sans-serif" font-size="2.4" fill="#557169">Functional placement remains editable in KiCad. Routing and physical qualification are pending.</text>
</svg>'''
    (OUT/'placement_top.svg').write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(),write_to=str(OUT/'placement_top.png'),output_width=int(canvas_width*10))
    cairosvg.svg2pdf(bytestring=svg.encode(),write_to=str(OUT/'placement_top.pdf'))
    print('Rendered native placement topview PNG, PDF, SVG; assembly SVG.')

if __name__=='__main__':main()
