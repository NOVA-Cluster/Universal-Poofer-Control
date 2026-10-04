# Universal Poofer Control — revision A.3

Controller platform intended for creating theatrical flame effects devices (poofers), including stage effects, flame-art installations and custom theatrical projects. The current design remains an engineering preview, not a qualified live-effects system.

Editable KiCad 10 design for ESP32-S3-WROOM-1-N8, eight relay-controlled 12 VDC valves and eight **grounded switches, active LOW**, with nominal **20 mA board-sourced wetting current**. The field circuits are designed for continuous ±100 V relative to shared return, including power-off conditions. Physical fault and temperature qualification remains required.

Open `Universal_Poofer_Control.kicad_pro`. The schematic has **24 numbered A3 sheets**, grouped by function with repeated channel layouts and local wiring. The **200 × 160 mm PCB is placement only**: 0.5 mm footprint-origin grid, no tracks, vias or copper pours. `AGENTS.md` makes these engineering and appearance standards persistent.

**New to the board?** Start with the [Hardware User Guide](docs/hardware-user-guide.md), the maintained customer-facing source of truth for features, project ideas, wiring, first-use commissioning, expansion and schematic navigation. A.3 remains an engineering preview until qualification.

## Files

| Deliverable | Location |
|---|---|
| Customer hardware guide | `docs/hardware-user-guide.md` / `output/pdf/Universal_Poofer_Control_Hardware_User_Guide.pdf` |
| Editable schematic / board | `Universal_Poofer_Control.kicad_sch` / `.kicad_pcb` |
| Schematic PDF | `output/pdf/Universal_Poofer_Control_A3.pdf` |
| Board preview | `output/pcb/placement_top.png` / `.pdf` |
| Full hardware review | `docs/hardware-design-review-A3.md` |
| Analog and stop evidence | `docs/hardware-topology-review.md`, `docs/hardware-stop-logic-review.md` |
| Complete connector reference | `docs/connector-pinouts.md` |
| Arduino / PlatformIO project | `firmware/` |
| Exact JLC assembly BOM / stock | `bom/JLCPCB_BOM.csv`, `bom/assembly_availability.csv` |

## Power and valves

J1: pin 1 regulated **5.0–5.25 V, ≥1 A**, pin 2 GND. J2: pin 1 **12 V, ≥0.5 A**, pin 2 GND, powering analog circuits and eight approximately 30 mA relay coils. Both supplies share logic/input GND. Each expansion module has independent supplies; chain headers have no power pins.

Feed each `J31…J38.1 / COM` from an **individually fused external 12 V valve supply**. Connect its valve between `J41…J48.1 / NO` and `.2 / RETURN`, and connect RETURN to that external supply's negative. Valve RETURN is separate from logic GND. The aggregate valve current does not pass through a common board power header. Plan for **1 A per valve**. The relays' 10 A resistive-contact rating is not the header or inductive-load rating. NC is auxiliary and must not be used for shutdown-controlled valve loads.

All interfaces are 2.54 mm / 100 mil headers. Every resistor/capacitor is **0805**. Ordinary ICs are SOIC; other packages are DPAK, SOT-223, SOT-23 and SMA/SMB. The ESP32 is a replaceable castellated module. There are no 0402/0603 passives or TSSOP logic.

## Switch inputs

Close a dry contact between `J11…J18.1 / FIELD` and `.2 / GND`. LOW means closed; an open contact is inactive. A compensated LM2902 / HV PNP source supplies approximately 20 mA to a grounded contact. A backup limiter bounds saturation-recovery surges. Independent protected paths sense contact state and negative faults.

Closed FIELD must be ≤0.3 V including wiring/contact drop; ≤10 Ω total series-loop contact/return resistance (including every contact and cable in an expansion chain) is a conservative system target. Wetting is nominal, not calibrated or a guaranteed 20 mA minimum. Source accuracy, all-channel settling, MLCC capacitance, cold compliance, fault quench and hot powered-off leakage need prototype tests.

Each module captures 16 bits: active-HIGH fault byte, then active-LOW contact byte. Firmware computes `closed = (~contacts_n) & (~faults)`. Fault detection has a finite threshold: small negative voltages near ground can still read as closed. ±100 V endurance does not imply every intermediate voltage has a unique diagnostic interpretation. This protection applies only to FIELD pins; power, GPIO, I²C, expansion logic and GND retain ordinary limits.

## Hardware emergency stop

J9 connects an external **NC contact** between ESTOP_FIELD and ESTOP_CHAIN_OUT. Opening the loop, disconnecting it, or asserting its field fault removes permission. The master supplies nominal 20 mA. Fit **J10 ground termination only on the last module**; on a single board it is that board. Remove intermediate terminators.

Hardware clears an edge-triggered RUN flip-flop, disables actual 595 `/OE`, and cuts relay-coil power. A 3.3 V supervisor blocks startup/brownout; logic-powered supply monitors also clear RUN on loss of 5 V or raw 12 V (nominal trips about 4.27 V / 8.88 V). Restoring the loop or a supply cannot restart while ARM is held. A fresh arm edge is required. Actual hardware inhibit propagates downstream without firmware cooperation.

GPIO18 reads protected loop permission; GPIO21 reads protected local RUN. Series isolation prevents GPIO backdrive from overriding hardware. GPIO2 observes the physical host jumper through 100 kΩ.

This is a single-channel prototype shutdown circuit. Coil removal cannot open a welded relay contact, and a short across an NC contact can bypass that contact. Use an independent valve-power disconnect where those faults must stop flow. Measure actual relay/valve closure time and clamp energy. No safety certification or shutdown-time rating is established.

## Expansion and I²C

Connect J21 DOWN to the next J20 UP with matching pin numbers. Fit **JP1 on exactly one host**, leave it absent on expanders, and configure roles with power off. Reset after role changes. Do not hot-plug an armed control chain.

| Pin | J20 UP | J21 DOWN |
|---:|---|---|
| 1, 2 | GND | GND |
| 3 | Clock input | Buffered clock |
| 4 | 595 serial input | Local 595 QH′ |
| 5 | Input stream returned upstream | Input stream from next module |
| 6 | Latch input | Buffered latch |
| 7 | Active-low arm/inhibit input | Actual hardware-gated inhibit |
| 8 | Clear input | Buffered clear |
| 9 | Parallel-load input | Buffered parallel load |
| 10 | GND | GND |
| 11 | ESTOP_FIELD | ESTOP_CHAIN_OUT |
| 12, 13, 14 | GND | GND |
| **15** | **I²C SDA common bus** | **I²C SDA common bus** |
| **16** | **I²C SCL common bus** | **I²C SCL common bus** |

LVC244 buffers regenerate shift signals with power-off isolation and 33 Ω series resistors. UP controls have their own safe pulls, so an unplugged expander inhibits. The return tail pulls HIGH, filling absent-module fault bytes with FF. Write 595 bytes farthest-first and read 165 words host-first. Firmware supports a configured **1–32 modules**, each adding 8 output and 16 input bits; this allocation is not a qualified cable-length or physical-chain limit.

I²C uses GPIO8/SDA and GPIO9/SCL on each private MCU B-side bus, isolated onto the common A-side by PCA9517A. Only A sides join together. Fit JP2 at one common pullup provider, normally the host: **2.2 kΩ common**, **4.7 kΩ private** pullups. Start at **100 kHz**, qualify common capacitance ≤400 pF and LOW/high/rise-time/leakage behavior. Thirty-two buffers can consume 224 pF before cables. Unique peripheral addresses and bus loading are independent of shift-chain expansion. [NXP PCA9517A datasheet](https://www.nxp.com/docs/en/data-sheet/PCA9517A.pdf); see `docs/i2c-interface-review.md`.

## GPIO, programming and firmware

| Function | GPIO |
|---|---:|
| Clock / output serial / input serial | 6 / 4 / 5 |
| Latch / MCU inhibit / clear / input load | 7 / 15 / 16 / 17 |
| Loop permission / local RUN / role monitor | 18 / 21 / 2 |
| I²C SDA / SCL | 8 / 9 |
| UART TX / RX | 43 / 44 |
| USB D− / D+ | 19 / 20 |

J3/J4 expose module pins 1–40; pad 41 is grounded on the PCB. GPIO0/3/45/46 are straps. J6 is EN/GND/BOOT; J7 is TX/RX/GND for a 3.3 V UART adapter. Exposed USB signals need a suitable protected external connection. Every header pin, including J5 debug/service access, is listed in `docs/connector-pinouts.md`.

The Arduino/PlatformIO scaffold starts inhibited, clears/latches all configured outputs, requires explicit arm and hardware RUN acknowledgement, and supports bounded 1–1000 ms pulses with a 500 ms renewable control lease. I²C scans are explicit and disarmed-only. It does not automatically map switches to valves. Nothing has been flashed.

From `firmware/`: `pio run -e poofer_uart -e poofer_usb -e poofer_chain32_compile`; `pio test -e native`. `firmware/README.md` documents an isolated build environment. Three target builds and all 24 tests passed; physical timing, interrupts and watchdog remain hardware tests.

## Review, assembly and regeneration

The full review records native ERC, exported-netlist contract checks, saved-board parity, placement DRC, schematic/PCB/cross/thermal/EMC/lifecycle analyzers, generic SPICE and dedicated analog/stop models, with evidence and limitations. The unrouted PCB is not a fabrication release; production Gerbers and final routing/CPL validation have not been produced.

`scripts/build_schematic.py` invokes the A.3 builder; `scripts/build_pcb.py` reproduces placement; `scripts/validate_a3.py` checks the authoritative KiCad-exported netlist. Preserve and reconcile manual or unsaved editor work before regeneration. Local KiCad CLI/pcbnew paths must match the installation. Earlier incompatible active-HIGH / wetting-sink revisions are preserved locally under ignored `archive/`; they are not part of a fresh clone. See [repository contents](docs/repository-content.md) for the versioned sources and local artifacts.

All exact parts had JLC assembly inventory on 2026-10-03; Basic was preferred, with Extended devices retained where electrical/package requirements justify them. Mixed SMT/THT header/relay assembly needs the appropriate service and quote. Recheck stock and orientations at ordering. [JLC assembly capabilities](https://jlcpcb.com/capabilities/pcb-assembly-capabilities). Inventory is not lifecycle evidence: the available LCSC audit returns unknown lifecycle status; production release still needs manufacturer/distributor lifecycle checks.
