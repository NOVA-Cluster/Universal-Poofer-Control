#include <unity.h>
#include "ShiftRegisters.h"

// Behavioral model of a three-module chain. Each module has two 165s and one
// 595. The host's high input byte is its fault IC; its low byte is contacts.
// Output serial data enters the host 595 and cascades toward downstream boards.
struct FakeIo {
  bool pins[49] = {};
  poofer::InputWords inputPins = {};
  poofer::InputWords inputShift = {};
  poofer::OutputMasks relayShift = {};
  poofer::OutputMasks relayStorage = {};
  uint32_t latchEdges = 0;
  bool everEnabledDuringInitialize = false;

  FakeIo() {
    relayShift.fill(0xFF);
    relayStorage.fill(0xFF);  // Storage is not cleared by /SRCLR.
  }
  void write(uint8_t pin, bool high) {
    const bool old = pins[pin];
    pins[pin] = high;
    if (pin == board::kRelayOeN && !high) everEnabledDuringInitialize = true;
    if (pin == board::kRelayClearN && !high) relayShift.fill(0);
    if (pin == board::kInputLoadN && !high) inputShift = inputPins;
    if (pin == board::kSerialClock && high && !old) {
      for (uint8_t module = 0; module < board::kModuleCount; ++module) {
        const uint16_t serial = module + 1 < board::kModuleCount ?
                               (inputShift[module + 1] >> 15) : 0;
        inputShift[module] = static_cast<uint16_t>((inputShift[module] << 1) | serial);
      }
      if (pins[board::kRelayClearN]) {
        for (int8_t module = board::kModuleCount - 1; module >= 0; --module) {
          const uint8_t serial = module == 0 ? pins[board::kRelayData] :
                                 static_cast<uint8_t>(relayShift[module - 1] >> 7);
          relayShift[module] = static_cast<uint8_t>((relayShift[module] << 1) | serial);
        }
      }
    }
    if (pin == board::kRelayLatch && high && !old) {
      relayStorage = relayShift;
      ++latchEdges;
    }
  }
  bool read(uint8_t pin) {
    return pin == board::kInputData ? (inputShift[0] & 0x8000) != 0 : pins[pin];
  }
  void waitMicros(uint8_t) {}
};

void setUp() {}
void tearDown() {}

void test_initialize_inhibits_and_clears_all_module_storage() {
  FakeIo io;
  poofer::ShiftRegisters<FakeIo> shifts(io);
  shifts.initialize();
  TEST_ASSERT_TRUE(io.pins[board::kRelayOeN]);
  TEST_ASSERT_FALSE(io.everEnabledDuringInitialize);
  for (auto storage : io.relayStorage) TEST_ASSERT_EQUAL_UINT8(0, storage);
  TEST_ASSERT_EQUAL_UINT32(1, io.latchEdges);
}

void test_all_65536_input_words_preserve_cascade_order_and_physical_mapping() {
  FakeIo io;
  poofer::ShiftRegisters<FakeIo> shifts(io);
  shifts.initialize();
  poofer::OutputMasks outputs = {};
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    outputs[module] = static_cast<uint8_t>(0x96 ^ (module * 0xA5));
  }
  shifts.writeOutputs(outputs);
  const uint32_t latchesBeforeInput = io.latchEdges;
  for (uint32_t pattern = 0; pattern < 65536; ++pattern) {
    for (uint8_t module = 0; module < board::kModuleCount; ++module) {
      io.inputPins[module] = static_cast<uint16_t>(pattern ^ (module * 0xA55A));
    }
    const auto read = shifts.readRawInputs();
    for (uint8_t module = 0; module < board::kModuleCount; ++module) {
      TEST_ASSERT_EQUAL_UINT16(io.inputPins[module], read[module]);
      TEST_ASSERT_EQUAL_UINT8(outputs[module], io.relayStorage[module]);
    }
    TEST_ASSERT_EQUAL_UINT32(latchesBeforeInput, io.latchEdges);
  }
}

void test_all_output_words_map_qa_to_valve_one_and_downstream_first() {
  FakeIo io;
  poofer::ShiftRegisters<FakeIo> shifts(io);
  shifts.initialize();
  for (uint16_t pattern = 0; pattern < 256; ++pattern) {
    poofer::OutputMasks outputs = {};
    for (uint8_t module = 0; module < board::kModuleCount; ++module) {
      outputs[module] = static_cast<uint8_t>(pattern ^ (module * 0x59));
    }
    shifts.writeOutputs(outputs);
    for (uint8_t module = 0; module < board::kModuleCount; ++module) {
      TEST_ASSERT_EQUAL_UINT8(outputs[module], io.relayStorage[module]);
    }
  }
}

void test_closed_contact_polarity_matches_board_contract() {
  FakeIo io;
  poofer::ShiftRegisters<FakeIo> shifts(io);
  shifts.initialize();
  io.inputPins.fill(0x00FE);  // Contact 1 closed, no faults.
  for (auto input : shifts.readInputs()) TEST_ASSERT_EQUAL_UINT8(0x01, input.closed);
  io.inputPins.fill(0x007F);  // Contact 8 closed, no faults.
  for (auto input : shifts.readInputs()) TEST_ASSERT_EQUAL_UINT8(0x80, input.closed);
}

void test_all_contact_fault_cross_products_mask_faulted_inputs_on_every_module() {
  FakeIo io;
  poofer::ShiftRegisters<FakeIo> shifts(io);
  shifts.initialize();
  for (uint32_t pattern = 0; pattern < 65536; ++pattern) {
    for (uint8_t module = 0; module < board::kModuleCount; ++module) {
      io.inputPins[module] = static_cast<uint16_t>(pattern ^ (module * 0x6A93));
    }
    const auto inputs = shifts.readInputs();
    for (uint8_t module = 0; module < board::kModuleCount; ++module) {
      const auto contactsN = static_cast<uint8_t>(io.inputPins[module]);
      const auto faults = static_cast<uint8_t>(io.inputPins[module] >> 8);
      TEST_ASSERT_EQUAL_UINT8(contactsN, inputs[module].contactsN);
      TEST_ASSERT_EQUAL_UINT8(faults, inputs[module].faults);
      TEST_ASSERT_EQUAL_UINT8(static_cast<uint8_t>(~contactsN & ~faults), inputs[module].closed);
    }
  }
}

int main(int, char **) {
  UNITY_BEGIN();
  RUN_TEST(test_initialize_inhibits_and_clears_all_module_storage);
  RUN_TEST(test_all_65536_input_words_preserve_cascade_order_and_physical_mapping);
  RUN_TEST(test_all_output_words_map_qa_to_valve_one_and_downstream_first);
  RUN_TEST(test_closed_contact_polarity_matches_board_contract);
  RUN_TEST(test_all_contact_fault_cross_products_mask_faulted_inputs_on_every_module);
  return UNITY_END();
}
