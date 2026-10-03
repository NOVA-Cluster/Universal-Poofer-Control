# Wetting-current loop: independent compensation review

Review date: 2026-10-03. Scope: the nine identical A.3 wetting sources, comparing the preserved original circuit with the implemented correction in the final 577-component native netlist. This reviewer changed only analysis artifacts; the main task implemented the schematic correction.

**Finding and correction:** the original 10 kΩ / 100 nF feedback network did not adequately isolate the high-gain transistor path at high frequency. The unfiltered emitter-sense topology had essentially no simulated stability margin at nominal gain and became unstable at illustrative high transistor gain. The final circuit now includes a 10 kΩ series resistor from each MJD350 emitter to its LM2902 noninverting input, with a 100 nF capacitor from that input to ground. All nine implemented filters pass direct native-netlist connectivity, value and 0805 footprint checks. The existing 2.2 kΩ NPN drive resistor and 10 kΩ / 100 nF local inverting-input compensation are retained. Confidence: high for the feedback mechanism; medium for numerical simulation margins; physical margin requires bench qualification.

## Evidence and mechanism

The preserved original native netlist maps each LM2902 noninverting input directly to the corresponding MJD350 emitter. The final native netlist instead maps emitter → 10 kΩ resistor → `INn_EMIT_F` → LM2902 noninverting input, with a 100 nF return to ground. Filter resistors are R1024/R1054/R1084/R1114/R1144/R1174/R1204/R1234/R1264; capacitors are C141–C149. The amplifier output drives an MMBT3904 through 2.2 kΩ. Its collector pulls the MJD350 base down through 1 kΩ; another 1 kΩ pulls that base to 5 V before the 33 Ω current shunt. The 100 nF compensation capacitor connects the amplifier output to its private inverting input, which returns through 10 kΩ to the buffered current reference. The BAT54 guards this private node against negative excursion relative to the shared reference. The backup MMBT3906 senses half the shunt voltage.

For small signals, denote the inverting transistor/emitter plant by `G(s)` and the output-to-inverting-input capacitor feedback by `H(s)`. The return ratio is `T(s) = A(s) [H(s) − G(s)]`. The capacitor branch approaches unity at high frequency, but the direct emitter branch still supplies an additional inverted gain of about 23 at low frequency in the nominal model. That plant contributes substantial phase lag near the amplifier crossover. The capacitor alone does not make the full circuit a dominant-pole integrator.

The added emitter filter makes the transistor contribution `G(s)/(1+sRC)`. Its corner is approximately 159 Hz; the unfiltered high-frequency unity feedback branch remains intact. The outer current loop controls the DC emitter voltage, while the LM2902's local loop handles its own high-frequency response. The filter leaves the autonomous negative-field fault clamp and backup peak limiter connected to the actual transistor nodes.

## Independent AC simulations

The preserved native fixture records netlist SHA-256 `b90e80cdd2f7ed641f507a0a3712b8f8555d7761b5ebe20b295cc2c7e850b111`. The script keeps that original fixture so the comparison remains reproducible after correction. The script `scripts/analyze_source_loop.py` reconstructs the operating transistor plant from the native exported netlist fixture, biases it with the closed DC fixture, then injects AC before a 50 Ω amplifier output resistance. It measures both feedback paths. A 100 kV/V single-pole amplifier with 1.2 MHz GBW is applied to that return signal. An illustrative second pole at 3 MHz checks sensitivity to additional amplifier phase lag. Final netlist SHA-256 is `82626bce67bed894514820d4328f78b24980fc4462ac153dd3bfe20e93e1a7c2`. Four additional AC fixtures were generated directly from that final native export; their results match the corrected comparison fixture. All 28 AC fixtures, four small-perturbation transient fixtures and their logs are retained in `analysis/source_loop_independent/`; machine-readable results are in `analysis/source-loop-independent.json`.

| Candidate | Nominal phase margin, single pole | High-gain phase margin, single pole | Nominal margin, added 3 MHz pole |
| --- | ---: | ---: | ---: |
| Native 2.2 kΩ drive, direct emitter sense | 2.1° | −6.9° | −23.1° |
| 10 kΩ drive, direct emitter sense | 47.0° | 32.1° | 28.4° |
| 47 kΩ drive, direct emitter sense | 85.6° | 85.9° | 65.7° |
| Implemented 2.2 kΩ drive + 10 kΩ / 100 nF emitter filter | 89.6° | 89.5° | 69.1° |

Nominal transistor assumptions: MJD350 β = 100, MMBT3904 β = 150. Illustrative high gain: β = 240 / 300. Further fixtures use β = 30 / 100 and increased PNP transit time. The implemented filtered circuit stays near 89.5° with the one-pole amplifier, and at least 69.0° with the illustrative second pole. These numbers are **model results**, not guaranteed margins of production parts.

A separate small-perturbation transient uses the same nonlinear transistor fixture and single-pole amplifier, with output voltage bounded but no slew or output-current limit. A 1 µA emitter-node disturbance is applied at 1 ms. At nominal gain the original circuit's lightly damped response eventually decays, consistent with the very small positive AC margin. At illustrative high gain, the original circuit oscillates spontaneously at 15.80–25.20 mA over the final 3–4 ms interval. The filtered circuit settles to 20.43423 mA, with less than 0.000001 mA numerical variation in that late interval. This demonstrates the instability mechanism and its removal in the model; it does not validate contact-close saturation recovery or current limiting in real hardware.

Increasing only the NPN base resistor to 10 kΩ is insufficiently robust in this check. A much larger value reduces plant gain, but changes required amplifier swing, saturation recovery, available drive and fault-clamp contention. The implemented emitter filter directly removes the identified mechanism while preserving the selected drive and independent fault override.

## Datasheet and model limits

The selected device is the legacy **LM2902DR**, not the newer LM2902B. The local TI datasheet `datasheets/TI-LM2902.pdf`, SLOS066AE revised September 2025, page 12 states maximum full-temperature input offset of 10 mV and input bias magnitude of 500 nA. Pages 13 and 23 give typical GBW of 1.2 MHz and slew rate of 0.5 V/µs. The legacy output stage's sinking capability is strongly dependent on its output voltage; a fixed 50 Ω output resistance and unlimited output current do not reproduce that behavior.

The filter's 10 kΩ resistor adds up to 5 mV bias-related error under the datasheet's maximum 500 nA assumption, equivalent to about 0.15 mA in a 33 Ω shunt, in addition to the existing reference-input bias and offset errors. This is compatible with nominal rather than precision-guaranteed 20 mA wetting current; the final tolerance budget should include it explicitly.

The transistor models are generic Gummel–Poon approximations with capacitance and transit-time terms. Manufacturer β limits are stated at different current/voltage conditions than this 20 mA operating point, so the swept β values are illustrative sensitivity checks. The extra 3 MHz amplifier pole is an illustrative perturbation, not a datasheet-derived pole. The one-pole model's nominal 90° unity-loop margin overstates a real amplifier's margin, so it must not be represented as hardware verification.

A separate native-derived filtered-cell contact transient with a synthetic 5 mA output-current limit completed and settled to 20.31509–20.31513 mA over 25–29 ms (`analysis/candidate_emitter_filter.json`). That fixture was generated as a candidate before the final native export; the actual implemented filter topology has since passed the independent checks above. This adds nonlinear model evidence for settling, while the nine-loop final-native transient is tracked separately by the main review.

A separate reviewer is testing the official TI LMX24_LM2902 Rev. A macro-model from [TI SGLM009](https://www.ti.com/lit/zip/SGLM009), revised June 24, 2024. At the time of this review, that model had failed ordinary operating-point convergence, and a ramped-supply UIC transient had not yet produced a completed report. No manufacturer-model stability claim is made here.

Before qualification, observe current at contact close/open, supply transitions, field faults and simultaneous nine-channel switching over temperature and part samples. Verify settling, any oscillation, limiter peak and PNP pulse energy. The PCB is only at placement stage, so trace/coupling parasitics are not included.

Final577-component re-run confirms all nine filters and four actual-native AC fixtures after the detector guards and rail/discharge changes. Minimum illustrative additional-pole margin remains68.99degrees. The baseline fixture is retained for comparison; subsequent protection does not have to produce bit-identical intermediate metrics.
