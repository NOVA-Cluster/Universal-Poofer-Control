#!/usr/bin/env python3
"""Check the electrical contract in the authoritative KiCad-exported netlist.

This is connectivity validation, not physical or safety certification.
"""
import json
from pathlib import Path
from pcb_netlist_reader import parse_file, find_first, find_all

ROOT = Path(__file__).resolve().parents[1]
raw = parse_file(ROOT / 'analysis/Universal_Poofer_Control.net')
nodes = {}
for net in find_all(find_first(raw, 'nets'), 'net'):
    name = find_first(net, 'name')[1]
    for node in find_all(net, 'node'):
        nodes[(find_first(node, 'ref')[1], find_first(node, 'pin')[1])] = name
checks = []

def check(label, result):
    checks.append({'check': label, 'pass': bool(result)})

def net(ref, pin):
    return nodes.get((ref, str(pin)))

def equal(label, *pins):
    values = [net(*p) for p in pins]
    check(label, values[0] is not None and len(set(values)) == 1)

def named(ref, pin, name):
    check(f'{ref}.{pin} = {name}', net(ref, pin) == name)

meta = json.loads((ROOT / 'bom/design-components.json').read_text())
parts = json.loads((ROOT / 'bom/parts.json').read_text())
refs = [c['ref'] for c in meta]
native_refs = [find_first(c, 'ref')[1] for c in find_all(find_first(raw, 'components'), 'comp')]
check('Unique physical references', len(refs) == len(set(refs)))
check('Native physical references match metadata', set(refs) == set(native_refs))
for c in meta:
    if c['ref'][0] in 'RC':
        check(f"{c['ref']} minimum 0805", '_0805_2012Metric' in c['footprint'])
    check(f"{c['ref']} assembly inventory", parts[c['code']].get('stock', 0) >= 5)
    check(f"{c['ref']} exact MPN", bool(parts[c['code']].get('mpn')))
check('No small-pitch active footprints', not any('TSSOP' in c['footprint'] or 'QFN' in c['footprint'] for c in meta))

op = [(2, 3, 1), (6, 5, 7), (9, 10, 8), (13, 12, 14)]
cp = [(4, 5, 2), (6, 7, 1), (10, 11, 13), (8, 9, 14)]
for ch in range(1, 10):
    rb = 1000 + (ch - 1) * 30
    q, dv, uv, pm = f'Q{100+ch}', f'Q{110+ch}', f'Q{120+ch}', f'Q{130+ch}'
    amp = 'U20' if ch <= 4 else 'U21' if ch <= 8 else 'U22'
    mi, pl, out = op[(ch - 1) % 4]
    field = 'ESTOP_FIELD' if ch == 9 else f'IN{ch}_FIELD'
    equal(f'Input {ch} emitter and shunt', (q, 3), (f'R{rb}', 2), (f'R{rb+24}', 1))
    equal(f'Input {ch} filtered emitter feedback', (f'R{rb+24}', 2), (amp, pl), (f'C{140+ch}', 1))
    named(f'C{140+ch}', 2, 'GND')
    check(f'Input {ch} PNP terminals distinct', len({net(q, p) for p in (1, 2, 3)}) == 3)
    equal(f'Input {ch} blocker anode', (q, 2), (f'D{100+ch}', 1))
    named(f'D{100+ch}', 3, field)
    equal(f'Input {ch} driver collector resistor', (q, 1), (f'R{rb+2}', 1), (pm, 3))
    equal(f'Input {ch} driver collector', (dv, 3), (f'R{rb+2}', 2))
    named(f'R{rb+3}', 1, '+5V_LOGIC')
    equal(f'Input {ch} base pullup', (q, 1), (f'R{rb+3}', 2))
    equal(f'Input {ch} compensated output', (amp, out), (f'C{130+ch}', 1))
    equal(f'Input {ch} private compensation node', (amp, mi), (f'C{130+ch}', 2), (f'R{rb+21}', 2), (f'D{140+ch}', 3))
    named(f'R{rb+21}', 1, 'CURRENT_REF')
    named(f'D{140+ch}', 1, 'CURRENT_REF')
    named(dv, 2, 'GND')
    equal(f'Input {ch} independent UV clamp', (uv, 3), (pm, 1))
    equal(f'Input {ch} UV charge-absorption capacitor', (uv, 2), (f'C{160+ch}', 1))
    named(f'C{160+ch}', 2, 'GND')
    named(pm, 2, '+5V_LOGIC')
    equal(f'Input {ch} early negative flag', (uv, 2), (f'R{rb+9}', 1))
    equal(f'Input {ch} UV attenuator grounds', (f'R{rb+11}', 2), (f'R{rb+12}', 2))
    named(f'R{rb+11}', 2, 'GND')
    if ch < 9:
        named(f'J{10+ch}', 1, field)
        named(f'J{10+ch}', 2, 'GND')

equal('Reference buffer negative feedback', ('U22', 6), ('U22', 7), ('R66', 1))
named('U22', 5, 'CURRENT_REF_RAW')
equal('Reference buffer resistor chain', ('R66', 2), ('R67', 1))
equal('Reference hold capacitor', ('R67', 2), ('C66', 1))
named('C66', 1, 'CURRENT_REF')

for ch in range(1, 9):
    equal(f'Valve {ch} coil drain', (f'K{ch}', 2), (f'Q{ch}', 3), (f'D{10+ch}', 2))
    named(f'K{ch}', 5, '+12V_COIL_SAFE')
    equal(f'Valve {ch} coil opposing cathodes', (f'D{10+ch}', 1), (f'D{20+ch}', 1))
    named(f'D{20+ch}', 2, '+12V_COIL_SAFE')
    equal(f'Valve {ch} load opposing cathodes', (f'D{30+ch}', 1), (f'D{40+ch}', 1))
    named(f'D{30+ch}', 2, f'VALVE{ch}_RETURN')
    named(f'D{40+ch}', 2, f'VALVE{ch}_NO')
    for kp, jp in [(1, 1), (4, 2), (3, 3)]:
        equal(f'Valve {ch} contact mapping {kp}', (f'K{ch}', kp), (f'J{30+ch}', jp))
    equal(f'Valve {ch} NO connector', (f'K{ch}', 4), (f'J{40+ch}', 1))

named('U40', 1, 'GND'); named('U40', 2, 'PG_RESET_N'); named('U40', 3, '+3V3')
named('Q40', 2, '+12V_IN'); named('Q40', 3, '+12V_COIL_SAFE')
equal('Coil gate arm and power-good transistors in series', ('Q41', 2), ('Q42', 3))
named('Q42', 2, 'GND')
named('U34', 1, 'RUN_CLEAR_N'); named('U34', 2, '+3V3')
named('U34', 3, 'ARM_LEVEL'); named('U34', 4, '+3V3'); named('U34', 5, 'HW_RUN_LATCH')
named('U35', 8, '+3V3'); named('U35', 4, 'GND')
named('U35', 1, 'RUN_CLEAR_N'); named('U35', 7, 'RUN_CLEAR_N')
named('U35', 2, 'RAIL_UV_REF'); named('U35', 6, 'RAIL_UV_REF')
equal('Raw12 rail monitor divider', ('U35', 3), ('R152', 2), ('R153', 1))
equal('Logic5 rail monitor parallel divider', ('U35', 5), ('R154', 2), ('R158', 2), ('R155', 1))
named('U3', 13, 'RLY_OE_ACTUAL_N')
named('U52', 15, 'RLY_OE_ACTUAL_N')
named('J5', 9, 'OE_MONITOR_N')
check('Debug OE monitor isolation', {net('R136', 1), net('R136', 2)} == {'RLY_OE_ACTUAL_N', 'OE_MONITOR_N'})
for monitor, gpio_pin, res, hard in [('ESTOP_SAFE_MON_GPIO18', 10, 'R4', 'SAFE_PERMIT'), ('HW_RUN_MON_GPIO21', 23, 'R5', 'HW_RUN_LATCH'), ('ROLE_GPIO2_MON', 38, 'R71', 'LOCAL_MASTER_N')]:
    named('U1', gpio_pin, monitor)
    check(f'{monitor} protected series path', {net(res, 1), net(res, 2)} == {monitor, hard})

for j in ['J20', 'J21']:
    named(j, 15, 'I2C_SDA_BUS'); named(j, 16, 'I2C_SCL_BUS')
    check(f'{j} independent module power', not any(str(net(j, p)).startswith('+') for p in range(1, 17)))
for p, n in [(1, '+3V3'), (8, '+3V3'), (4, 'GND'), (5, 'PG_RESET_N'), (2, 'I2C_SCL_BUS'), (3, 'I2C_SDA_BUS'), (7, 'I2C_SCL_GPIO9'), (6, 'I2C_SDA_GPIO8')]:
    named('U54', p, n)
check('I2C A shared / B private', net('U54', 2) != net('U54', 7) and net('U54', 3) != net('U54', 6))
named('R127', 1, '+3V3'); named('R127', 2, 'UP_ARM_N')
named('R133', 1, '+3V3'); named('R133', 2, 'MCU_INHIBIT_N_GPIO15')
for ref in ['R65', 'R137', 'R138', 'R139']:
    named(ref, 1, '+5V_LOGIC'); named(ref, 2, 'GND')
named('R140', 1, '+3V3'); named('R140', 2, 'GND')

result = {'revision': 'A.3', 'scope': 'Raw native netlist connectivity and package/inventory snapshot only', 'checks': len(checks), 'failed': [c for c in checks if not c['pass']], 'pass': all(c['pass'] for c in checks), 'physical_components': len(meta), 'results': checks}
(ROOT / 'analysis/validation-A3.json').write_text(json.dumps(result, indent=2))
print(json.dumps({k: result[k] for k in ['checks', 'physical_components', 'pass', 'failed']}, indent=2))
raise SystemExit(0 if result['pass'] else 1)
