#pragma once

#include <stdint.h>

#ifndef BOARD_CHAIN_MODULES
#define BOARD_CHAIN_MODULES 1
#endif

// Board contract: change these definitions only together with the schematic.
// ESP32-S3-WROOM-1-N8: 8 MB flash; no PSRAM. GPIOs use 3.3 V logic.
namespace board {
constexpr uint8_t kLocalMasterN = 2;
constexpr bool kHostRoleLevel = false;  // Closed host jumper LOW; absent jumper is expander.
constexpr uint8_t kSerialClock = 6;
constexpr uint8_t kRelayData = 4;
constexpr uint8_t kInputData = 5;
constexpr uint8_t kRelayLatch = 7;
constexpr uint8_t kRelayOeN = 15;
constexpr uint8_t kRelayClearN = 16;
constexpr uint8_t kInputLoadN = 17;
constexpr uint8_t kSafePermit = 18;
constexpr uint8_t kHardwareRun = 21;
constexpr uint8_t kI2cSda = 8;  // UP/DOWN expansion pin 15.
constexpr uint8_t kI2cScl = 9;  // UP/DOWN expansion pin 16.
constexpr uint32_t kI2cFrequencyHz = 100000;
constexpr uint16_t kI2cTimeoutMs = 5;
// Protected logic only: HIGH = NC EStop loop closed with valid field voltage.
// Raw 5 V/12 V faults independently clear RUN; this pin does not prove supply health.
// Never connect an external field wire to GPIO18.
constexpr bool kSafePermitHealthyLevel = true;
// Protected 3.3 V HC74 RUN feedback: HIGH=latched, LOW=hard inhibited.
// RUN may remain HIGH after software disarm while MCU_OE_N inhibits outputs.
constexpr bool kHardwareRunLevel = true;
// CONTACTS_N is active LOW: ground at FIELD closes the dry contact. The second
// cascaded 74HC165 reports HIGH for a per-input negative-voltage fault.
constexpr bool kClosedContactLevel = false;
constexpr uint8_t kUartTx = 43;
constexpr uint8_t kUartRx = 44;
constexpr uint8_t kUsbDm = 19;
constexpr uint8_t kUsbDp = 20;
constexpr uint8_t kValveCount = 8;
constexpr uint8_t kInputShiftBits = 16;
constexpr uint8_t kModuleCount = BOARD_CHAIN_MODULES;
static_assert(BOARD_CHAIN_MODULES >= 1 && BOARD_CHAIN_MODULES <= 32,
              "Configure 1..32 modules; physical chain length requires qualification");

// MCU_OE_N HIGH disables. Hardware combines ARM with HC74 RUN for actual 595 /OE
// and the relay-coil gate. EStop and supply faults independently clear HC74 RUN.

static_assert(kRelayOeN < 32, "ISR OE register write assumes GPIO0..31");
}  // namespace board
