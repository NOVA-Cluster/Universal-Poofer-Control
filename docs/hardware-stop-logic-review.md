# Hardware stop logic review — revision A.3

The final native netlist passes **174 connectivity and state checks**. The audit found three restart/connection problems during the redesign; all three are corrected in the reviewed export. This is a Boolean and DC-topology review, with physical timing and leakage qualification still open. It is not a safety certification or a guaranteed shutdown-time result.

The reviewed KiCad 10.0.5 export is dated `2026-10-03T15:49:08`, with 577 components and 432 nets. Its SHA-256 is `82626bce67bed894514820d4328f78b24980fc4462ac153dd3bfe20e93e1a7c2`. The exact pins, gate functions, test trajectories, and engineering assumptions are preserved in [the machine-readable review](../analysis/hardware-stop-state-review.json).

Reproduce it from the project root:

```sh
python3 scripts/verify_hardware_stop.py --self-test
```

The script reads the native netlist directly. It derives gate nets from physical pin numbers using manufacturer pin tables, checks the actual role/forwarding and transistor connections, and fails if those connections or modeled invariants change. A failed parse/model updates the report to `cannot-complete`, preventing an old passing report from being mistaken for current evidence.

## Corrections established by this review

| Problem found | Final correction | Evidence |
|---|---|---|
| A pulse-qualified NOR latch could rearm if a stop cleared while the original arm pulse was still HIGH. | U34 is a positive-edge 74HC74. Stops asynchronously clear Q; releasing clear with a held clock cannot set Q. The RC pulse network is removed. | U34 pins 1–5; held-arm NC, UV, PG, 5 V, and 12 V trajectories. |
| An unplugged expander's enabled upstream receiver had floating ARM/control inputs; a pullup after the buffer could not define its driven output. | R124–R129 bias the receiver inputs: ARM/LOAD HIGH; CLK/LATCH/CLR/SER LOW. | Native UP input nets and role-selection checks. |
| 12 V loss while 3.3 V remained present could leave RUN armed, because unpowered receiver outputs were not guaranteed. | U35 remains powered by 3.3 V and independently monitors 12 V and 5 V. Either open-drain fault output forces `/CLR` LOW. The final low-voltage comparator is TLV9022DR. | U35 pins 1–8, R150–R158, supply-loss/restoration trajectories. |

## Actual gate and flip-flop functions

| Part/unit | Native pins | Function |
|---|---|---|
| U31A, HC02 | Inputs 2/3; output 1 | `SAFE_PERMIT = NOT(ESTOP_CLOSED_N OR ESTOP_UV_FAULT)` |
| U31B, HC02 | Inputs 5/6; output 4 | `STOP_REQUEST = NOT(SAFE_PERMIT)` |
| U32D, HC14 | Input 9; output 8 | `PG_FAULT = NOT(PG_RESET_N)` |
| U31C, HC02 | Inputs 8/9; output 10 | `RUN_CLEAR_DRIVE_N = NOT(STOP_REQUEST OR PG_FAULT)` |
| U35A, TLV9022 | Sense `IN+` 3; reference `IN−` 2; output 1 | LOW when divided 12 V falls below reference. |
| U35B, TLV9022 | Sense `IN+` 5; reference `IN−` 6; output 7 | LOW when divided 5 V falls below reference. |
| R150/U35 | U31 output → 4.7 kΩ → U34 `/CLR`; both drains join `/CLR` | `RUN_CLEAR_N = RUN_CLEAR_DRIVE_N AND RAIL12_OK AND RAIL5_OK` as a wired LOW override. |
| U32A, HC14 | Input 1; output 2 | `ARM_LEVEL = NOT(BUS_ARM_N)` |
| U34A, HC74 | `/CLR` 1; D 2 HIGH; CLK 3; `/PRE` 4 HIGH; Q 5 | Q clears asynchronously; a fresh rising CLK captures HIGH only with clear released. |
| U30D, HC00 | Inputs 12/13; output 11 | `RLY_OE_ACTUAL_N = NOT(HW_RUN_LATCH AND ARM_LEVEL)` |
| U32C, HC14 | Input 5; output 6 | `COIL_EN = NOT(RLY_OE_ACTUAL_N)` |
| U32E, HC14 | Input 11; output 10 | `ROLE_RX_OE_N = NOT(LOCAL_MASTER_N)` |

The current design contains no HC32 OR package. The earlier OR/pulse-latch circuit has been replaced; the verifier retains OR pin/function support so future additions are interpreted explicitly. U34's second flip-flop has `/CLR` held LOW, `/PRE` HIGH, and D/CLK grounded. Unused logic inputs are grounded; unused outputs are unconnected. U35 is a dual comparator with both units used; pin 8 is 3.3 V and pin 4 is GND.

Pin/function evidence: [Nexperia HC02](https://assets.nexperia.com/documents/data-sheet/74HC_HCT02.pdf), [HC00](https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf), [HC14](https://assets.nexperia.com/documents/data-sheet/74HC_HCT14.pdf), [HC74, pp. 3–4](https://assets.nexperia.com/documents/data-sheet/74HC_HCT74.pdf), and [TI TLV9022, p. 4](https://www.ti.com/lit/ds/symlink/tlv9022.pdf). Local manufacturer copies are `datasheets/C27597.pdf` and `datasheets/TI-TLV9022.pdf`.

## State behavior and recovery

| Event | RUN after the event | Output behavior |
|---|---|---|
| Logic startup with supervisor reset asserted | LOW, independent of initial Q assumption | OE HIGH; strong coil-gate path disabled. |
| Healthy loop/supplies, new ARM rising edge | HIGH | OE follows the arm level; firmware must already have latched zero command bytes. |
| NC loop opens, UV bit asserts, or any monitored supply faults | LOW | Hardware inhibits without requiring MCU code. |
| Fault clears while ARM remains held | Remains LOW | Old commands cannot resume. |
| Arm edge occurs while clear is asserted, then supplies recover | Remains LOW | A later fresh arm edge is required. |
| ARM is deasserted after successful arming | May remain HIGH | OE is still HIGH because ARM_LEVEL is LOW. |

The verifier checks all 16 static NC/UV/PG/ARM combinations, repeated held-clock restoration events, and fresh rearming. It also models 1, 2, 3, and 32 buffered boards. A master NC-loop stop inhibits every downstream board, including boards whose own receivers still report healthy. A local-only stop or supply fault inhibits that board and everything downstream; upstream shutdown requires the shared NC loop or another upstream indication. GPIO21 confirms the local board's RUN state, not every remote board.

U52 input pin 15 receives **actual local OE**, not the raw MCU ARM signal. Its output pin 5 passes through R85 to `DOWN_ARM_N`/J21 pin 7. The regression test demonstrates that forwarding raw ARM would leave a healthy downstream board enabled after its predecessor's RUN had cleared.

Do not gate the clock with PG or permission. Their restoration with ARM held could create a new clock edge. The final hardware instead applies those conditions to asynchronous clear. Current firmware's GPIO21 acknowledgement refuses an arm while hardware clear holds Q LOW; it then raises GPIO15 again. Permission release alone does not arm the firmware.

**Recovery remains a physical timing requirement.** The HC74 datasheet specifies reset recovery, minimum reset/clock pulse widths, and data setup/hold requirements. At 2 V, recovery minima are 40 ns through 85 °C and 45 ns through 125 °C; at 4.5 V they are 8/9 ns. The report flags an abstract event where clear releases simultaneously with clock rising; its ideal transition is not a guarantee of real behavior. Test supply/stop release near arm edges, contact bounce, asynchronous path skew, and the real logic-rail/load conditions. The timing table and waveform definitions are in [HC74, pp. 7–9](https://assets.nexperia.com/documents/data-sheet/74HC_HCT74.pdf).

## Independent supply monitoring and DC corners

The common reference is `3.3 × 10 kΩ/(68 kΩ+10 kΩ) = 0.4231 V`. The 12 V divider uses two series 100 kΩ resistors over 10 kΩ. The 5 V divider uses `100 kΩ || 1 MΩ = 90.909 kΩ` over 10 kΩ. Both positive inputs are sense nodes, so undervoltage sinks the collector LOW.

For each rail, `Vtrip = (VREF + offset + sense-bias error) × (Rtop+Rbottom)/Rbottom`. The script enumerates 512 resistor/supply/offset/bias combinations per rail, including the two comparator inputs loading the reference.

| Rail | Nominal trip | Calculated engineering band | Normal-supply minimum used |
|---|---:|---:|---:|
| 12 V | 8.885 V | 8.213–9.592 V | 10.8 V |
| 5 V | 4.269 V | 3.951–4.604 V | 4.75 V |

Assumptions are 3.3 V ±3%, 1% resistors, ±2 mV offset, and a conservative 100 nA engineering allowance per input. TLV9022 publishes 5 pA typical input bias without a guaranteed full-temperature maximum, so the 100 nA allowance must be qualified rather than called a manufacturer limit. The largest calculated sense voltages are 0.641 V at 13.2 V and 0.555 V at 5.5 V, well inside the rail-to-rail input range. The low-voltage device operates from 1.65–5.5 V, removing the earlier LM2901B common-mode/supply-range concern. [TI TLV9022, pp. 7, 11](https://www.ti.com/lit/ds/symlink/tlv9022.pdf).

R150=4.7 kΩ bounds ideal sink demand to about 0.731 mA with a +3% rail and −1% resistor. **These are engineering corner checks, not a complete physical transfer/timing proof.** TLV9022's full-temperature offset limit is ±2 mV at the stated 1.8 V/5 V test points, and its 4 mA LOW-output limit is 175 mV in the 5 V-default table. The actual 3.3 V load is substantially smaller, but still validate `/CLR` LOW level, trip thresholds, bias, response, and supervisor-boundary behavior over temperature. The published switching delays are typical values and do not establish maximum shutdown time. [TI TLV9022, pp. 11–12](https://www.ti.com/lit/ds/symlink/tlv9022.pdf).

## Coil gate, role, and MCU monitor isolation

The native high-side path is Q40 source/pin 2 on `+12V_IN`, drain/pin 3 on `+12V_COIL_SAFE`, and gate/pin 1 on `COIL_GATE`. Q41 pin 3 sinks the gate through R111; its emitter/pin 2 joins Q42 collector/pin 3. Q42 emitter/pin 2 is grounded. Q41 receives COIL_EN through R112, and Q42 receives supervisor reset-release through R114. The script checks every relay's positive coil connection to Q40's drain and finds no direct supply header on the gated coil rail. MMBT3904's manufacturer pin table is 1 base, 2 emitter, 3 collector (`datasheets/JSCJ-MMBT3904.pdf`, p. 1).

R116 is a 100 kΩ emitter return around Q42, so Q42 OFF is **not an ideal open circuit**. With Q41's emitter bounded by 3.3 V+3%, R116−1%, and gate pullup R110+1%, weak gate bias is bounded to approximately `4.747 kΩ × 3.399 V/99 kΩ = 0.163 V`. That excludes transistor hot leakage, back-powering, and invalid logic rails. AO3401A's smallest threshold magnitude is 0.5 V under its 25 °C test conditions; this does not guarantee hot off-state coil current. Measure PMOS gate/source voltage, residual coil voltage/current, and absence of relay pickup/hold during startup, brownout, and removal of each supply. See `datasheets/AOS-AO3401A.pdf`, pp. 1–2.

JP1 physically grounds `LOCAL_MASTER_N` for host mode; R70 pulls it HIGH for the default expander role. U50 local drivers and U51 upstream drivers have complementary hardware enables. GPIO2 monitors the role through R71=100 kΩ; it does not connect directly to the role net. An ordinary LOW counterdrive with JP1 open leaves at least 0.907×VCC at the physical role node under the stated 1% resistor corners. This resistance calculation is separate from arbitrary-voltage protection.

GPIO18 and GPIO21 likewise connect through R4/R5=10 kΩ to the protected permission and RUN signals. The script confirms that their module and debug-monitor nets are distinct from the hardware source nodes. These are resistor-isolated logic monitors, not galvanic isolation or ±100 V MCU-pin interfaces.

## Scope and remaining tests

This audit ran native pin-connectivity assertions, settled Boolean event simulations, positive-edge state tests, ideal-DC supply-monitor sign tests, chain propagation tests, regression sensitivity tests, and enumerated resistor/supply corners. It did not rerun the parent project's schematic/PCB/EMC/thermal/SPICE/lifecycle workflows. It does not assess field-receiver ±100 V threshold timing, cable length/capacitance, propagation delays, invalid CMOS supply behavior, PMOS/BJT SOA, relay/valve dynamics, or welded contacts.

Hardware qualification must exercise all supply permutations, slow ramps/brownouts, stop release near arm edges, disconnected upstream headers, role defaults/counterdrive, and every board position in a chain. Record the measured `/CLR` LOW level, RUN state, actual OE, PMOS gate/source voltage, coil current, and relay/valve release times. Removing coil power cannot open a welded relay contact; an appropriate independent valve-power disconnect remains necessary when that failure must stop flow.

## Final startup receiver bias correction

R130–R135 now bias all six local MCU-facing U50 inputs, including GPIO15 HIGH/inhibited, when the ESP32 is reset or never boots. A pull after an enabled buffer does not define a floating receiver input. The audit checks both upstream and local receiver pulls and verifies that a high-impedance MCU cannot clock RUN on supervisor release. The final native audit passes 174 checks on the 577-component export.

## Final protected OE observation

J5 pin9 observes OE through R136=100k. It has no direct connection to the hard OE/coil-enable node. Ordinary 0…VCC counterdrive is limited below35µA. Use a high-impedance probe; this is observation, not an external enable control. The final audit includes this resistor and verifies no direct hard-OE header.
