# A.3 I²C interface evidence

PCA9517AD,118 (C2802638) provides a rework-friendly SO8 package. Wire the shared UP/DOWN bus to port A and each ESP32 to its private port B. NXP permits multiple port-A connections; joining port-B outputs is prohibited. Unpowered pins are high impedance. See [NXP datasheet, pp.1,4,6–7](https://www.nxp.com/docs/en/data-sheet/PCA9517A.pdf).

Use one selectable2.2k common-bus pull-up pair and separate local-B pull-ups. Budget the entire common bus below400pF and verify rise time at the selectedclock. For32buffers,2.2k tolerates the specified10µA-per-port high leakage better than4.7k. At400pF it gives~746ns rise time; use100kHz initially. The32Aports consume up to224pF beforecables. [I²C timing specification,p44](https://www.nxp.com/docs/en/user-guide/UM10204.pdf). Local GPIO outputs must pull below0.4V during contention; the buffer's0.6V maximum B-side outputLOW fits the ESP32's0.825V inputLOW limit at3.3V. Power/reset changes may interrupt a transaction and require bus recovery. [NXP datasheet, pp.5,10](https://www.nxp.com/docs/en/data-sheet/PCA9517A.pdf).

Exactstock records and pin maps are in `bom/i2c-candidate-parts.json` and `datasheets/i2c-critical-facts.json`. No ±100V field-protection claim applies to I²C pins.
