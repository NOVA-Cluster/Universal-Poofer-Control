# Universal Poofer Control — A.3 hardware design review

**Date:** 2026-10-03. **Stage:** schematic and PCB placement, deliberately unrouted. **Tools:** KiCad 10.0.5, native ERC/DRC/netlist export/pcbnew reload, schematic/PCB/cross/thermal/EMC/lifecycle analyzers, ngspice, dedicated exported-netlist and hardware-state checks, PlatformIO builds/tests.

## Overview and verdict

The revised design has 577 physical schematic components on 24 functional A3 sheets. It uses ESP32-S3-WROOM-1-N8, one 74HC595, two 74HC165s, eight 12 V relay/NO valve outputs and eight board-wetted grounded contacts. A ninth protected source/receiver serves a series NC stop loop. Buffered shift expansion and isolated I²C are available on 2×8 headers. All passives are 0805, and the active packages are selected for rework.

The 200 × 160 mm, four-layer board contains the 577 schematic parts plus four M3 holes and three fiducials. Native ERC is zero; saved-board pad/net parity and placement DRC pass. It has zero tracks, vias and copper pours. **This is a reviewed placement-stage prototype, not a fabrication or safety release.** Open items below require routing and physical qualification; the wetting loop's dynamic model sensitivity is a specific qualification concern.

## Critical findings and remaining work

| Status | Finding / consequence | Evidence and next verification |
|---|---|---|
| Required before release | The corrected wetting loop needs measured phase/settling margin and real-device fault qualification. Independent AC and current-limited models now support the added emitter filters; manufacturer-macro integration remains limited. | Dedicated native-derived simulations and independent loop review; bench all nine channels, startup, open/close transitions and fault recovery. Do not infer stability from DC agreement or generic RC tests. |
| Required before release | Continuous ±100 V, especially hot power-off leakage and maximum negative-fault quench, is not a tested endurance rating. | Manufacturer ratings and analytical bounds support the topology; qualify actual voltage, temperature, effective capacitance and repeated fault energy. |
| Required before release | LDO and HV-device heat spreading, field spacing, return paths and EMC are incomplete without copper. | Thermal/EMC analyzers identify this intentional stage; route and reassess with actual loads and enclosure ambient. |
| System requirement | Removing coil power cannot open a welded relay contact; a short across an NC contact can bypass it. | Relay mechanism and single-channel loop topology. Use an appropriate independent valve-power disconnect where those failures must stop flow. No SIL/PL or shutdown-time claim is made. |
| Required before release | Real stop/coil/valve release time and clamp energy depend on actual valves and wiring. | Coil/valve suppression is connected correctly; measure at 1 A, actual inductance and repetition rate. |
| Supply qualification | Rail-monitor LOW levels, input leakage, hysteresis and recovery timing need fixed-3.3 V tests. | TLV9022 low-supply design provides ample practical margin; not every endpoint electrical table is a separate 3.3 V guarantee. See the stop review. |

## Demonstrated problems corrected

| Problem found during review | Final correction |
|---|---|
| Earlier active-HIGH inputs and wetting sinks did not implement switches to ground. | Protected active-LOW receivers and nominal 20 mA board-sourced wetting. |
| A generated PNP collector/emitter connection could short the HV protection device. | Correct rotation/wiring and nine explicit native C/E-separation regressions. |
| Compensation wiring crossed a FIELD diode stub. | Separate wire geometry; native ERC and terminal-level contract checks. |
| Servo and fault override could continuously fight. | Mandatory 1 kΩ NPN collector resistors; bounded override current. |
| Shared compensation currents coupled the nine source references. | Private 10 kΩ/100 nF compensation nodes and buffered shared reference, with 200 Ω isolation / 10 µF hold capacitance. A separate 10 kΩ/100 nF emitter filter was added after the independent AC review; physical qualification remains open. |
| Direct emitter feedback had only about 2° nominal AC margin and became unstable at an illustrative high-gain corner. | Added 10 kΩ/100 nF IN+ emitter filters to all nine sources. Corrected illustrative margin is about 69° with an extra amplifier pole; current-limited transient checks settle near 20.315 mA. |
| Saturation recovery could create a large source-current spike. | Fast backup PNP limiters sensing half the shunt drop. Worst quench/SOA remains a measured qualification item. |
| A gate-based UV flag could miss a negative voltage after the source shut off. | Early emitter-based status sensing: four 100 kΩ conductances, 30 kΩ/10 kΩ reference, healthy positive bias. Worst-corner ordering fixture asserts fault before source cutoff. |
| A pulse-reset SR latch could restart after a brief stop within the pulse. | 74HC74 positive-edge RUN latch with asynchronous clear; stop restoration cannot create a clock. |
| Raw 12 V loss with 3.3 V retained could revive stored outputs on restoration. | Logic-powered TLV9022 monitors 12 V and 5 V and independently overrides `/CLR` through 4.7 kΩ. |
| MCU GPIOs could backdrive safety/role nodes. | 10 kΩ protected permission/RUN monitors and 100 kΩ physical-role monitor isolation. |
| A direct OE debug pin could bypass the hard inhibit. | R136=100k makes J5pin9 a high-impedance observation point; ordinary counterdrive stays below35µA. |
| Shared expansion supply pins could backfeed independent regulators. | No power pins on expansion headers; independent local supplies. |
| Downstream hardware stops could depend on upstream firmware. | Forward actual hardware-gated `/OE` as downstream inhibit. |
| Enabled UP receivers floated on an unplugged powered expander. | Input-side safe pulls, including UP_ARM_N HIGH; bus pulls alone were insufficient. |
| Headers for field inputs were missing during an early placement import. | J11–J18 restored and native connector regressions added. |
| Generic packing left some decouplers too far from their supply pins. | Explicit chip/cap pairs placed from actual VCC pad geometry; pad-edge routing opportunities ≤2.1 mm. |
| Positive fault-step charge could reverse-bias the detector emitter above6V. | Nine1nF emitter guards reduce the modeled100V step peak from7.60V to0.548V; quench remains about21µs in an illustrative slow/cold case. |
| A failed MCU boot left local buffer inputs undefined. | R130–R135 bias all six MCU-facing receiver inputs independently of downstream bus pulls. |
| Footprint/text/drill and document quality problems. | Correct relay NC/NO geometry, 1.3 mm relay drills, preserved project settings, cleared silk/courtyard DRC, grouped pages and 0.5 mm PCB grid. |

## Previous review delta

Revision A.2 is preserved in `archive/rev_A_2/`; it had active-HIGH voltage inputs with wetting sinks and no hardware stop or PCB. Those electrical instructions are obsolete. A.3 changes the input direction/polarity, serial word length, GPIO contract, suppression and shutdown architecture, packages and expansion headers. The prior single-byte firmware contract must not be reused.

`analysis/review-delta-A2-A3.json` records the analyzer diff. Its breaking/regression classification reflects the intentional architectural redesign and several heuristic no-driver reports; it is not a count of unfixed hardware defects. The corrected problems above and the explicit qualification items are the reviewer disposition.

## Component summary and sourcing

| Type | Physical quantity |
|---|---:|
| Resistors / capacitors | 312 / 71 |
| Transistors / diodes | 57 / 69 |
| ICs / relays / headers | 23 / 8 / 37 |
| Total | **577** |

There are 49 exact assembly part codes: 24 Basic and 25 Extended. Quantities are 427 Basic and 150 Extended. All selected types had assembly inventory sufficient for at least five boards on the recorded date; the snapshot's tightest part allowance was 174 whole boards. This is unreserved inventory, not a future availability promise. `bom/assembly_availability.csv` records exact manufacturer/MPN/package/class/stock/source/date; schematic symbol properties carry the same selections.

Resistors/capacitors are 0805. Buffers are wide SOIC-20, logic/analog ICs are SOIC-14/16, the rail monitor and I²C buffer are SOIC-8, HV PNPs are DPAK, the regulator is SOT-223, small transistors are SOT-23 and clamp devices are SMA/SMB. Two-pin passives have no meaningful polarity/pinout distinction; their package, value and electrical stress are reviewed separately. Per-component evidence is in `component-verification.csv`.

## Power tree and budgets

```text
J1 5.0–5.25 V / ≥1 A
  ├─ TLV1117LV33 → 3.3 V: ESP32, HC/LVC logic, supervisor, I²C and rail monitor
  ├─ eight input sources, one master stop-loop source and their bias circuitry
  └─ current-reference divider; buffered from raw 12 V
J2 12 V / ≥0.5 A
  ├─ raw analog amplifiers/comparators
  └─ supervisor + hardware RUN gate → high-side PMOS → eight relay coils
External individually fused valve feeds
  └─ relay COM → intended NO valve output → valve RETURN (separate from logic GND)
```

Nine grounded contacts consume about 180 mA wetting current on a host; allow driver/reference losses and ESP32 radio peaks in the 1 A logic budget. Eight nominal 400 Ω relay coils consume about 240 mA. Valve load currents remain external to the board supply headers.

The 5 V-to-3.3 V LDO dissipates about 0.85 W at 500 mA before quiescent losses. The thermal analyzer's inferred load gives about 0.536 W and estimated 117.2 °C junction at 85 °C ambient. That load/copper assumption is not a measured result. Adequate tab copper and thermal verification are required; this estimate is not evidence that the unrouted regulator passes worst load at 85 °C. Ceramic capacitor stability and SOT-223 pin 1 GND / pin 2+tab OUT / pin 3 IN match the selected TLV1117LV, rather than relying on the generic AMS1117 name.

## Analyzer and pin verification

Native schematic export and the source metadata agree on 577 physical components. `scripts/validate_a3.py` checks package/inventory/MPN coverage plus critical terminal connections, source compensation/clamps, relay contacts/suppression, role/monitor isolation, register inhibit and common-A/private-B I²C. All 1,906 checks pass. These are raw-file checks, not physical certification.

Critical manufacturer pin maps checked against the exported terminal connections include:

| Part | Physical mapping / use | Manufacturer evidence |
|---|---|---|
| ESP32-S3-WROOM-1-N8 | 2 VDD; 1/40/41 GND; assigned GPIO functions and module breakout order | Espressif module datasheet, pin table pp.11–12 |
| MJD350T4G | 1 B, 2/tab C, 3 E; collector behind its own field blocker | [onsemi MJD340/MJD350, pp.1–4](https://www.onsemi.com/download/data-sheet/pdf/mjd340-d.pdf) |
| MMBT3904 / MMBT3906 | 1 B, 2 E, 3 C | Exact JSCJ C20526/C2143 manufacturer PDFs, p.1 |
| AO3400A / AO3401A | 1 G, 2 S, 3 D | AOS manufacturer PDFs, p.1 |
| BAS21 / BAT54 | BAS21 1 A, 3 K, 2 NC; BAT54 1 A, 3 K | Nexperia PDFs, pinning pp.1–2; custom BAT54 symbol remapped |
| LM2901B | 3 V+, 12 GND; open-collector outputs pulled to 3.3 V | [TI LM2901, pp.3,6–8](https://www.ti.com/lit/ds/symlink/lm2901.pdf) |
| LM2902DR | 4 V+, 11 GND; four OUT/IN± triplets | [TI LM2902, pp.3,5–6](https://www.ti.com/lit/ds/symlink/lm2902.pdf) |
| TLV803EA30 | 1 GND, 2 RESET_N, 3 VDD; 3.08 V threshold | [TI TLV803E, pp.3–5,8–9](https://www.ti.com/lit/ds/symlink/tlv803e.pdf) |
| HC595 / HC165 | 16 VCC, 8 GND; pin13 actual 595 `/OE`; D0=input/output1 | Nexperia pin/function tables; native serial-map tests |
| HC00/02/14/74 | Manufacturer gate and DFF pin tables; HC74 1 CLR_N, 2 D, 3 CLK, 4 PRE_N, 5 Q | Nexperia PDFs and `verify_hardware_stop.py` |
| LVC244A | 20 VCC, 10 GND; 1/19 OE; exact 8 channel input/output mappings | [TI LVC244A, pp.3–7](https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf) |
| TLV9022DR | 8 V+, 4 GND; 3/2/1 IN+A/IN−A/OUTA; 5/6/7 channelB | [TI TLV9022, pin table and electrical tables](https://www.ti.com/lit/ds/symlink/tlv9022.pdf) |
| PCA9517AD | 1/8 VCCA/B, 4 GND, 5 EN; 2/3 shared SCLA/SDAA, 7/6 private SCLB/SDAB | [NXP PCA9517A, pp.4–7](https://www.nxp.com/docs/en/data-sheet/PCA9517A.pdf) |
| Songle SRD | 1 COM, 2/5 coil, 3 NC, 4 NO; bottom-view translated to actual top-view hole pattern | Exact C30431 Songle drawing; `datasheets/C30431-evidence.png` |
| SS14/SS34 / SMAZ / SMBJ | Cathode band mapped to pad1/K; opposed cathodes in each suppression pair | Exact manufacturer package/polarity sheets and native connected-pin regressions |

Every header pin is listed in `connector-pinouts.md`. Connector numbering is assigned consistently by this design; manufacturer mechanical evidence verifies pitch and package, rather than pretending the vendor defined the project's signal order. All rails and critical source/stop/relay paths are traced in the native contract checks. Footprints and every populated pad net are independently compared after reloading the saved PCB.

## Signal and fault analysis

The current reference is `5 V × (6.8 kΩ || 150 kΩ)/(1 kΩ + (6.8 kΩ || 150 kΩ)) ≈4.333 V`. A spare amplifier buffers it, followed by 200 Ω/10 µF isolation. Each source has a private reference input and OUT-to-IN− compensation capacitor, plus a 10 kΩ/100 nF emitter-sense low-pass at IN+. The independent native-derived loop review demonstrates the gain-sensitive HF problem and its correction; `source-loop-independent-review.md` records before/after fixtures and limitations. Main PNP base pullups return to 5 V before the shunt. The 1 kΩ collector drive resistors prevent continuous contention with the independent PMOS override. The nominal wetting DC model agrees near 20 mA; it does not establish a calibrated minimum or dynamic stability.

Each positive-voltage receiver has a separate BAS21 plus 300 kΩ total series resistance, 6.8 kΩ shunt, 10 nF filtering and 2 MΩ Schmitt feedback. At +100 V the sensed node is roughly 2.2 V, below the 12 V comparator's common-mode ceiling; each 100 kΩ series resistor sees roughly 33 V / 11 mW. At −100 V the blocking diode leakage and shunt bound the negative sense voltage; the hot/cold leakage and power-off result need physical qualification. Selected 0805 parts have substantial steady-state voltage/power margin for these resistor loads.

The early negative-fault readout monitors the grounded-base detector **emitter**, not its PMOS gate. Four 100 kΩ branches give `(UE +3.3 V)/4`; a 30 kΩ/10 kΩ reference equals 3.3 V/4. The healthy emitter is positively biased, while negative faults pull it down before the PMOS shuts the source off. The independent ordering fixture and resistor/offset/bias/TCR bounds are documented by the analog review. Small negative field voltages around ground remain an unspecified diagnostic region; they can read as a closed switch before the fault threshold.

The HV PNP and diode ratings support ±100 V topology, but peak fault dissipation is not simply 20 mA×100 V in every state. Open-source saturation recovery and temperature affect peak current. Backup limiters reduce the modeled surge; qualification must still measure PNP VCE×IC, quench and pulse energy against manufacturer SOA, and ensure compensation-input excursions stay within absolute limits through all power sequences.

## Hardware stop and supply sequencing

`SAFE_PERMIT = NOT(ESTOP_CLOSED_N OR ESTOP_UV_FAULT)`. HC14 converts BUS_ARM_N into an independent arm clock. HC74 D/PRE are held HIGH; its asynchronous clear is the wired LOW override of loop/3.3 V permission and the two logic-powered supply comparators. The 4.7 kΩ clear-source resistor limits TLV9022 sink demand to about 0.731 mA. No supply-valid signal is ANDed into the clock; supply or stop restoration cannot create a rearm edge.

`OE_N = NOT(RUN AND ARM_LEVEL)` drives actual 595 inhibit; its inverse requests coil power. The coil gate's NPN path additionally requires supervisor power-good. A 100 kΩ intermediate-node bleed creates a small off-state bias rather than a perfect open circuit; nominal analysis leaves the PMOS gate about 0.16 V below source, and hot leakage/off-coil voltage needs testing. R4/R5/R71 protect the hard nodes from GPIO backdrive.

The independent native state audit passes 174 checks, including held-arm stop/supply restoration, disconnected UP defaults and 1/2/3/32-module hardware-inhibit propagation. It evaluates 512 corner combinations per rail. Its ±3% supply / ±1% resistor / 2 mV offset / assumed 100 nA bias envelope gives 12 V trips 8.213–9.592 V and 5 V trips 3.951–4.604 V. A separate wider temperature/resistor envelope is recorded by the datasheet review. Bias allowances and fixed-3.3 V LOW behavior are explicitly qualified, not claimed as nonexistent manufacturer maximum rows. See `hardware-stop-logic-review.md` and `rail-monitor-critical-facts.json`.

The supervisor threshold/delay, DFF asynchronous reset width and recovery/removal times, slow ramps, brief brownouts and simultaneous clear-release/clock edges require measurements. Firmware's healthy hold/clear/latch sequence helps normal operation; the hardware architecture remains responsible for stopping a stalled controller.

## Expansion and I²C

J20/J21 share ground and a pin11 NC continuity path; they contain no power pins. The master/expander source and buffer role are fixed physically, with GPIO2 isolated as a monitor. Only the master sources stop wetting; only the last module receives a ground terminator. Incorrect intermediate termination or a grounded bypass can defeat series continuity and must be excluded by assembly/system tests.

UP_ARM_N has a real input-side HIGH pull; CLK/LATCH/CLR/SER default LOW and LOAD defaults HIGH. The return tail defaults HIGH and gives absent-module FAULT=FF. LVC buffers support ordinary 3.3 V/5 V logic and power-off isolation, not ±100 V on the digital pins. Qualify cable resistance, propagation, ground offsets and edge quality at the intended count.

PCA9517A A sides form the common bus on header pins15 SDA /16 SCL; B sides remain private. Select one 2.2 kΩ common pullup pair with JP2 and use 4.7 kΩ private pullups. Start at 100 kHz. Conservative 32-port leakage gives 0.704 V pullup drop, and 400 pF gives approximately 746 ns rise time; 32 A ports can use 224 pF before cable. These are explicit electrical budgets, not an unlimited-I²C-chain promise. Verify buffered LOW levels and address uniqueness. Firmware initializes only the host master and probes only while disarmed.

## PCB, thermal and EMC disposition

Saved-board verification confirms 584 footprints, 200×160 mm outline, 0.5 mm origins, ≥1 mm courtyard spacing, all-layer module antenna keepout and zero routing entities. Native DRC has zero structural and zero schematic-parity findings; 499 reported unconnected items are intentional at this stage. All dedicated IC decouplers have actual VCC-pad-to-cap edge opportunities ≤2.1 mm, recorded in `pcb_decoupling_placement.json`; routing and ground-return loop length still matter.

Rules reserve 0.6 mm field-to-other clearance and 1.25 mm between distinct raw fields, which can differ by 200 V. Internal HV nodes are classified from their physical pin paths. These are fault-tolerance routing constraints, not a certified isolation barrier or an IEC safety-spacing claim. Logic and field returns are deliberately shared.

The full PCB analyzer reports unrouted-net errors and thermal-via/testpoint suggestions. Unconnected nets are expected; do not route merely to silence them. DPAK via-count heuristics are not a universal required count for short pulses; size copper from actual steady/pulse stress during routing. Header access provides testability even though explicit TestPoint footprints are absent. Thermal analysis assesses the LDO but lacks complete device/board parasitic data for the source pulse paths.

Final EMC analysis retains missing-ground-plane and stitching findings. Those remain routing work under the user's no-routing instruction. Earlier real decoupler-placement problems were fixed. Radio/USB cable behavior, return continuity, switching loops and regulatory emission/ESD tests cannot be assessed as passing from an empty copper stack. The EMC score is a heuristic, not a compliance prediction.

## Manufacturing, lifecycle and firmware

The four-layer/top-component placement, clear courtyards, 0805 minimum, SOIC selection, fiducials, accessible headers and verified relay drill pattern support rework and assembly. Use the exact BOM and current mixed SMT/THT service/quote. The header contact rating and separate 1 A valve feeds limit the application despite the relay's larger resistive rating. Verify orientation and current inventory before a production order. [JLC mixed-assembly capabilities](https://jlcpcb.com/capabilities/pcb-assembly-capabilities).

The lifecycle analyzer was run with the available LCSC source. It cannot supply lifecycle/obsolescence status; selected parts return **unknown**. No active/NRND/EOL claim is made. Manufacturer status and distributor credentials must be resolved for a company production release. Inventory availability alone is not evidence of long-term lifecycle.

PlatformIO Arduino firmware built for UART, USB and the 32-module allocation; all 24 host tests pass. They cover serial ordering/polarity, all contact/fault cross-products, startup-zeroing, RUN handshake, stop/role loss, bounded pulses/lease expiry, rollover and disarmed-only I²C scheduling. Nothing was flashed. MCU interrupt/watchdog latency, cable timing and actual actuator behavior remain measured bring-up work.

## False positives and verification limits

- The schematic analyzer's 18 voltage-domain errors assume the 12 V-powered LM2901 outputs drive 12 V. These are open collectors with explicit 3.3 V pullups; raw terminal tracing dismisses that level-shift inference.
- The coil rail's no-source warning misses Q40's switched power path. Raw source/drain tracing proves its source; adding a PWR_FLAG would not fix a circuit error.
- Prior-delta analog no-driver reports treat transistor/resistor pins as passive; native ERC and terminal-level circuitry are the relevant checks.
- Thermal-via, no-plane, stitching and unrouted-net findings are routing-stage requirements/suggestions, not evidence that placement must violate the no-routing instruction.
- Generic SPICE passes 133 detected checks and skips nine unsupported checks in the final report. These chiefly validate simplified detected networks; they do not validate the complete HV current servo or safety mechanism.

Gerber/drill-production/CPL validation was not performed because there is no routed fabrication release. Physical endurance, EMC, thermal, relay life, valve release and safety certification were not performed because no built board/actual valve was supplied. Complete typed datasheet extraction/deep-IC inference was not substituted for manual manufacturer checks; the scout cache is an evidence index, not a blanket verified-spec database. Dynamic source-model convergence and model sensitivity are explicitly retained in the analog evidence. These limits do not negate the corrected raw connectivity and state findings, but they prevent a production-readiness claim.

## Final off-rail discharge disposition

R65/R137–R139 form250Ω from5V toGND; R140 adds1k on3.3V. The illustrative nine-device100µA cutoff-current envelope gives roughly−0.23V including resistor/shunt allowance, versus roughly−0.9V with the former1k bleed. The onsemi0.1mA table is at300V/25°C, so hot100V/disconnected-rail performance remains qualified, not guaranteed. Each5V resistor dissipates27.6mW at5.25V; the change adds20mA logic-input load plus3.3mA on3.3V. Measure floating rails and all-channel faults before release.
