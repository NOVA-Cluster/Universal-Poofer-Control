# A.3 input electrical review

The final native export has **577 components**, SHA256 `82626bce67bed894514820d4328f78b24980fc4462ac153dd3bfe20e93e1a7c2`. All nine field cells, including E-stop, were checked against exported pin-to-net connections. The later digital startup and debug isolation changes leave the numerically tested analog fixture identical; the provenance record retains both hashes.

The contract is grounded dry contacts, active LOW, nominal 20 mA board-sourced wetting, shared return, and continuous ±100 V field-fault survival subject to prototype qualification. This is not the retired active-HIGH TTL input or wetting-sink design.

## Topology and static checks

The source uses a 33 Ω emitter shunt, MJD350 PNP, independent BAS21 output blocker, LM2902 servo, and MMBT3904 driver with a mandatory 1 kΩ collector resistor. The base pull-up is on 5 V before the shunt. A MMBT3906 senses the shunt through an equal 1 kΩ divider and supplies a backup current limit. Both amplifier inputs are deliberately shaped: emitter → 10 kΩ / 100 nF → IN+, and isolated 10 kΩ / 100 nF Miller feedback at IN−. A buffered 200 Ω / 10 µF global reference and BAT54 local guards manage reference coupling and supply cuts.

The raw divider is 6.8 kΩ in parallel with 150 kΩ below a 1 kΩ top resistor. At 5 V it yields 4.33379 V and 20.188 mA shunt current. Including base current and the helper divider gives approximately 20.31 mA nominal collector current at β = 100.

| Condition | FIELD | Contact_N | UV fault | Source current |
|---|---:|---:|---:|---:|
| Open contact | 4.394 V | 3.284 V | 0.1232 V | 0.0127 mA |
| 0.1 Ω contact | 0.002032 V | 0.1232 V | 0.1232 V | 20.32 mA |
| 10 Ω contact | 0.2032 V | 0.1232 V | 0.1232 V | 20.32 mA |
| +100 V fault | 100 V | 3.295 V | 0.1232 V | -1.951e-07 mA |
| −100 V fault | -100 V | 0.1232 V | 3.3 V | 1.05e-07 mA |

DC simulation uses a reduced, centered control gain and ideal reference follower for numerical convergence. It verifies nominal operating direction and passive values; its small errors are not a manufacturer precision or temperature guarantee. Active models remain approximate. Cold/high-gain variations and input offsets must be measured.

The contact comparator has a nominal 27 mV reference. Under the stated 1% resistor, 3.3 V ±3%, 5.5 mV offset and 50 nA bias envelope, a 0.3 V contact remains LOW. A conservative cold opening calculation requires FIELD above about 2.9 V; nominal open FIELD is 4.394 V. BAS21 does not tabulate a cold maximum drop at the very small sensor current, so qualify open detection with all connected receivers. The documented NC chain limit is 10 Ω **total**, not per contact.

## Negative detector and voltage-step guard

UV status reads the detector emitter through four 100 kΩ conductances, giving `(UV_EMITTER +3.3 V)/4`, against the 30 kΩ /10 kΩ reference `3.3 V/4`. Healthy emitter bias is approximately +0.4 to +0.47 V. The conservative resistor/TCR/offset/bias arithmetic gives a trip envelope of −0.197 to +0.202 V. A separate KCL bound keeps the healthy emitter above +0.321 V with a 1 µA leakage qualification envelope. That leakage envelope is an engineering assumption, not a manufacturer hot maximum.

The native-derived ordering fixture, with the servo amplifier held saturated HIGH, detects the tested negative fault before the PMOS source override stops current. This removes the earlier source-OFF / fault-LOW deadband from monitoring the PMOS gate. Near-ground negative voltages remain subject to the detection threshold; the circuit cannot diagnose every ground fault.

C161..169 are 1 nF guards from UV_EMITTER to ground. Without them a fast +100 V step predicted 7.60 V of emitter reversal in a no-avalanche model, exceeding the MMBT3904's 6 V rating. With 1 nF the peak is 0.548 V. The tested negative-step quench remains short after adding the guard.

## Loop stability and surge evidence

Independent AC reconstruction found approximately 2° nominal phase margin and a negative high-gain corner for the original direct-emitter input. The implemented 10 kΩ /100 nF emitter filter raises illustrative margins above 89° with a single opamp pole and above 68° with an additional 3 MHz pole. A high-gain small-perturbation transient changes from persistent oscillation to a settled result. See `analysis/source-loop-independent.json` for model assumptions.

The final nonlinear single-cell model settles near 20.315 mA. The simultaneous nine-cell test settles every channel between 20.3156 and 20.3181 mA in the 25–29 ms window, with a conduction overload near 39 mA. The shared reference is instantiated once; all nine native input filters and emitter guards are included.

For an open-to−100 V transition, the illustrative cold, weak detector, increased-capacitance case drops below 1 mA in 21.15 µs. The trace's conservative peak collector-current/power measures include very short capacitance displacement spikes; the emitter-shunt conduction pulse is about 45 mA. These operating points are below the published 100 µs MJD350 SOA. The actual detector gain, gate charge and overload recovery are not matching guaranteed corners, so this is not a guaranteed shutdown-time bound.

The original simplified unlimited-output model was insufficient: moving 100 nF at 0.5 V/µs asks for roughly 50 mA. The final dynamic model includes output-current limiting and the implemented input filter. TI's official 2024 LM2902 macro was also obtained and parsed, but its ordinary operating point failed and a ramped UIC run exceeded 60 seconds. No successful manufacturer-macro stability result is claimed.

Generic ngspice traces completed the closure/settling window but encountered a timestep failure at an ideal contact-reopening transition. The reopening waveform is excluded from the reported pass evidence. The separate DC open-contact case is valid. Physical reopening, bounce and harness loading remain qualification items.

## Power-off and rail sequencing

The report includes ±100 V with all rails held at zero, each independent rail missing, reverse-leakage injection and both startup orders. Sensor excursions remain small in these tests; a 10 µA reverse-leakage injection puts the negative sensor near −68 mV. That value follows the BAS21 maximum-temperature curve for the proposed −40…85 °C range, not its generic diode model.

The ideal voltage sources clamp off rails to zero. They cannot prove that disconnected rails remain discharged. In particular, hot MJD350 cutoff leakage is not tabulated at the final bias condition; multiple negative faults can pull a floating 5 V rail down through leakage despite its bleed resistor. Positive faults can feed small currents toward logic rails through blocker leakage or hysteresis feedback. Test both floating and grounded-off supply cases, all channels together, and measure every affected rail/input. Do not promote the current simulations into unconditional powered-off, full-temperature guarantees.

The 200 Ω reference isolator limits the initially charged 10 µF reference capacitor's discharge to roughly 22 mA and stored energy to about 94 µJ. TI does not specify an unpowered-output injection limit for the selected legacy LM2902. Local BAT54 guards and rail-fault hardware improve sequencing, but the actual waveform remains a bench check.

U35's logic-powered TLV9022 and the 3.3 V supervisor clear the HC74 RUN latch during raw-rail loss. That safety logic is reviewed separately; field comparators powered from raw 12 V are not claimed functionally valid with their supply absent.

## Reproduction and physical qualification

Run `scripts/simulate_a3_inputs.py`, `scripts/simulate_a3_nine.py`, then `scripts/finalize_a3_input_review.py`. Preserved circuits, logs and compressed traces are in `analysis/revA3_input_spice/`. UV threshold, emitter-capacitor, rail-monitor and independent-loop calculations have separate evidence files referenced by `datasheets/revA3-critical-facts.json`.

Measure wetting accuracy/ripple and mixed contacts over temperature, complete-loop resistance and cold opening, ±100 V edges and continuous hot faults, floating-rail leakage, fault pulse/SOA, startup/brownout/restart, and physical EXP source-disable. Routed-board thermal, field-voltage spacing and EMC remain unverified. Relay/valve release and suppression energy require the actual loads; coil shutdown cannot guarantee a welded contact opens.

## Final rail discharge bounds

R65/R137/R138/R139 are four1k resistors in parallel, giving250Ω from5V toGND; R140 adds1k from3.3V toGND. The illustrative nine-device100µA leakage envelope gives about−0.225V on a floating5V rail (about−0.23V including1% resistance/shunt allowance). The manufacturer0.1mA row is at300V/25°C; it is not a full-temperature100V leakage guarantee. Hot/disconnected-rail tests remain required. At5.25V each5V resistor dissipates27.6mW; total extra supply load is20mA over the former1k bleed, plus3.3mA for3.3V. Stiff-source analog fixtures remain identical; discharge behavior is separately bounded and qualified.
