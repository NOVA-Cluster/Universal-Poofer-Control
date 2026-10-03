# Universal Poofer Control firmware

Arduino/PlatformIO bring-up project for the custom ESP32-S3-WROOM-1-N8 board. The pinned official `platformio/espressif32@6.12.0` platform uses Arduino ESP32 2.0.17. The `esp32-s3-devkitc-1` board definition matches the module's 8 MB flash and absence of PSRAM. See the [PlatformIO board definition](https://docs.platformio.org/en/latest/boards/espressif32/esp32-s3-devkitc-1.html) and [pinned platform manifest](https://github.com/platformio/platform-espressif32/blob/v6.12.0/platform.json).

`include/board_pins.h` is the firmware pin/polarity contract. Each board has one 74HC595 output register and two cascaded 74HC165 input registers, all using 3.3 V logic. Both 165s share parallel-load GPIO17. The fault-register Q7 feeds MCU MISO/GPIO5 on the host; its DS pin receives contact-register Q7, and contact-register DS receives the next board's return stream or the HIGH pullup at the serial chain tail. Missing modules therefore return fault bits HIGH and are masked, rather than appearing to have grounded contacts. The separate NC continuity chain still uses its specified ground terminator. The driver samples Q7 before each rising edge and reads D7 first. Each board contributes 16 bits: first/high byte `UVFAULT` (HIGH=fault), then low byte `CONTACTS_N` (LOW=closed). Input 1 is bit 0 and input 8 is bit 7 in each byte. Input reads keep the 595 output latch LOW. Output writes send MSB first, so QA/bit 0 drives valve 1.

## Board role and expansion

GPIO2 reads `JP_LOCAL_MASTER_N`: LOW with the local-host jumper closed means **host**, while HIGH with the jumper absent means **expander**. Hardware buffers isolate local MCU bus drivers in expander mode and select the upstream controls. The same firmware can be loaded on each identical board. One board has the host jumper closed; every downstream board leaves it absent. Expander firmware keeps local GPIO15 HIGH, rejects `arm`/`pulse`/`ping`, and never initializes, clears, clocks, or scans the shift-register bus. Its `status` reports local role and protected stop/latch feedback, without claiming to know host-controlled valve or input states. Close an expander's host jumper only with the chain configured for that role, then reset the MCU to configure master GPIOs. Removing a host jumper disarms its firmware immediately on the next safety service and isolates its hardware drivers.

`BOARD_CHAIN_MODULES` configures the total board count **including host module 0**. It defaults to 1; add `-D BOARD_CHAIN_MODULES=3` to the selected environment's `build_flags` for three boards. The software accepts 1–32 boards with fixed arrays sized at compile time; this is an allocation limit, not a qualified physical chain length. Match the setting to the connected chain. There is no automatic module discovery.

The host clocks the shared `CLK`, `LATCH`, `LOAD_N`, `CLEAR_N`, and arm/inhibit controls. Each board forwards buffered controls downstream. Its own 595 QH′ feeds downstream `SER`, and the next board's return stream feeds its contact-165 DS; its fault-165 Q7 returns upstream. Thus inputs are read **host first**, then modules 1, 2, and onward, while output bytes are written **farthest module first**, with the host byte last. Every write latches a complete set of `8 × BOARD_CHAIN_MODULES` outputs together. Initialization, disarm, emergency-stop handling, and a lease expiry command all configured outputs off.

Use one active host and independent local 5 V/12 V supplies sized for each board. Connect the common reference and the required EStop return chain, with the specified ground terminator at the last board. Only the field inputs have the ±100 V design tolerance; expansion logic is 3.3 V. Qualify cable length, rise/fall times, per-board propagation, buffer fanout, connector current, common-ground voltage, power sequencing, and EStop-chain resistance for the chosen physical chain. The bit-banged driver uses at least 2 µs per clock phase, but propagation and GPIO execution time govern its actual rate. Increasing module count also increases main-loop pulse-expiry latency; measure timing with the intended chain before use.

## I²C diagnostics

UP/DOWN header pin 15 is SDA/GPIO8, and pin 16 is SCL/GPIO9. Only host firmware initializes `Wire.begin(8, 9, 100000)`, with a 5 ms transaction timeout. Expander firmware initializes neither an I²C master nor an I²C slave address. Role removal ends the local I²C master; reset after changing the role to initialize it again. `i2c_ready` and `i2c_scan` appear in the common status line. These APIs follow [Espressif's I²C documentation](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/i2c.html) and the [pinned Arduino 2.0.17 Wire interface](https://github.com/espressif/arduino-esp32/blob/2.0.17/libraries/Wire/src/Wire.h).

Send the explicit command `i2cscan` while **disarmed**. It probes one address per loop, with at least 2 ms between probes, over normal 7-bit addresses `0x08–0x77`. Each probe sends only the address followed by STOP; no register or data bytes are written. Connected peripherals must permit address probing. Results report `i2c_found=0xNN`, then a summary with addresses probed, devices acknowledging, and completion/error state. A timeout or unexpected bus error aborts the scan, and the whole scan has a 1.5 s scheduling deadline. An `arm` command cancels a running scan before arming; no I²C probes occur during an armed valve session. Scanning while armed is rejected and follows the existing disarm-on-rejected-command policy.

Enable the JP2 pullup pair where appropriate for the connected bus; coordinate it with pullups on peripherals and any isolated bus segments. I²C peripherals need unique addresses on their segment, suitable 3.3 V logic, and qualified pullup/rise-time/capacitance behavior. Its address and electrical limits are separate from the firmware's 32-board shift-chain allocation. This scaffold implements no peripheral configuration writes, actuator mapping, or automatic I²C activity after startup.

The eight field inputs are active-low dry contacts: close the switch from FIELD to the adjacent GND pin. The powered board supplies approximately 20 mA wetting current into each grounded switch; an open switch reads HIGH. `closed` in the status response is a mask of **closed switches without faults**, calculated as `(~contacts_n) & (~input_faults)`, with bit 0 for input 1. The negative-voltage detector sets the corresponding `input_faults` bit HIGH, so a voltage fault cannot be interpreted as a closed switch. `contacts_n` also reports the raw conditioned contact byte. Inputs are sampled every 5 ms without debounce, which is suitable for electrical commissioning. Add application-specific debounce before consuming switch transitions.

## Output behavior

- Boot, reset, upload, and serial connection do not arm the board. Initialization raises `MCU_OE_N`, holds `/SRCLR` LOW, clears the shift register, and latches `0x00` before accepting commands. `/SRCLR` alone does not clear the output storage register.
- `arm` must be explicit in host mode, and the hardware emergency-stop permissive must have been healthy for 50 ms. Arming raises GPIO15, clears/latches zero output bytes on all configured modules, holds the inhibit for a conservative 1 ms, then creates a fresh GPIO15 HIGH→LOW edge. The Schmitt inverter clocks a positive-edge 74HC74 with D tied HIGH; the former RC pulse/SR-latch circuit has been removed. Firmware polls GPIO21 `HW_RUN` for up to 1 ms and accepts the arm only if feedback is HIGH and no stop event intervened. Missing feedback raises the inhibit again, clears outputs, latches `hw_fault_latched`, and rejects the command. Arming never starts a valve pulse.
- Each valve command is a pulse of 1–1000 ms. A pulse already in progress cannot be extended. The application performs no automatic input-to-valve mapping and exposes no indefinitely-on command.
- An armed control session expires 500 ms after its last accepted `arm`, `ping`, or `pulse`. `status` and invalid commands do not renew it. Send `ping` at less than 500 ms intervals when a pulse longer than the lease is intentionally required.
- A falling `SAFE_PERMIT` immediately raises `MCU_OE_N` in an interrupt and latches a disarm, including a brief assertion that restores before the main loop reads it. Restoring the stop alone cannot resume outputs. After it has been healthy for 50 ms, send a fresh `arm` followed by a new `pulse`.
- A falling GPIO21 `HW_RUN` also raises the inhibit in an interrupt and disarms every configured module. Restored feedback does not resume commands. While armed, GPIO15 stays LOW even when no pulse is active; only an explicit new `arm` creates a rearm edge. Manual disarm, timeout, or a stop raises it HIGH.
- `disarm`, a lease expiry, an invalid/rejected command, or a serial line exceeding 47 characters turns all outputs off. The subscribed task watchdog invokes an OE inhibit hook and then its configured panic/reset if the main loop stalls for approximately 2 seconds.

Serial reception and transmission each process at most 32 bytes per main-loop iteration. Responses are queued, and writes use only reported buffer space; a stalled host can drop acknowledgements when the queue fills but cannot hold up a pulse deadline. `status` streams a common safety/role line followed by one line per module as buffer space becomes available. Each module line reports the latest scan; status requests do not renew the armed lease.

The board's hardware stop cuts relay-coil power independently of firmware. GPIO18 receives only protected `RAW_SAFE_PERMIT`: HIGH means the normally-closed EStop loop is closed and its voltage is valid; LOW means stop/open wiring or an unsafe field voltage, including ±100 V. GPIO21 receives protected 3.3 V hardware `RUN` feedback. GPIO15 is `MCU_OE_N`, HIGH=disable; a 74HC74 is asynchronously cleared on a stop, 3.3 V supervision fault, or independently monitored 5 V/12 V loss. Releasing clear while ARM remains held cannot create a new clock edge. Only a fresh arm edge after valid supplies can rearm it. The actual 595 `/OE` is gated by hardware `RUN` and the arm level. An independent power-good supervisor holds coil power off for approximately 200 ms after regulation starts and during brownout. Raw field voltage must never reach any MCU GPIO.

`hw_run=1` acknowledges the local hardware latch, which can remain latched HIGH after a manual software disarm while GPIO15 inhibits outputs. It does not prove remote latch state, coil power, or relay-contact position. Mechanical relay/valve release is delayed by coil/contact/valve dynamics and suppression. Software pulse timing is a main-loop deadline, not an independent precision or certified safety timer. Watchdog settings and behavior follow [Espressif IDF 4.4 task-watchdog documentation](https://docs.espressif.com/projects/esp-idf/en/v4.4.8/esp32s3/api-reference/system/wdts.html).

## Build and test

From this directory:

```sh
pio run -e poofer_uart -e poofer_usb
pio test -e native
pio run -e poofer_chain32_compile
```

If the host's PlatformIO installation has missing Python dependencies, an isolated build environment is available without modifying it:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/pio run -e poofer_uart -e poofer_usb
.venv/bin/pio test -e native
```

The native test environment configures three modules. Tests simulate all 65,536 input words and all 256 output bytes on each module, verify both cascade directions, and start with nonzero output storage at reset. Every one of the 256 contact bytes is tested against every fault byte on every module. Tests also cover the GPIO21 handshake/refusal, an interrupted arm, runtime hardware-latch loss, role inhibition/removal, all-module emergency-stop and lease expiry, bounded pulse timing/retrigger rejection, old and module-addressed commands, malformed commands, and `millis()` rollover. I²C scheduler tests verify disarmed-host eligibility, incremental/reserved-address bounds, completion, arm/role cancellation, bus-error termination, and the overall deadline across rollover. The 32-module environment verifies the largest supported compiled allocation on the ESP32-S3 toolchain. These checks do not upload or exercise physical hardware.

## Programming connection

The default `poofer_uart` environment uses J7 and a **3.3 V logic** UART adapter: adapter RX to board TX/GPIO43, adapter TX to board RX/GPIO44, and GND to GND. Power the target from its specified logic supply; the adapter's power pin stays disconnected. Hold BOOT/GPIO0 LOW, pulse EN/reset LOW, and release BOOT after entering the ROM download loader. Choose the adapter's serial port explicitly when uploading. UART `Serial` operates at 115200 baud.

The optional `poofer_usb` environment enables hardware USB CDC using GPIO19/D− and GPIO20/D+. The 100 mil module breakout is not a complete USB connector/interface. Use a suitable external USB connection with appropriate ESD protection and wiring; do not connect USB VBUS directly to the module or 3.3 V supply. The first download may require the same BOOT/reset sequence. Espressif describes [native USB CDC programming](https://docs.espressif.com/projects/arduino-esp32/en/latest/tutorials/cdc_dfu_flash.html).

## Commissioning commands

Terminate each command with a newline; commands use lowercase. Fit the host-role jumper before resetting the host and leave it absent on downstream boards. With valve loads disconnected and the external stop circuit exercised first, `status` confirms the role, protected feedback, and per-module input masks. Close the emergency-stop permissive, wait at least 50 ms after it becomes healthy and allow the power-good startup interval, then use:

```text
arm
pulse 1 100
status
disarm
```

`pulse 1 100` preserves the original command syntax and requests **host module 0**, valve 1, for 100 ms. `pulse 2 1 100` requests module 2, valve 1, for 100 ms when at least three boards are configured. Modules are numbered 0–`BOARD_CHAIN_MODULES−1`; valves remain 1–8. Commands must follow an acknowledged `arm` before the 500 ms lease expires. For automated bring-up, send `ping` every 100 ms during an intentionally armed session. Disconnecting the controller stops lease renewal; the host inhibits the configured chain. Repeat the external stop test while each module/relay is commanded on, verify that restoring the stop leaves the relay off, verify GPIO21 acknowledgement failure prevents arming, and verify physical NO/NC and walking-bit module mappings before connecting the intended loads.

Firmware is a commissioning scaffold. It has not been flashed to or electrically tested on a manufactured board. Production application behavior, debounce, communication authorization, diagnostics, and physical shutdown/release qualification remain future work.
