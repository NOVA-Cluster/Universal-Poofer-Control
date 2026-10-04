# Customer guide fact audit — revision A.3

Internal editorial evidence for the first-use hardware guide, checked on
2026-10-03. This records the implemented hardware and firmware contract; it is
not a new electrical specification or qualification result.

## Sources and scope

- Native KiCad netlist: `analysis/Universal_Poofer_Control.net`, exported
  `2026-10-03T15:49:08`, 577 physical components, 432 nets, 24 sheets. SHA-256:
  `82626bce67bed894514820d4328f78b24980fc4462ac153dd3bfe20e93e1a7c2`.
- `docs/connector-pinouts.md`: all **37 headers/jumpers and 166 pin rows** were
  compared with the native export; zero mismatches and no omitted header.
- `analysis/hardware_contract.json`, `firmware/include/board_pins.h`,
  `firmware/src/main.cpp`, and the `PooferControl` headers were read directly.
- Electrical limitations were cross-checked against the current input,
  topology, hardware-stop, I²C, and full hardware-review documents.

No functional hardware or firmware was changed by this audit. Stale comments in
three firmware files were corrected after root authorization. No fabricated board was
tested. The PCB is still an unrouted placement, so the customer guide must label
this revision as an engineering prototype pending production qualification.

## Header and supply facts

| Interface | Customer connection |
|---|---|
| J1 | Pin 1 regulated 5.0–5.25 V, ≥1 A; pin 2 logic/input GND. |
| J2 | Pin 1 nominal 12 V DC, ≥0.5 A for analog circuitry and relay coils; pin 2 logic/input GND. This header does not feed the eight valve loads. |
| J11–J18 | Pin 1 FIELD; pin 2 GND. Dry contact closes between those pins. Channel 1 is J11, channel 8 is J18. |
| J9 | Pin 1 ESTOP_FIELD; pin 2 ESTOP_CHAIN_OUT. External normally closed contact between pins; this is not a FIELD-to-GND switch on every board. |
| J10 | Pin 1 ESTOP_CHAIN_OUT; pin 2 GND. Ground termination on the last board only. |
| J31–J38 | Pin 1 COM, pin 2 NO, pin 3 NC auxiliary. Each COM receives its own externally fused valve feed. |
| J41–J48 | Pin 1 NO/valve positive; pin 2 valve RETURN/negative. RETURN must be connected to that valve supply's negative and is separate from logic GND. |
| J6 | Pin 1 EN/reset, pin 2 GND, pin 3 BOOT/GPIO0. |
| J7 | Pin 1 TX/GPIO43, pin 2 RX/GPIO44, pin 3 GND. Use a 3.3 V logic UART adapter with RX/TX crossed; leave adapter power disconnected. |
| JP1 | Closed = host, absent/open = expander; physical selection, monitored on GPIO2. |
| JP2 | Closed = selected common I²C pullup provider; one provider, normally host. Coordinate with external peripheral pullups. |

The valve circuit connection requires **both** the COM positive feed and RETURN
negative connection. Merely powering J2 and attaching a valve to J41 does not
power the valve. Each channel is intended for a 12 V DC valve up to 1 A; the
relay's 10 A resistive-contact rating does not increase header or inductive-load
capability. Do not use the auxiliary NC terminal for a shutdown-controlled valve.

Use native connector pin numbers and the square/pin-1 mark. GPIO numbers,
ESP32 module pad numbers, and connector pin numbers are three different things.
All 40 native comparisons confirm J3 pin N matches U1 physical pad N and J4
pin N matches U1 physical pad N+20. These physical pad numbers are not GPIO
numbers; for example J4 pin 3/U1 pad 23 is GPIO21. Their 3.3 V/EN/strap pins make an
arbitrary plug-in breadboard cable hazardous; use the complete pin reference.

The expansion connectors have **no power pins**. Independently supply each
module's J1 and J2 and establish the common logic reference through the chain.
Do not repurpose ground pins as a shared supply feed or parallel local regulators.

## Expansion wiring and jumpers

Connect J21 DOWN to the next board's J20 UP, matching all 16 pin numbers. This is
not a standard SPI, I²C, or IDC accessory connector. Verify pin 1 and cable
continuity with power off; do not assume that a generic cable is pin-for-pin.

| Pins | Function |
|---|---|
| 1, 2, 10, 12, 13, 14 | Logic/input GND. |
| 3 | Shift clock. |
| 4 | 595 serial stream toward downstream boards. |
| 5 | 165 input-return stream toward upstream boards. |
| 6 | Output latch. |
| 7 | Active-low arm/inhibit; DOWN is actual local hardware-gated inhibit. |
| 8 | Active-low shift clear. |
| 9 | Active-low parallel input load. |
| 11 | Raw NC-loop continuity: UP = ESTOP_FIELD, DOWN = ESTOP_CHAIN_OUT. It is not a 3.3 V GPIO. |
| 15 | Shared I²C SDA bus. |
| 16 | Shared I²C SCL bus. |

| Configuration | JP1 host role | JP2 common pullups | J10 termination |
|---|---|---|---|
| Single board | Closed | Closed if using its common pullup pair | Closed |
| Three-board module 0 / host | Closed | Closed if using host as common pullup provider | Open |
| Three-board module 1 / middle | Open | Open | Open |
| Three-board module 2 / tail | Open | Open | Closed |

Every J9 must provide intentional NC continuity; an unused open J9 breaks the
series stop loop. The complete NC contact/cable/connector path should be ≤10 Ω
**total**, not 10 Ω per contact. An intermediate J10 shorts the remainder of the
loop to ground and can bypass downstream stops. Configure roles and cabling
with power off and reset after a role change.

Set `BOARD_CHAIN_MODULES` to the exact number of connected modules, including
the host as module 0. The default is one; use `-D BOARD_CHAIN_MODULES=3` for
three. The software accepts 1–32 as a compiled allocation; there is no automatic
discovery and no qualified arbitrary cable/count limit. Inputs read host first;
output bytes are shifted farthest first. Channel numbers remain 1–8 on every
module. Each module contributes eight contacts, eight fault bits, and eight
outputs, not sixteen independent customer input channels.

## Input and stop meanings

The board **sources** nominal 20 mA into a grounded dry contact. FIELD is
normally near 4.4 V when open; that figure is a nominal model value, not a
precision output specification. Closed FIELD must remain ≤0.3 V including
contact and cable drop. A customer's ordinary 5 V push-pull output is not the
documented interface. An electronic sink would need to be designed for the
source current and LOW voltage; it is not an automatic substitute for a dry
contact.

Continuous ±100 V is a field-fault survival design target subject to physical
qualification, including hot/floating-power-off behavior. It is neither the
normal operating range nor a test the customer should perform during first use.
It does not cover power, GPIO, I²C, ordinary expansion logic, or GND pins. The
inputs share GND and provide no galvanic isolation. Small negative voltages near
ground may still appear closed because fault detection has a finite threshold.

The firmware does not debounce inputs or map an input to a valve. Inputs are
sampled approximately every 5 ms. For each module, bit 0 is input/output 1 and
bit 7 is input/output 8:

- `contacts_n`: LOW bit = raw conditioned closed contact.
- `input_faults`: HIGH bit = detected negative field fault.
- `closed`: `(~contacts_n) & (~input_faults)`; HIGH bit = usable closed contact.
- `outputs`: commanded pulse mask, not measured relay-contact position.

Hardware stop disables actual 595 outputs and removes relay-coil power. U34 is
a **74HC74 positive-edge flip-flop with asynchronous clear**, replacing the old
RC-pulse/SR-latch design. Stop or monitored-supply restoration alone cannot
rearm a held ARM signal.

GPIO18/`safe_permit` is protected **NC-loop and field-fault permission only**.
The raw 5 V/12 V monitors clear RUN separately, so `safe_permit=1` does not prove
that all supplies are valid. GPIO21/`hw_run` is only the local hardware latch;
it can remain HIGH after software disarm while output inhibit is HIGH. It does
not prove remote latch state, coil power, contact position, or valve closure.

A shared NC-loop stop reaches the host and propagates through the chain. A
local supply/hardware fault inhibits that board and downstream boards; it does
not inherently stop upstream valves. Check stops from every physical chain
position. A short across an NC contact can bypass it, and removing coil power
cannot open a welded relay contact. The board has no safety certification or
guaranteed physical shutdown time; an independent system valve-power
disconnect is required where those failures must stop flow.

## Firmware commands and observable responses

Commands are lowercase ASCII, newline-terminated. Carriage returns are ignored.
The line buffer accepts up to 47 printable characters; an overlong line or
nonprintable byte disarms. Use normal single spaces; arbitrary whitespace is
not normalized.

| Command | Implemented behavior |
|---|---|
| `status` | Common role/safety line, then one module line per configured board in host mode. No separate `ok`; does not renew lease. Expander reports only the common local line. |
| `arm` | Explicit host-only arm from disarmed state, after ≥50 ms continuous local permission health. Clears/latches all outputs, inhibits for 1 ms, makes a fresh arm edge, and waits up to 1 ms for local RUN. Successful arm starts no pulse. |
| `disarm` | Clears pulse commands and inhibits; accepted in either role. |
| `ping` | Renews an already-armed host session; rejects when disarmed or expander. |
| `pulse 1 100` | Module 0, channel 1, 100 ms. Requires acknowledged arm. |
| `pulse 2 1 100` | Module 2, channel 1, 100 ms; requires at least three configured modules. |
| `i2cscan` | Disarmed host only; address-only discovery diagnostics. |

Accepted non-status commands reply exactly `ok`. Rejection replies
`rejected; outputs disarmed` in host mode, or
`rejected; expander firmware has no bus control` in expander mode. A command
outside its current allowed state is not silently ignored: it disarms. This
includes a second `arm` while already armed, a pulse on a channel already
pulsing, or `i2cscan` while armed. Acknowledgements can be dropped if the serial
transmit queue is full; a status response is the practical diagnostic check.

Pulse duration is 1–1000 ms. There is no indefinite-ON command and an active
pulse cannot be extended. The control lease is **500 ms** from the last accepted
`arm`, `ping`, or `pulse`. Thus a requested 1000 ms pulse stops at the lease if
the controller sends no accepted renewal. For a deliberately longer session,
send `ping` about every 100 ms. `status` does not keep it armed. Inputs alone do
not start pulses.

After an EStop, restore the loop, allow supplies/startup to settle and local
permission to remain healthy for 50 ms, then send a new `arm` and new pulse.
Restoring a stop does not continue an old pulse. The supervisor has an
approximately 200 ms startup delay; allow at least that interval rather than
treating the firmware's 50 ms permission check as a power-up guarantee.

The exact common status fields are:

```text
role=host armed=0 safe_permit=1 hw_run=0 estop_latched=0 hw_fault_latched=0 modules=1 needs_reset=0 i2c_ready=1 i2c_scan=0 last_stop=boot
module=0 contacts_n=0xFF input_faults=0x00 closed=0x00 outputs=0x00
```

This is an illustrative format, not a promised boot snapshot: actual latch and
`last_stop` values depend on prior events. `needs_reset=1` means firmware booted
as expander but now observes a closed host jumper. Possible `last_stop` strings
are `boot`, `manual`, `estop`, `hardware_inhibit`, `expander_role`,
`lease_expired`, and `internal_fault`. `estop_latched` records a stop seen by
software; `hw_fault_latched` records a failed/lost RUN acknowledgement. They
clear on successful arm. Neither is a separate physical contact sensor.

## I²C and programming facts

Only the host calls `Wire.begin(GPIO8, GPIO9, 100000)` and sets a 5 ms
transaction timeout. An expander is not given an I²C slave address. The common
UP/DOWN bus connects PCA9517A port A; each MCU uses its private B side. Multiple
B ports must not be joined. JP2 selects 2.2 kΩ common pullups; each private side
has fixed 4.7 kΩ pullups. Peripheral power must be separately provided; the
expansion header supplies no power.

Use 3.3 V-compatible peripherals with unique 7-bit addresses. Start at 100 kHz
and qualify the total ≤400 pF common-bus budget; 32 buffer A ports can consume
224 pF before cabling. The software's 32-module shift limit is not an I²C address
or capacitance limit.

`i2cscan` probes 0x08–0x77 (112 addresses), sends address then STOP with no data,
at most one transaction per loop and ≥2 ms between probes. Peripherals must
allow address probes. Each acknowledgement reports `i2c_found=0xNN`; summary is
`i2c_scan=<state> probed=<count> found=<count> error=<code>`. States include
`complete`, `cancelled`, `deadline`, and `bus_error`. An unexpected bus error or
timeout aborts; deadline is 1.5 s. `arm` cancels a running scan. There is no
automatic scan or peripheral configuration after startup. Power/role changes
can require bus recovery/reset.

The UART build uses 115200 baud and J7, with a self-powered target and 3.3 V
logic adapter. Enter ROM download by holding J6.3 BOOT to J6.2 GND, pulsing
J6.1 EN to GND, then releasing BOOT. Use the adapter's actual serial port;
uploading must be done with valve power disconnected. The optional native USB
build uses GPIO19/D− and GPIO20/D+, but the header breakout lacks a complete
USB connector/protection interface. Do not suggest plugging a normal USB
cable directly into it or feeding VBUS into 3.3 V.

## Existing wording that needs correction

1. Root README mentions `J5/J8` debug ports; **J8 does not exist** in the final
   native netlist. Refer to J5 only.
2. Root README's `J3/J4 expose module pins 1–40` is electrically correct, but
   must distinguish module physical pad numbers from GPIO numbers. All 40
   header/pad native net comparisons pass; always use the connector table.
3. Corrected `HardwareArming.h:30` comment: 1 ms is conservative inhibit setup
   before the HC74 edge; the old 100 µs edge RC is absent. Timing is unchanged.
4. Corrected `ShiftRegisters.h:21` comment: serial chain tail is a HIGH pullup,
   not GND. The implementation and final firmware README already described
   HIGH/fault-FF behavior correctly.
5. Corrected `board_pins.h` comments: GPIO18 is field-loop permission; raw-rail
   faults independently clear the HC74 RUN latch. RUN can remain HIGH during
   software disarm. Customer text should not diagnose all supplies solely
   from GPIO18.

## Independent review of the customer guide

The first draft of `docs/hardware-user-guide.md` (UG-A3-1.0) was reviewed in full
against the native pins and actual firmware. No consequential wiring or command
mismatch was found. In particular:

- Both J1/J2 are required, and valve RETURN uses a separate external negative
  splice; J2 is not an eight-valve feed.
- Single-board and three-board role/pullup/termination instructions match the
  actual hardware. Pin 11 is an NC continuity path, not a digital GPIO.
- GPIO/header/module-pad examples and all schematic-navigation net names are
  correct; IN1_N, IN1_FAULT and RLY1_CMD exist in the native export.
- The pasted `arm` / `pulse 1 100` / `status` sequence is valid and avoids the
  earlier cancellation error of immediately adding `disarm`. All three lines
  fit within the firmware's 32-byte receive-work limit in one loop. Hardware
  RUN feedback and healthy permission are still required for the arm.
- `safe_permit`, local `hw_run`, commanded `outputs`, negative fault flags,
  lease renewal and input masking are described accurately.
- Possible project uses are clearly separated from features actually
  implemented in the commissioning scaffold.

The SVG generator was subsequently inspected independently. Valve topology is
correct: external fused COM feed, switched NO to valve positive, and RETURN
joining valve negative and external supply negative; the clamp spans NO/RETURN.
The reviewer identified a 30 px J9-to-J10 drawing gap and 5 px NC-path gaps at
the intermediate module left edges. The root author corrected those connections
in `scripts/render_hardware_user_guide.py`. Only the final board is terminated.
Draft PDF valve/contact pages were rendered and visually inspected; the J10
label and figure-bottom text margins were flagged for the author's final layout
pass. Complete final PDF pagination remains the root workflow responsibility.

The documented monitor flags `--port`, `--baud`, `--eol LF`, and `--echo` were
verified against the installed isolated PlatformIO 6.1.19 help and the
[official monitor reference](https://docs.platformio.org/en/latest/core/userguide/device/cmd_monitor.html).
No serial port was opened.

The reviewer also requested a load-selection clarification: relay NO does not
describe the valve's fluid state. Removing power does not close a normally-open
or latching valve. Customer text should require a deenergized state appropriate
to the intended system, such as a normally-closed nonlatching valve where flow
must stop. This is an application-selection clarification, not a change to the
board's electrical design.

## Final purchaser-guide disposition

The complete guide was checked against actual command/status behavior and native headers. The three vector examples were checked for valve RETURN/negative-supply continuity, NC J9/J10 continuity and expansion pin11 series connections; reported line gaps were corrected. Added valve deenergized-state selection, explicit50ms healthy-arm timing, and a pasted100ms test batch that does not immediately cancel with disarm. Source remains preview-labeled, with qualification rather than simulated-guarantee claims. Final PDF layout/links are recorded in analysis/customer-guide-verification.json.


## Intended-use correction — UG-A3-1.1, 2026-10-03

The project owner clarified that UPC is intended to create theatrical flame effects devices (poofers). The introduction and project examples now name stage effects, flame-art installations and custom theatrical poofers. This is an intended-use correction, not evidence of hardware qualification. Electrical specifications, commissioning commands and firmware behavior are unchanged; the guide still distinguishes the controller preview from a qualified complete effects system. The website and its downloadable guide use this corrected positioning.
