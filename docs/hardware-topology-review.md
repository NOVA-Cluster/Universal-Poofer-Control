# Revision A.3 hardware topology review

The final design uses eight protected, active-LOW dry-contact inputs with nominal 20 mA sourced wetting current, plus a ninth protected input for the normally closed emergency-stop loop. An edge-clocked hardware latch inhibits both relay-command outputs and relay-coil power. Each relay switches a separately supplied12VDC valve circuit, designed for1A per channel.

This is an editable prototype schematic and an unrouted placement. Native connectivity and component pin maps were checked; analog simulations support the circuit choices within stated model limits. Physical temperature, leakage, loop stability, fault pulses, valve energy, and routed-board thermal/EMC behavior still require qualification.

## Wetting source and continuous field protection

Each path is `5 V →33 Ω→MJD350 emitter→collector→BAS21→FIELD`. The raw reference is `5 V×(6.8 kΩ||150 kΩ)/(1 kΩ+(6.8 kΩ||150 kΩ))`, or4.33379 V at 5 V. This sets20.188 mA in the33Ω resistor. The PNP base pull-up connects to5V **before** the shunt. A separate MMBT3906 backup limiter senses the shunt drop through an equal1k divider and drives the main PNP base toward5V during overload. Its small bypass contribution makes nominal collector current approximately 20.31 mA atβ100.

LM2902 runs from 12 V. Each positive input senses the physical emitter through 10 kΩ with 100 nF to ground. Each negative input uses a separate10k connection to the global reference and 100 nF feedback from that channel's output. A BAT54 guard runs from global reference to the local negative-input node. The output drives an MMBT3904 through 2.2 kΩ; its collector reaches the main PNP base through a mandatory1k resistor that limits contention during a fault clamp.

Spare U22B buffers the raw divider. Two100Ω resistors isolate its output from a 10 µF reference hold capacitor. This separates the nine compensation currents from the high-impedance divider and reduces power-cut input undershoot. Legacy LM2902 limits apply:10 mV full-temperature offset,500 nA bias, and input absolute range−0.3..26 V. Its unpowered output-injection behavior is not guaranteed by the datasheet. [TI LM2902,pp5,12–13](https://www.ti.com/lit/ds/symlink/lm2902.pdf).

The source blocker, sensing blocker and negative-detector blocker use separate internal nodes. All BAS21s are1A/2NC/3K and rated200V continuous reverse. Both sensing and detector field paths contain three100k resistors, spreading the approximately 100 V fault across three parts; each dissipates about 11mW. [Nexperia BAS21,pp1–4](https://assets.nexperia.com/documents/data-sheet/BAS21.pdf).

The negative detector is an MMBT3904 with base at ground, emitter connected to FIELD through 300 kΩ and a BAS21, and a 100 kΩ emitter return. Its collector pulls the AO3401 gate down against a 68 kΩ return to5V. The PMOS then clamps the main PNP base toward5V, independently of firmware and the regulator amplifier.

C161–169 add 1 nF from each detector emitter to ground. This is necessary for voltage steps: a generic no-avalanche model without these capacitors predicted7.60 V emitter reversal after a fast+100 V edge, above the detector's6V rating. With1nF the modeled peak is0.548 V. The corresponding negative-fault delay remains short; see the numerical report.

## Contact and fault detection

The contact receiver is `FIELD→BAS21→300 kΩ→SENSE`, with 6.8 kΩ and 10 nF to ground. Its LM2901B uses `IN+=SENSE` and `IN−=3.3 V×3.3 kΩ/(400 kΩ+3.3 kΩ)`, giving approximately 27 mV. Two1M resistors provide positive feedback from the3.3 V open-collector output to SENSE. LOW means a grounded contact.

The UV status receiver monitors the **detector emitter**, not its PMOS gate. Four100k conductances give `UVSENSE=(UV_EMITTER+3.3 V)/4`. The comparator reference is `3.3 V×10 kΩ/(30 kΩ+10 kΩ)=3.3 V/4`; fault is HIGH when the emitter falls sufficiently negative. The network biases a healthy detector emitter positive, normally about 0.4–0.47 V. This supplies healthy margin and makes the diagnostic assert before the source shuts off.

The conservative arithmetic envelope includes±1% resistors plus65°C×100ppm/°C,5.5 mV comparator offset,50 nA bias and 3.3 V±3%. The emitter trip lies between approximately−0.197 and+0.202 V. A healthy-node KCL check remains above 0.321 V even with a 1 µA reverse-leakage qualification envelope and the field blocker treated as a short toward ground. The1µA envelope is a test assumption, not a manufacturer hot-leakage maximum. Tested detector corners flag faults before the source-off point; the previous gate-monitoring deadband has been removed.

At+100 V, contact_N is HIGH and the source is reverse blocked. At−100 V, UVFAULT is HIGH and the source is clamped off. Near-ground negative voltages are limited by the analog detection threshold; the design does not claim to distinguish every ground fault or to provide galvanic isolation.

## Hardware emergency stop and supply loss

`SAFE_PERMIT=NOR(ESTOP_CLOSED_N,ESTOP_UV_FAULT)`. U34 is a 74HC74 rising-edge D flip-flop with D tied HIGH and preset inactive. STOP, the3.3 V supervisor, or U35 raw-supply monitoring assert its asynchronous clear. A loop restoration while ARM is held cannot produce a fresh clock edge and cannot restart outputs. The former RC arm pulse and SR latch are absent.

`OE_N=NAND(HW_RUN_LATCH,ARM_LEVEL)` inhibits the74HC595. Its inverse requests coil power. A separate supervisor-controlled NPN sits in series with the coil PMOS gate sink, providing an additional hardware power-good condition. The coil PMOS gate has a source pull-up and an8.2 V VGS clamp.

U35 is TLV9022DR on3.3 V. It monitors raw12V through 200 kΩ/10 kΩ and raw5V through(100 kΩ||1M)/10 kΩ against `3.3 V×10 kΩ/(68 kΩ+10 kΩ)`. Nominal trip points are8.885 V and 4.269 V. Open-drain faults override RUN_CLEAR_N; R150 (4.7 kΩ) limits contention below 0.74 mA. The full-temperature table reports175mV at 4 mA under its default5V test condition;3.3 V output curves are typical, so the actual3.02..3.4 V LOW level remains a bench check. The conservative rail-divider envelope retains positive overdrive at healthy5.0 V and 12.0 V. [TI TLV9022,pp4,7,11,16](https://www.ti.com/lit/ds/symlink/tlv9022.pdf).

GPIO18 and 21 observe permission and RUN through resistors. GPIO2 reads the physical role selection through 100 kΩ. Only MASTER supplies E-stop loop wetting; EXP hardware clamps its source driver. Downstream ARM forwards actual local OE_N, so a local hardware stop propagates even if firmware stalls. R124–129 bias all raw upstream buffer inputs, and R130–135 independently bias the MCU-facing inputs. Clock/data/latch/clear default LOW; arm/load default HIGH. Missing upstream connections and an unbooted ESP32 therefore have defined inhibit states. J5's OE monitor is separately isolated by R136 (100 kΩ).

The complete closed NC chain, including contacts, connectors and wiring, is specified at**≤10 Ω total**. A10Ω per-contact allowance cannot be multiplied across32 modules. Exactly one MASTER source and one final loop termination are required.

## Relays, suppression and interfaces

Songle contact numbering is1COM,2/5coil,3NC and 4NO. The project footprint corrects the stock-symbol/footprint NO/NC mismatch. Valves use NO contacts. The10A resistive contact rating does not establish an inductive-load endurance rating or a 10A rating for the2.54mm headers; each valve path is designed for1A.

Each coil flyback diode and 8.2 V zener share cathodes, allowing a higher release clamp than an ordinary diode. Each valve uses SS34 plusSMBJ8.0A with cathodes joined, diode anode at return and TVS anode at valve NO. An8V TVS must not be placed directly across an energized12V valve. Actual coil/valve inductance and switching repetition determine release time and energy. Coil shutdown cannot open a welded contact; use an independent valve-power disconnect where that failure must stop flow.

SPI chain buffering uses three SN74LVC244ADWR wide-SOIC20 parts with 1.27mm pitch and powered-off Ioff support. I²C uses PCA9517AD,118: shared UP/DOWN bus on port A, private MCU port B, one selectable2.2 kΩ common pull-up pair, and local4.7 kΩ pull-ups. Port B-to-B connection is prohibited. Start at 100 kHz and qualify the global≤400 pF bus budget. See `docs/i2c-interface-review.md`.

## Simulation evidence and remaining qualification

Native-derived nonlinear tests settle the filtered single source near 20.315 mA. Simultaneous nine-channel closure settles all channels near 20.316 mA, with a modeled overload transient near 39 mA. Independent AC analysis found the original direct-emitter loop nearly unstable, with negative margin in a high-gain corner. The implemented10k/100n emitter filter raises illustrative margins above 68° even with an added opamp pole. Small-perturbation and nonlinear results agree on the filter's benefit.

The generic transistor, diode and opamp models are engineering approximations. TI's2024 LM2902 macro was downloaded and parsed, but the ngspice operating point failed and the ramped UIC run reached the60-second limit. No manufacturer-macro stability pass or guaranteed maximum shutdown time is claimed. Quench, leakage and phase-margin results must not be promoted into production guarantees.

Qualify loop settling and ripple across temperature/parts, fast and continuous±100 V faults, floating/disconnected supplies, source pulse/SOA and all-channel heating, raw-supply clear/restart, E-stop bounce/role/chain behavior, actual relay/valve release and suppression energy. The ideal supply sources in SPICE hold off rails at zero; they do not prove that leakage leaves disconnected rails discharged. Final routing must also verify200V differences between simultaneously opposite raw-field faults, return paths, thermal copper and EMC. The PCB is intentionally unrouted.

Exact native hashes, pin maps and numerical traces are recorded in `datasheets/revA3-critical-facts.json`, `analysis/revA3_input_simulation.json`, `analysis/revA3_input_spice/nine_final_summary.json` and `analysis/source-loop-independent.json`.

## Final rail discharge bounds

R65/R137/R138/R139 are four1k resistors in parallel, giving250Ω from5V toGND; R140 adds1k from3.3V toGND. The illustrative nine-device100µA leakage envelope gives about−0.225V on a floating5V rail (about−0.23V including1% resistance/shunt allowance). The manufacturer0.1mA row is at300V/25°C; it is not a full-temperature100V leakage guarantee. Hot/disconnected-rail tests remain required. At5.25V each5V resistor dissipates27.6mW; total extra supply load is20mA over the former1k bleed, plus3.3mA for3.3V. Stiff-source analog fixtures remain identical; discharge behavior is separately bounded and qualified.
