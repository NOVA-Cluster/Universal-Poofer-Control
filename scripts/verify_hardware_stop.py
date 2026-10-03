#!/usr/bin/env python3
"""Native-netlist hardware-stop audit; no analogue timing or safety certification.

Run: python3 scripts/verify_hardware_stop.py --self-test
The default netlist/output are relative to the project containing this script.
Gate/FF pin functions come from manufacturer tables, not KiCad symbol graphics.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
import sys

from pcb_netlist_reader import parse_file, find_all, find_first

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "74HC00": "https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf",
    "74HC02": "https://assets.nexperia.com/documents/data-sheet/74HC_HCT02.pdf",
    "74HC14": "https://assets.nexperia.com/documents/data-sheet/74HC_HCT14.pdf",
    "74HC32": "https://assets.nexperia.com/documents/data-sheet/74HC_HCT32.pdf",
    "74HC74": "https://assets.nexperia.com/documents/data-sheet/74HC_HCT74.pdf",
    "SN74LVC244A": "https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf",
    "TLV9022": "https://www.ti.com/lit/ds/symlink/tlv9022.pdf",
}
PIN_MAPS = {
    "74HC00": ("NAND", [((1, 2), 3), ((4, 5), 6), ((9, 10), 8), ((12, 13), 11)]),
    "74HC02": ("NOR", [((2, 3), 1), ((5, 6), 4), ((8, 9), 10), ((11, 12), 13)]),
    "74HC32": ("OR", [((1, 2), 3), ((4, 5), 6), ((9, 10), 8), ((12, 13), 11)]),
    "74HC14": ("NOT", [((1,), 2), ((3,), 4), ((5,), 6), ((9,), 8), ((11,), 10), ((13,), 12)]),
}
BUFFER_PINS = [(2, 18, 1), (4, 16, 1), (6, 14, 1), (8, 12, 1),
               (17, 3, 19), (15, 5, 19), (13, 7, 19), (11, 9, 19)]


def child(node, key, default=None):
    item = find_first(node, key)
    return item[1] if item and len(item) > 1 else default


def base(net):
    return net.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Gate:
    ref: str
    unit: int
    family: str
    kind: str
    input_pins: tuple[int, ...]
    output_pin: int
    inputs: tuple[str, ...]
    output: str

    def evaluate(self, values):
        inputs = [bool(values[n]) for n in self.inputs]
        return {"NAND": lambda: not all(inputs), "NOR": lambda: not any(inputs),
                "OR": lambda: any(inputs), "NOT": lambda: not inputs[0]}[self.kind]()

    def evidence(self):
        return {"reference": self.ref, "unit": self.unit, "operation": self.kind,
                "input_pins": list(self.input_pins), "input_nets": list(self.inputs),
                "output_pin": self.output_pin, "output_net": self.output,
                "source": SOURCES[self.family], "evidence_basis": "native-netlist and manufacturer pin table"}


class Design:
    def __init__(self, path):
        self.path = Path(path)
        tree = parse_file(self.path)
        self.design = find_first(tree, "design")
        self.components = {child(c, "ref"): c for c in find_all(find_first(tree, "components"), "comp")}
        self.pins = {}
        self.nodes = {}
        for net in find_all(find_first(tree, "nets"), "net"):
            name = child(net, "name")
            self.nodes[name] = []
            for node in find_all(net, "node"):
                ref, pin = child(node, "ref"), child(node, "pin")
                self.pins.setdefault(ref, {})[str(pin)] = name
                self.nodes[name].append((ref, str(pin)))
        self.gates = []
        for ref, comp in self.components.items():
            value = child(comp, "value", "")
            for family, (kind, units) in PIN_MAPS.items():
                if family in value:
                    for unit, (inputs, output) in enumerate(units, 1):
                        self.gates.append(Gate(ref, unit, family, kind, inputs, output,
                                               tuple(self.net(ref, pin) for pin in inputs), self.net(ref, output)))
        self.outputs = {gate.output: gate for gate in self.gates}

    def net(self, ref, pin):
        return self.pins[ref][str(pin)]

    def value(self, ref):
        return child(self.components[ref], "value")

    def resistor(self, ref):
        text = self.value(ref).strip().lower().replace("ohm", "").replace("r", "")
        scale = 1000 if text.endswith("k") else 1000000 if text.endswith("m") else 1
        return float(text[:-1] if scale != 1 else text) * scale

    def resistor_between(self, ref, a, b):
        return {self.net(ref, 1), self.net(ref, 2)} == {a, b}

    def pull(self, net, rail):
        return [ref for ref in self.components if ref.startswith("R") and
                {self.pins.get(ref, {}).get("1"), self.pins.get(ref, {}).get("2")} == {net, rail}]

    def combinational(self, external, run):
        values = {"GND": False, "+3V3": True, "HW_RUN_LATCH": bool(run), **external}
        pending = list(self.gates)
        while pending:
            remaining = []
            for gate in pending:
                if all(net in values for net in gate.inputs):
                    values[gate.output] = gate.evaluate(values)
                else:
                    remaining.append(gate)
            if len(remaining) == len(pending):
                raise ValueError("Unknown/cyclic gate inputs: " + str([g.evidence() for g in remaining]))
            pending = remaining
        # Native U35 output pins 1/7 are open drains on the common /CLR net.
        # R150 supplies HIGH from the NOR driver; either LOW open drain overrides
        # that HIGH. Ideal DC comparator polarity is validated below from pins.
        vdd = external.get("v3v3_v", 3.3)
        vref = vdd * self.resistor("R157") / (self.resistor("R156") + self.resistor("R157"))
        top12 = self.resistor("R151") + self.resistor("R152")
        top5 = 1 / (1 / self.resistor("R154") + 1 / self.resistor("R158"))
        sense12 = external.get("raw12_v", 12.0) * self.resistor("R153") / (top12 + self.resistor("R153"))
        sense5 = external.get("logic5_v", 5.0) * self.resistor("R155") / (top5 + self.resistor("R155"))
        values["RAIL12_MONITOR_OK"] = sense12 >= vref
        values["RAIL5_MONITOR_OK"] = sense5 >= vref
        values[self.net("U34", 1)] = values[self.net("R150", 1)] and sense12 >= vref and sense5 >= vref
        return values


class StopModel:
    """Settled Boolean events; simultaneous clear release/clock edge is flagged.

    Inputs ESTOP_CLOSED_N/UV_FAULT are assumed already-qualified receiver bits.
    Supply validity below the HC operating region is outside this model.
    """
    def __init__(self, design, run=False):
        self.design = design
        self.run = bool(run)
        self.previous_clock = False
        self.previous_clear = False
        self.events = []

    def step(self, *, arm_n=True, closed_n=False, uv=False, pg=True, role_n=False,
             raw12_v=12.0, logic5_v=5.0, v3v3_v=3.3):
        external = {"BUS_ARM_N": bool(arm_n), "ESTOP_CLOSED_N": bool(closed_n),
                    "ESTOP_UV_FAULT": bool(uv), "PG_RESET_N": bool(pg), "LOCAL_MASTER_N": bool(role_n),
                    "raw12_v": raw12_v, "logic5_v": logic5_v, "v3v3_v": v3v3_v}
        before = self.design.combinational(external, self.run)
        clock = before[self.design.net("U34", 3)]
        clear = before[self.design.net("U34", 1)]
        preset = before[self.design.net("U34", 4)]
        data = before[self.design.net("U34", 2)]
        rising = clock and not self.previous_clock
        collision = clear and not self.previous_clear and rising
        if not preset:
            raise ValueError("/PRE unexpectedly asserted; model requires fixed inactive preset")
        if not clear:
            self.run = False
        elif rising:
            self.run = data
        values = self.design.combinational(external, self.run)
        result = {"safe": values["SAFE_PERMIT"], "clear_n": clear,
                  "clear_drive_n": values["RUN_CLEAR_DRIVE_N"], "rail12_ok": values["RAIL12_MONITOR_OK"],
                  "rail5_ok": values["RAIL5_MONITOR_OK"], "clock": clock,
                  "run": self.run, "oe_n": values["RLY_OE_ACTUAL_N"],
                  "coil_enable_request": values["COIL_EN"],
                  "strong_coil_gate_path": values["COIL_EN"] and pg and raw12_v > 0,
                  "recovery_collision_requires_analogue_qualification": collision}
        self.previous_clock, self.previous_clear = clock, clear
        self.events.append(result)
        return result


class Audit:
    def __init__(self):
        self.checks = []

    def check(self, name, condition, evidence):
        self.checks.append({"id": name, "status": "pass" if condition else "fail", "evidence": evidence,
                            "confidence": "deterministic", "evidence_source": "native-netlist/model"})

    def pin(self, design, ref, pin, expected):
        actual = design.net(ref, pin)
        self.check(f"pin:{ref}.{pin}", base(actual) == expected, {"actual_net": actual, "expected": expected})


def chain_step(models, *, arm_n, permissions=None, pgs=None, raw12s=None, logic5s=None):
    permissions = permissions or [True] * len(models)
    pgs = pgs or [True] * len(models)
    raw12s = raw12s or [12.0] * len(models)
    logic5s = logic5s or [5.0] * len(models)
    upstream = arm_n
    result = []
    for index, model in enumerate(models):
        state = model.step(arm_n=upstream, closed_n=not permissions[index], pg=pgs[index], role_n=index != 0,
                           raw12_v=raw12s[index], logic5_v=logic5s[index])
        result.append(state)
        upstream = state["oe_n"]  # Actual local inhibit forwarded, never raw MCU arm.
    return result


def supply_corners(design):
    """Engineering DC corners, deliberately separate from timing proof.

    All 1% resistor/supply/offset/bias combinations are enumerated. The 100nA
    per-pin bias allowance is an engineering assumption; two inputs load REF.
    TLV9022 publishes 5pA typical bias, not a guaranteed full-temp maximum.
    No claim about invalid VCC or analogue output response time is made.
    """
    def rvalues(ref):
        value = design.resistor(ref)
        return (value * .99, value * 1.01)

    result = {"assumptions": {"V3V3": "3.3V +/-3%", "resistors": "+/-1%", "offset_mV": 2,
                               "bias_nA_per_pin": 100, "reference_input_count": 2,
                               "bias_basis": "Conservative engineering allowance; manufacturer specifies5pA typical, no full-temperature maximum",
                               "offset_basis": "TLV9022 full-temperature2mV limit tested atVS1.8V/5V; intermediate3.3V qualification remains",
                               "normal_supply_min_V": {"5V": 4.75, "12V": 10.8},
                               "common_mode_rule": "TLV9022 rail-to-rail VCC+0.2V upper range; use assumedPG threshold minimum2.955V"}}
    reference_nominal = 3.3 * design.resistor("R157") / (design.resistor("R156") + design.resistor("R157"))
    for rail, tops, bottom, parallel in [("12V", ("R151", "R152"), "R153", False),
                                         ("5V", ("R154", "R158"), "R155", True)]:
        trips = []
        combinations = itertools.product((3.3 * .97, 3.3 * 1.03), rvalues("R156"), rvalues("R157"),
                                         rvalues(tops[0]), rvalues(tops[1]), rvalues(bottom),
                                         (-1, 1), (-1, 1), (-1, 1))
        for vdd, ref_top, ref_bottom, top1, top2, bot, ref_bias_sign, sense_bias_sign, offset_sign in combinations:
            top = 1 / (1 / top1 + 1 / top2) if parallel else top1 + top2
            reference = vdd * ref_bottom / (ref_top + ref_bottom)
            reference += ref_bias_sign * 2 * 100e-9 / (1 / ref_top + 1 / ref_bottom)
            error = offset_sign * .002 + sense_bias_sign * 100e-9 / (1 / top + 1 / bot)
            trips.append((reference + error) * (top + bot) / bot)
        nominal_top = (1 / (1 / design.resistor(tops[0]) + 1 / design.resistor(tops[1])) if parallel
                       else design.resistor(tops[0]) + design.resistor(tops[1]))
        nominal = reference_nominal * (nominal_top + design.resistor(bottom)) / design.resistor(bottom)
        result[rail] = {"nominal_trip_V": nominal, "trip_min_V": min(trips), "trip_max_V": max(trips),
                        "enumerated_corners": len(trips), "top_effective_ohm": nominal_top,
                        "bottom_ohm": design.resistor(bottom),
                        "equation": "Vtrip=(VREF + comparator offset + sense-bias error)*(Rtop+Rbottom)/Rbottom"}
    result["reference_nominal_V"] = reference_nominal
    result["sense12_max_V"] = 13.2 * max(rvalues("R153")) / (min(rvalues("R151")) + min(rvalues("R152")) + max(rvalues("R153")))
    min5top = 1 / (1 / min(rvalues("R154")) + 1 / min(rvalues("R158")))
    result["sense5_max_V"] = 5.5 * max(rvalues("R155")) / (min5top + max(rvalues("R155")))
    result["common_mode_min_when_PG_released_V"] = 2.955 + .2
    return result


def audit(design, self_test=False):
    out = Audit()
    expected = {
        "U34": {1: "RUN_CLEAR_N", 2: "+3V3", 3: "ARM_LEVEL", 4: "+3V3", 5: "HW_RUN_LATCH",
                7: "GND", 10: "+3V3", 11: "GND", 12: "GND", 13: "GND", 14: "+3V3"},
        "U31": {1: "SAFE_PERMIT", 2: "ESTOP_CLOSED_N", 3: "ESTOP_UV_FAULT", 4: "STOP_REQUEST",
                5: "SAFE_PERMIT", 6: "SAFE_PERMIT", 8: "STOP_REQUEST", 9: "PG_FAULT", 10: "RUN_CLEAR_DRIVE_N"},
        "U32": {1: "BUS_ARM_N", 2: "ARM_LEVEL", 5: "RLY_OE_ACTUAL_N", 6: "COIL_EN",
                9: "PG_RESET_N", 8: "PG_FAULT", 11: "LOCAL_MASTER_N", 10: "ROLE_RX_OE_N"},
        "U30": {12: "HW_RUN_LATCH", 13: "ARM_LEVEL", 11: "RLY_OE_ACTUAL_N"},
        "U3": {13: "RLY_OE_ACTUAL_N"}, "U40": {1: "GND", 2: "PG_RESET_N", 3: "+3V3"},
        "U35": {1: "RUN_CLEAR_N", 2: "RAIL_UV_REF", 3: "RAIL12_SENSE", 4: "GND",
                5: "RAIL5_SENSE", 6: "RAIL_UV_REF", 7: "RUN_CLEAR_N", 8: "+3V3"},
    }
    for ref, pinmap in expected.items():
        for pin, net in pinmap.items():
            out.pin(design, ref, pin, net)
    out.check("flipflop-family", "74HC74" in design.value("U34"), design.value("U34"))
    for ref in ("U30", "U31", "U32", "U34"):
        out.pin(design, ref, 7, "GND")
        out.pin(design, ref, 14, "+3V3")
    out.check("independent-3V3-supply-monitors", "TLV9022" in design.value("U35"), design.value("U35"))
    for ref, a, b in [("R150", design.net("U31", 10), design.net("U34", 1)),
                      ("R151", "+12V_IN", design.net("R152", 1)),
                      ("R152", design.net("R151", 2), design.net("U35", 3)),
                      ("R153", design.net("U35", 3), "GND"),
                      ("R154", "+5V_LOGIC", design.net("U35", 5)),
                      ("R158", "+5V_LOGIC", design.net("U35", 5)),
                      ("R155", design.net("U35", 5), "GND"),
                      ("R156", "+3V3", "RAIL_UV_REF"), ("R157", "RAIL_UV_REF", "GND")]:
        out.check(f"rail-monitor-network:{ref}", design.resistor_between(ref, a, b), design.pins[ref])
    out.check("OC-clear-sink-current", 3.3 * 1.03 / (design.resistor("R150") * .99) <= .004,
              {"max_mA": 1000 * 3.3 * 1.03 / (design.resistor("R150") * .99), "published_test_mA": 4})

    # Terminal comparisons preserve complete native sheet-local net names.
    p = design.net
    pairs = [(("Q41", 2), ("Q42", 3)), (("Q40", 1), ("R111", 1)),
             (("R111", 2), ("Q41", 3)), (("Q41", 1), ("R112", 2)),
             (("Q42", 1), ("R114", 2)), (("Q40", 2), ("R110", 1)),
             (("Q40", 1), ("R110", 2)), (("Q40", 2), ("D91", 1)), (("Q40", 1), ("D91", 2))]
    for a, b in pairs:
        out.check(f"connected:{a[0]}.{a[1]}:{b[0]}.{b[1]}", p(*a) == p(*b), {"a": p(*a), "b": p(*b)})
    for ref, pin, expected_net in [("Q40", 2, "+12V_IN"), ("Q40", 3, "+12V_COIL_SAFE"),
                                    ("Q42", 2, "GND"), ("R112", 1, "COIL_EN"), ("R114", 1, "PG_RESET_N")]:
        out.pin(design, ref, pin, expected_net)
    for ref, node in [("R113", p("Q41", 1)), ("R115", p("Q42", 1)), ("R116", p("Q41", 2))]:
        out.check(f"return:{ref}", design.resistor_between(ref, node, "GND"), design.pins[ref])
    for channel in range(1, 9):
        out.check(f"relay-coil:{channel}", p(f"K{channel}", 5) == p("Q40", 3), design.pins[f"K{channel}"])
    direct_coil_headers = [(ref, pin) for ref, pin in design.nodes[p("Q40", 3)] if ref.startswith("J")]
    out.check("no-direct-coil-supply-header", not direct_coil_headers, direct_coil_headers)
    out.check("debug-OE-observation-isolated", design.resistor_between("R136", "RLY_OE_ACTUAL_N", "OE_MONITOR_N") and p("J5", 9) == "OE_MONITOR_N", design.pins["R136"])
    out.check("debug-OE-counterdrive-current", design.resistor("R136") >= 100000, {"max_uA": 1e6 * 3.3 * 1.03 / (design.resistor("R136") * .99)})
    hard_oe_headers = [(ref, pin) for ref, pin in design.nodes["RLY_OE_ACTUAL_N"] if ref.startswith("J")]
    out.check("no-direct-hard-OE-header", not hard_oe_headers, hard_oe_headers)

    # Physical role and isolated monitor nodes, including ordinary GPIO counterdrive.
    out.pin(design, "JP1", 1, "LOCAL_MASTER_N")
    out.pin(design, "JP1", 2, "GND")
    for ref, source, target, module_pin in [("R4", "SAFE_PERMIT", "ESTOP_SAFE_MON_GPIO18", 10),
                                           ("R5", "HW_RUN_LATCH", "HW_RUN_MON_GPIO21", 23),
                                           ("R71", "LOCAL_MASTER_N", "ROLE_GPIO2_MON", 38)]:
        out.check(f"isolated-monitor:{ref}", design.resistor_between(ref, source, target) and p("U1", module_pin) == target,
                  {"resistor": design.pins[ref], "module_pin": module_pin, "ohms": design.resistor(ref)})
    for ref, oe in [("U50", "LOCAL_MASTER_N"), ("U51", "ROLE_RX_OE_N"), ("U52", "GND")]:
        out.pin(design, ref, 1, oe)
        out.pin(design, ref, 19, oe)
    for role_n, local_arm, upstream_arm in itertools.product((False, True), repeat=3):
        values = design.combinational({"BUS_ARM_N": True, "ESTOP_CLOSED_N": False,
                                       "ESTOP_UV_FAULT": False, "PG_RESET_N": True,
                                       "LOCAL_MASTER_N": role_n}, False)
        local_enabled = not values[p("U50", 19)]
        receiver_enabled = not values[p("U51", 19)]
        selected = local_arm if local_enabled else upstream_arm
        out.check(f"role-selector:{int(role_n)}{int(local_arm)}{int(upstream_arm)}",
                  local_enabled != receiver_enabled and selected == (upstream_arm if role_n else local_arm),
                  {"local_enabled": local_enabled, "receiver_enabled": receiver_enabled, "selected_arm_n": selected})
    out.pin(design, "U50", 15, "MCU_INHIBIT_N_GPIO15")
    out.pin(design, "U50", 5, "BUS_ARM_N")
    out.pin(design, "U51", 15, "UP_ARM_N")
    out.pin(design, "U51", 5, "BUS_ARM_N")
    out.pin(design, "U52", 15, "RLY_OE_ACTUAL_N")
    out.check("forward-actual-inhibit", design.resistor_between("R85", p("U52", 5), "DOWN_ARM_N") and p("J21", 7) == "DOWN_ARM_N",
              {"buffer": design.pins["U52"], "series": design.pins["R85"], "header_pin": p("J21", 7)})
    for net, rail in [("UP_ARM_N", "+3V3"), ("UP_LOAD_N", "+3V3"), ("UP_CLK", "GND"),
                      ("UP_LATCH", "GND"), ("UP_CLR_N", "GND"), ("UP_SER", "GND")]:
        out.check(f"unplugged-default:{net}", bool(design.pull(net, rail)), {"rail": rail, "resistors": design.pull(net, rail)})
    for net, rail in [("MCU_INHIBIT_N_GPIO15", "+3V3"), ("MCU_LOAD_N_GPIO17", "+3V3"),
                      ("MCU_CLK_GPIO6", "GND"), ("MCU_LATCH_GPIO7", "GND"),
                      ("MCU_CLR_N_GPIO16", "GND"), ("MCU_MOSI_GPIO4", "GND")]:
        out.check(f"MCU-high-Z-default:{net}", bool(design.pull(net, rail)), {"rail": rail, "resistors": design.pull(net, rail)})
    out.check("physical-role-pullup", bool(design.pull("LOCAL_MASTER_N", "+3V3")), design.pull("LOCAL_MASTER_N", "+3V3"))

    table = []
    for closed_n, uv, pg, arm_n in itertools.product((False, True), repeat=4):
        model = StopModel(design, run=True)
        model.step(arm_n=True, closed_n=closed_n, uv=uv, pg=pg)
        result = model.step(arm_n=arm_n, closed_n=closed_n, uv=uv, pg=pg)
        permitted = not closed_n and not uv and pg
        out.check(f"truth:{int(closed_n)}{int(uv)}{int(pg)}{int(arm_n)}",
                  result["safe"] == (not closed_n and not uv) and result["clear_n"] == permitted and
                  result["strong_coil_gate_path"] == (permitted and not arm_n), result)
        table.append({"closed_n": closed_n, "uv_fault": uv, "pg": pg, "arm_n": arm_n, **result})

    sequences = {}
    for name, fault in [("NC-open", {"closed_n": True}), ("negative-field-fault", {"uv": True}),
                        ("PG-loss", {"pg": False}), ("12V-loss", {"raw12_v": 0}), ("5V-loss", {"logic5_v": 0})]:
        model = StopModel(design)
        model.step(arm_n=True, pg=False)
        model.step(arm_n=True)
        armed = model.step(arm_n=False)
        stopped = model.step(arm_n=False, **fault)
        restored = model.step(arm_n=False)
        held = [model.step(arm_n=False) for _ in range(16)]
        model.step(arm_n=True)
        rearmed = model.step(arm_n=False)
        good = armed["run"] and not stopped["run"] and not restored["run"] and not any(s["run"] for s in held) and rearmed["run"]
        out.check(f"sequence:{name}:release-held-arm", good, {"stopped": stopped, "restored": restored, "rearmed": rearmed})
        sequences[name] = model.events
    model = StopModel(design, run=True)
    startup = model.step(arm_n=False, pg=False)
    pg_restore = model.step(arm_n=False, pg=True)
    out.check("arm-while-PG-invalid-remains-off-after-recovery", not startup["run"] and not pg_restore["run"], model.events)
    never_boots = StopModel(design, run=True)
    never_boots.step(arm_n=True, pg=False)
    idle = never_boots.step(arm_n=True, pg=True)
    out.check("MCU-never-boots-after-PG-release", not idle["run"] and not idle["strong_coil_gate_path"], never_boots.events)
    for name, fault in [("12V", {"raw12_v": 0}), ("5V", {"logic5_v": 0})]:
        model = StopModel(design)
        low = model.step(arm_n=False, **fault)
        recovered = model.step(arm_n=False)
        out.check(f"arm-while-{name}-invalid-does-not-start-on-restoration", not low["run"] and not recovered["run"], model.events)
    model = StopModel(design)
    model.step(arm_n=True, pg=False)
    collision = model.step(arm_n=False, pg=True)
    out.check("recovery-collision-is-disclosed", collision["recovery_collision_requires_analogue_qualification"], collision)

    chain_coverage = []
    for count in (1, 2, 3, 32):
        models = [StopModel(design) for _ in range(count)]
        chain_step(models, arm_n=True, pgs=[False] * count)
        chain_step(models, arm_n=True)
        enabled = chain_step(models, arm_n=False)
        # Host sees the complete NC continuity loop; healthy downstream receivers
        # cannot override its propagated inhibit after that loop opens.
        fault = chain_step(models, arm_n=False, permissions=[False] + [True] * (count - 1))
        restored = chain_step(models, arm_n=False)
        chain_step(models, arm_n=True)
        rearmed = chain_step(models, arm_n=False)
        correct = all(v["strong_coil_gate_path"] for v in enabled + rearmed) and not any(v["strong_coil_gate_path"] for v in fault + restored)
        out.check(f"chain:{count}:host-stop-release-rearm", correct, {"enabled": enabled, "fault": fault, "restored": restored, "rearmed": rearmed})
        chain_coverage.append({"boards": count, "host_stop_disables_all": correct})
        if count > 1:
            local_permissions = [True] * count
            local_permissions[1] = False
            local = chain_step(models, arm_n=False, permissions=local_permissions)
            out.check(f"chain:{count}:local-stop-forward", local[0]["run"] and not any(v["strong_coil_gate_path"] for v in local[1:]), local)
            for rail in ("12V", "5V"):
                chain_step(models, arm_n=True)
                chain_step(models, arm_n=False)
                kwargs = {"raw12s": [12.0] * count} if rail == "12V" else {"logic5s": [5.0] * count}
                kwargs[next(iter(kwargs))][1] = 0
                faulted = chain_step(models, arm_n=False, **kwargs)
                recovered = chain_step(models, arm_n=False)
                out.check(f"chain:{count}:local-{rail}-loss-held-arm", faulted[0]["run"] and recovered[0]["run"] and
                          not any(v["strong_coil_gate_path"] for v in faulted[1:] + recovered[1:]),
                          {"faulted": faulted, "recovered": recovered})

    if self_test:
        # Sensitivity test: a raw-arm forwarding regression would leave a healthy
        # downstream board enabled when only the preceding RUN latch was cleared.
        first, second = StopModel(design), StopModel(design)
        for arm in (True, False):
            state = first.step(arm_n=arm)
            second.step(arm_n=state["oe_n"], role_n=True)
        stopped = first.step(arm_n=False, closed_n=True)
        raw_regression = second.step(arm_n=False, role_n=True)
        out.check("sensitivity:raw-arm-forwarding-is-unsafe", stopped["oe_n"] and raw_regression["strong_coil_gate_path"], raw_regression)
        # Solve the prior cross-coupled NOR equations rather than assuming its
        # answer. Keep the same arm-pulse level during stop and subsequent release.
        legacy = []
        for safe, pg, pulse in [(True, True, True), (False, True, True), (True, True, True)]:
            reset, stop_set = safe and pulse, not safe or not pg
            states = [(stop, run) for stop, run in itertools.product((False, True), repeat=2)
                      if stop == (not (reset or run)) and run == (not (stop_set or stop))]
            legacy.append({"safe": safe, "pg": pg, "same_arm_pulse": pulse, "stable_states": states})
        out.check("sensitivity:legacy-pulse-restart-counterexample",
                  legacy[0]["stable_states"] == [(False, True)] and
                  legacy[1]["stable_states"] == [(True, False)] and
                  legacy[2]["stable_states"] == [(False, True)], legacy)

    gate_bias = 3.3 * 1.03 / (design.resistor("R116") * 0.99) * (design.resistor("R110") * 1.01)
    role_fraction = (design.resistor("R71") * 0.99) / (design.resistor("R71") * 0.99 + design.resistor("R70") * 1.01)
    corners = supply_corners(design)
    out.check("5V-normal-supply-corner-margin", corners["5V"]["trip_max_V"] < 4.75, corners["5V"])
    out.check("12V-normal-supply-corner-margin", corners["12V"]["trip_max_V"] < 10.8, corners["12V"])
    out.check("monitor-common-mode-margin", corners["sense12_max_V"] < corners["common_mode_min_when_PG_released_V"] and
              corners["sense5_max_V"] < corners["common_mode_min_when_PG_released_V"], corners)
    failed = [check for check in out.checks if check["status"] != "pass"]
    return {
        "schema": "hardware-stop-state-review/v1", "review_date": child(design.design, "date", "").split("T")[0],
        "verdict": "pass-with-physical-qualification" if not failed else "failed",
        "source": {"netlist": str(design.path.resolve()), "sha256": hashlib.sha256(design.path.read_bytes()).hexdigest(),
                   "export_date": child(design.design, "date"), "tool": child(design.design, "tool"),
                   "components": len(design.components), "nets": len(design.nodes)},
        "gate_functions": [gate.evidence() for gate in design.gates],
        "flipflop": {"reference": "U34", "pins": design.pins["U34"], "part": design.value("U34"),
                     "source": SOURCES["74HC74"], "source_pages": "3–4 pin map/function; 7–8 timing"},
        "rail_monitor": {"reference": "U35", "pins": design.pins["U35"], "part": design.value("U35"),
                         "source": SOURCES["TLV9022"], "source_pages": "4 pin map;7 recommended supply;11 electrical;12 typical timing",
                         "sink_current_max_mA": 1000 * 3.3 * 1.03 / (design.resistor("R150") * .99),
                         "R150_ohm": design.resistor("R150"), "full_temp_Vol_spec_mV": 175,
                         "Vol_test_condition": "4mA, VS5V default; actual3.3V/0.731mA LOW level must be checked",
                         "input_bias_typical_pA": 5, "input_bias_guaranteed_max": None},
        "derived_equations": ["SAFE_PERMIT = NOT(ESTOP_CLOSED_N OR ESTOP_UV_FAULT)",
                              "STOP_REQUEST = NOT(SAFE_PERMIT)", "PG_FAULT = NOT(PG_RESET_N)",
                              "RUN_CLEAR_DRIVE_N = NOT(STOP_REQUEST OR PG_FAULT) = SAFE_PERMIT AND PG_RESET_N",
                              "RUN_CLEAR_N = RUN_CLEAR_DRIVE_N AND RAIL12_OK AND RAIL5_OK (open-drain wired override via R150)",
                              "ARM_LEVEL = NOT(BUS_ARM_N)",
                              "RUN=0 whenever RUN_CLEAR_N=0; otherwise a fresh ARM_LEVEL rising edge captures D=1",
                              "RLY_OE_ACTUAL_N = NOT(HW_RUN_LATCH AND ARM_LEVEL)",
                              "COIL_EN = NOT(RLY_OE_ACTUAL_N)", "strong coil pull-down requires COIL_EN AND PG_RESET_N"],
        "truth_table": table, "sequences": sequences, "chain_coverage": chain_coverage,
        "checks": out.checks, "summary": {"checks": len(out.checks), "passed": len(out.checks) - len(failed), "failed": len(failed)},
        "analytical_qualifications": {
            "supply_monitor_corners": corners,
            "R116_is_not_an_open_circuit": "100k emitter return bypasses Q42 weakly; no zero-current proof is claimed",
            "weak_gate_bias_upper_V": gate_bias,
            "weak_gate_bias_assumptions": "Q41 emitter <=3.3V+3%; R116 -1%, R110 +1%; excludes transistor hot leakage/back-power/invalid logic rails",
            "role_low_counterdrive_fraction_of_VCC": role_fraction,
            "role_counterdrive_assumptions": "GPIO2 drives LOW through R71 -1%, role pullup R70 +1%; JP1 open; ordinary 0..VCC GPIO fault only",
            "clear_clock_collision": "Async clear release near a clock rising edge must meet HC74 recovery time; Boolean event priority is not physical timing proof",
        },
        "findings": [
            {"id": "HS-001", "severity": "info", "confidence": "deterministic", "evidence_source": "native-netlist/manufacturer",
             "summary": "HC74 asynchronous clear fixes restart on stop release during an existing RC arm pulse"},
            {"id": "HS-002", "severity": "info", "confidence": "deterministic", "evidence_source": "native-netlist",
             "summary": "Input-side UP controls now have safe unplugged defaults; actual local inhibit forwards downstream"},
            {"id": "HS-003", "severity": "warning", "confidence": "deterministic", "evidence_source": "manufacturer timing",
             "summary": "Recovery/reset-pulse widths and asynchronous path skew require physical qualification"},
            {"id": "HS-004", "severity": "warning", "confidence": "heuristic", "evidence_source": "bounded DC calculation",
             "summary": "R116 weak gate bias is about 0.16V under stated valid-rail assumptions; hot/powered-off coil leakage must be measured"},
            {"id": "HS-005", "severity": "info", "confidence": "deterministic", "evidence_source": "native-netlist/qualified DC model",
             "summary": "3.3V-powered open-drain supply monitors clear RUN on 5V/12V loss; restoration while ARM is held cannot restart outputs"},
        ],
        "model_scope": {
            "logic": "Settled 0/1 gates plus ideal-DC U35 supply-monitor signs, using actual native pin nets and edge-triggered FF asynchronous clear",
            "chain": "Ideal buffered stages; host NC-loop fault propagates actual OE downstream; a local-only fault stops that board/downstream, not necessarily upstream",
            "not_modeled": ["analog field thresholds/±100V detector behavior", "propagation/RC timing", "metastability",
                            "unpowered or out-of-range CMOS truth behavior", "PMOS/BJT leakage/temperature/SOA", "relay/valve mechanical release", "welded contacts", "physical cable length/capacitance"],
            "other_workflows": "This scoped review does not rerun schematic/PCB/EMC/thermal/SPICE/lifecycle analyzers; the parent project's full review owns them",
            "certification": False,
        },
        "trust_summary": {"trust_level": "high within Boolean/connectivity scope; physical qualification open",
                          "deterministic_checks": len(out.checks), "datasheet_sources": SOURCES,
                          "physical_timing_verified": False, "hardware_tested": False},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netlist", type=Path, default=ROOT / "analysis/Universal_Poofer_Control.net")
    parser.add_argument("--output", type=Path, default=ROOT / "analysis/hardware-stop-state-review.json")
    parser.add_argument("--self-test", action="store_true", help="include mutation/sensitivity regressions")
    args = parser.parse_args()
    try:
        report = audit(Design(args.netlist), args.self_test)
    except (KeyError, ValueError, ZeroDivisionError, OSError) as error:
        report = {"schema": "hardware-stop-state-review/v1", "verdict": "cannot-complete",
                  "source": {"netlist": str(args.netlist.resolve()),
                             "sha256": hashlib.sha256(args.netlist.read_bytes()).hexdigest() if args.netlist.exists() else None},
                  "summary": {"checks": 0, "passed": 0, "failed": 1}, "error": str(error)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Hardware-stop audit cannot complete: {error}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verdict": report["verdict"], "source": report["source"], "summary": report["summary"]}, indent=2))
    for check in report["checks"]:
        if check["status"] != "pass":
            print(json.dumps(check))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
