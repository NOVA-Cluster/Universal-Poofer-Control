#pragma once

#include <stdint.h>
#include <array>
#include "board_pins.h"

namespace poofer {

struct InputSnapshot {
  uint8_t contactsN;
  uint8_t faults;
  uint8_t closed;
};
using OutputMasks = std::array<uint8_t, board::kModuleCount>;
using InputWords = std::array<uint16_t, board::kModuleCount>;
using InputSnapshots = std::array<InputSnapshot, board::kModuleCount>;

// Io supplies write(pin, high), read(pin), and waitMicros(us).
// Each 74HC165 exposes D7 immediately after /PL: sample BEFORE rising CLK.
// Fault IC Q7 -> MISO; fault IC DS <- contact IC Q7; contact IC DS <- next
// module's fault Q7 (or the HIGH pullup at chain tail). Read host before downstream.
// Both devices share CLK. Input reads must never pulse the 595 output latch.
template <typename Io>
class ShiftRegisters {
 public:
  explicit ShiftRegisters(Io &io) : io_(io) {}

  void initialize() {
    setEnabled(false);
    io_.write(board::kRelayClearN, false);
    io_.write(board::kRelayLatch, false);
    io_.write(board::kSerialClock, false);
    io_.write(board::kRelayData, false);
    io_.write(board::kInputLoadN, true);
    io_.waitMicros(2);
    io_.write(board::kRelayClearN, true);
    writeOutputs(0);  // /SRCLR alone does not clear the storage/output register.
  }

  void setEnabled(bool enable) { io_.write(board::kRelayOeN, !enable); }

  void writeOutputs(uint8_t mask) {
    OutputMasks masks = {};
    masks[0] = mask;
    writeOutputs(masks);
  }

  void writeOutputs(const OutputMasks &masks) {
    io_.write(board::kRelayLatch, false);
    io_.write(board::kSerialClock, false);
    // Host SER feeds host 595, whose QH' feeds the next board. The farthest
    // module's byte must be shifted first; the host module's byte is last.
    for (int8_t module = board::kModuleCount - 1; module >= 0; --module) {
      for (int8_t bit = 7; bit >= 0; --bit) {
        io_.write(board::kRelayData, (masks[module] & (1U << bit)) != 0);
        clock();
      }
    }
    io_.write(board::kRelayLatch, true);
    io_.waitMicros(2);
    io_.write(board::kRelayLatch, false);
  }

  InputWords readRawInputs() {
    io_.write(board::kRelayLatch, false);
    io_.write(board::kSerialClock, false);
    io_.write(board::kInputLoadN, false);
    io_.waitMicros(2);
    io_.write(board::kInputLoadN, true);
    io_.waitMicros(2);
    InputWords raw = {};
    for (uint8_t module = 0; module < board::kModuleCount; ++module) {
      for (uint8_t bit = 0; bit < board::kInputShiftBits; ++bit) {
        raw[module] = static_cast<uint16_t>((raw[module] << 1U) | (io_.read(board::kInputData) ? 1U : 0U));
        clock();
      }
    }
    // High byte: UVFAULT, HIGH=fault. Low byte: CONTACTS_N, LOW=closed.
    // Each byte has bit 0 = D0 = physical input 1, bit 7 = input 8.
    return raw;
  }

  InputSnapshots readInputs() {
    const InputWords raw = readRawInputs();
    InputSnapshots result = {};
    for (uint8_t module = 0; module < board::kModuleCount; ++module) {
      const uint8_t contactsN = static_cast<uint8_t>(raw[module]);
      const uint8_t faults = static_cast<uint8_t>(raw[module] >> 8);
      const uint8_t active = board::kClosedContactLevel ? contactsN : static_cast<uint8_t>(~contactsN);
      result[module] = {contactsN, faults, static_cast<uint8_t>(active & static_cast<uint8_t>(~faults))};
    }
    return result;
  }

  uint8_t readClosedContacts() {
    return readInputs()[0].closed;
  }

 private:
  void clock() {
    io_.waitMicros(2);
    io_.write(board::kSerialClock, true);
    io_.waitMicros(2);
    io_.write(board::kSerialClock, false);
  }
  Io &io_;
};

}  // namespace poofer
