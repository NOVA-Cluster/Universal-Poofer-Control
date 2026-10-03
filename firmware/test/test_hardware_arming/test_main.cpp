#include <unity.h>
#include "HardwareArming.h"
#include "ShiftRegisters.h"

struct FakeArmAdapter {
  uint32_t timeUs = 50000;
  uint32_t releasedUs = 0;
  uint16_t feedbackDelayUs = 100;
  uint16_t eventDelayUs = UINT16_MAX;
  bool safe = true;
  bool inhibited = true;
  bool latchHigh = false;
  bool feedbackFailed = false;
  bool nonzeroAtArmEdge = false;
  uint8_t armEdges = 0;
  uint8_t clearCount = 0;
  poofer::OutputMasks storage = {};

  FakeArmAdapter() { storage.fill(0xFF); }
  void inhibit() { inhibited = true; }
  void clearOutputs() { storage.fill(0); ++clearCount; }
  bool safePermit() { return safe; }
  bool hardwareRun() {
    if (!feedbackFailed && releasedUs != 0 && timeUs - releasedUs >= feedbackDelayUs) latchHigh = true;
    return latchHigh && !feedbackFailed;
  }
  bool eventPending() {
    return releasedUs != 0 && timeUs - releasedUs >= eventDelayUs;
  }
  bool tryReleaseInhibit() {
    if (!safe || eventPending()) return false;
    for (auto mask : storage) nonzeroAtArmEdge |= mask != 0;
    if (inhibited) ++armEdges;
    inhibited = false;
    releasedUs = timeUs;
    return true;
  }
  void waitMicros(uint16_t us) { timeUs += us; }
  uint32_t nowMillis() { return timeUs / 1000; }
};

void setUp() {}
void tearDown() {}

void test_arm_requires_feedback_and_clears_all_storage_before_falling_edge() {
  poofer::SafetyController controller(true);
  controller.observeEstop(false, 0);
  FakeArmAdapter adapter;
  poofer::HardwareArming<FakeArmAdapter> arming(adapter);
  TEST_ASSERT_TRUE(arming.arm(controller, 50));
  TEST_ASSERT_TRUE(controller.armed());
  TEST_ASSERT_FALSE(adapter.inhibited);
  TEST_ASSERT_FALSE(adapter.nonzeroAtArmEdge);
  TEST_ASSERT_EQUAL_UINT8(1, adapter.armEdges);
  TEST_ASSERT_EQUAL_UINT32(51100, adapter.timeUs);
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask(module));
    TEST_ASSERT_EQUAL_UINT8(0, adapter.storage[module]);
  }
}

void test_missing_hw_run_feedback_refuses_arm_within_one_millisecond() {
  poofer::SafetyController controller(true);
  controller.observeEstop(false, 0);
  FakeArmAdapter adapter;
  adapter.feedbackFailed = true;
  poofer::HardwareArming<FakeArmAdapter> arming(adapter);
  TEST_ASSERT_FALSE(arming.arm(controller, 50));
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_TRUE(controller.hardwareFaultLatched());
  TEST_ASSERT_TRUE(adapter.inhibited);
  TEST_ASSERT_EQUAL_UINT32(52000, adapter.timeUs);  // 1 ms RC settle + 1 ms feedback deadline.
  TEST_ASSERT_EQUAL_UINT8(2, adapter.clearCount);
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::StopReason::HardwareInhibit),
                        static_cast<int>(controller.stopReason()));
}

void test_stop_event_during_arming_cannot_acknowledge_hardware_run() {
  poofer::SafetyController controller(true);
  controller.observeEstop(false, 0);
  FakeArmAdapter adapter;
  adapter.eventDelayUs = 50;
  poofer::HardwareArming<FakeArmAdapter> arming(adapter);
  TEST_ASSERT_FALSE(arming.arm(controller, 50));
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_TRUE(controller.hardwareFaultLatched());
  TEST_ASSERT_TRUE(adapter.inhibited);
  TEST_ASSERT_EQUAL_UINT32(51050, adapter.timeUs);
}

void test_falling_hardware_latch_clears_every_module_and_requires_fresh_arm() {
  poofer::SafetyController controller(true);
  controller.observeEstop(false, 0);
  FakeArmAdapter adapter;
  poofer::HardwareArming<FakeArmAdapter> arming(adapter);
  TEST_ASSERT_TRUE(arming.arm(controller, 50));
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_TRUE(controller.pulse(module, 7, 1000, 60));
  }
  controller.observeHardwareRun(false);
  adapter.inhibit();  // Native counterpart of the GPIO21 falling-edge ISR.
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_TRUE(controller.hardwareFaultLatched());
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask(module));
  }
  controller.observeHardwareRun(true);  // Restoring feedback must not auto-arm.
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_FALSE(controller.pulse(0, 100, 61));
  TEST_ASSERT_TRUE(arming.arm(controller, 61));
  TEST_ASSERT_EQUAL_UINT8(2, adapter.armEdges);
  TEST_ASSERT_FALSE(controller.hardwareFaultLatched());
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask(module));
  }
}

int main(int, char **) {
  UNITY_BEGIN();
  RUN_TEST(test_arm_requires_feedback_and_clears_all_storage_before_falling_edge);
  RUN_TEST(test_missing_hw_run_feedback_refuses_arm_within_one_millisecond);
  RUN_TEST(test_stop_event_during_arming_cannot_acknowledge_hardware_run);
  RUN_TEST(test_falling_hardware_latch_clears_every_module_and_requires_fresh_arm);
  return UNITY_END();
}
