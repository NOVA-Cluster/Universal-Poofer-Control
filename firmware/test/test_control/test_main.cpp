#include <unity.h>
#include <stdint.h>
#include "SafetyController.h"
#include "Commands.h"

using poofer::SafetyController;
void setUp() {}
void tearDown() {}

void test_boot_requires_healthy_stop_and_explicit_arm() {
  SafetyController controller(true);
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
  TEST_ASSERT_FALSE(controller.arm(100));
  TEST_ASSERT_FALSE(controller.pulse(0, 100, 100));
  controller.observeEstop(false, 100);
  TEST_ASSERT_FALSE(controller.arm(149));
  TEST_ASSERT_TRUE(controller.arm(150));
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
  TEST_ASSERT_FALSE(controller.arm(151));
}

void test_individual_pulses_expire_and_cannot_be_extended() {
  SafetyController controller(true);
  controller.observeEstop(false, 0);
  TEST_ASSERT_TRUE(controller.arm(50));
  TEST_ASSERT_TRUE(controller.pulse(0, 100, 60));
  TEST_ASSERT_TRUE(controller.pulse(7, 200, 70));
  TEST_ASSERT_EQUAL_UINT8(0x81, controller.outputMask());
  TEST_ASSERT_FALSE(controller.pulse(0, 1000, 100));
  controller.tick(159);
  TEST_ASSERT_EQUAL_UINT8(0x81, controller.outputMask());
  controller.tick(160);
  TEST_ASSERT_EQUAL_UINT8(0x80, controller.outputMask());
  controller.tick(270);
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
}

void test_short_stop_opening_latches_all_channels_off() {
  SafetyController controller(true);
  controller.observeEstop(false, 0);
  TEST_ASSERT_TRUE(controller.arm(50));
  for (uint8_t channel = 0; channel < 8; ++channel) {
    TEST_ASSERT_TRUE(controller.pulse(channel, 1000, 60));
  }
  TEST_ASSERT_EQUAL_UINT8(0xFF, controller.outputMask());
  controller.observeEstop(true, 100);
  controller.observeEstop(false, 101);
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
  TEST_ASSERT_TRUE(controller.estopLatched());
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_FALSE(controller.heartbeat(110));
  TEST_ASSERT_FALSE(controller.pulse(0, 100, 110));
  TEST_ASSERT_FALSE(controller.arm(150));
  TEST_ASSERT_TRUE(controller.arm(151));
  TEST_ASSERT_FALSE(controller.estopLatched());
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
}

void test_control_lease_cannot_be_revived_by_late_ping() {
  SafetyController controller(true);
  controller.observeEstop(false, 0);
  controller.arm(50);
  TEST_ASSERT_TRUE(controller.pulse(3, 1000, 50));
  TEST_ASSERT_TRUE(controller.heartbeat(400));
  controller.tick(899);
  TEST_ASSERT_EQUAL_UINT8(8, controller.outputMask());
  controller.tick(900);
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
  TEST_ASSERT_FALSE(controller.heartbeat(901));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::StopReason::LeaseExpired),
                        static_cast<int>(controller.stopReason()));
  TEST_ASSERT_TRUE(controller.arm(902));
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
}

void test_pulse_bounds_and_manual_disarm() {
  SafetyController controller(true);
  controller.observeEstop(false, 0);
  controller.arm(50);
  TEST_ASSERT_FALSE(controller.pulse(8, 100, 50));
  TEST_ASSERT_FALSE(controller.pulse(0, 0, 50));
  TEST_ASSERT_FALSE(controller.pulse(0, 1001, 50));
  TEST_ASSERT_TRUE(controller.pulse(0, 1000, 50));
  controller.disarm();
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_TRUE(controller.arm(60));
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
}

void test_millis_rollover_preserves_pulse_and_lease_bounds() {
  SafetyController controller(true);
  controller.observeEstop(false, UINT32_MAX - 100);
  TEST_ASSERT_TRUE(controller.arm(UINT32_MAX - 50));
  TEST_ASSERT_TRUE(controller.pulse(2, 200, UINT32_MAX - 50));
  controller.tick(148);  // 199 ms after start
  TEST_ASSERT_EQUAL_UINT8(4, controller.outputMask());
  controller.tick(149);  // 200 ms after start
  TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask());
  controller.tick(449);  // 500 ms after lease
  TEST_ASSERT_FALSE(controller.armed());
}

void test_command_parser_rejects_unbounded_and_ambiguous_commands() {
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::CommandKind::Arm),
                       static_cast<int>(poofer::parseCommand("arm").kind));
  const auto pulse = poofer::parseCommand("pulse 8 1000");
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::CommandKind::Pulse), static_cast<int>(pulse.kind));
  TEST_ASSERT_EQUAL_UINT8(7, pulse.channel);
  TEST_ASSERT_EQUAL_UINT8(0, pulse.module);  // Backward-compatible host command.
  TEST_ASSERT_EQUAL_UINT32(1000, pulse.duration);
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::CommandKind::I2cScan),
                       static_cast<int>(poofer::parseCommand("i2cscan").kind));
  const char *invalid[] = {"pulse 0 1", "pulse 9 1", "pulse 1 0", "pulse 1 1001",
                          "pulse 1 -1", "pulse 1 4294967297", "pulse 1 10 extra",
                          "pulse 1 1.0", "pulse  1 10", "arm extra", "arm ", "on 1", "i2cscan 0x20", "i2cscan ", ""};
  for (const auto text : invalid) {
    TEST_ASSERT_EQUAL_INT_MESSAGE(static_cast<int>(poofer::CommandKind::Invalid),
                                 static_cast<int>(poofer::parseCommand(text).kind), text);
  }
}

void test_all_module_pulses_stop_on_estop_and_shared_lease_expiry() {
  SafetyController controller(true);
  controller.observeEstop(false, 0);
  TEST_ASSERT_TRUE(controller.arm(50));
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_TRUE(controller.pulse(module, module, 1000, 60));
    TEST_ASSERT_EQUAL_UINT8(1U << module, controller.outputMask(module));
  }
  TEST_ASSERT_FALSE(controller.pulse(board::kModuleCount, 0, 100, 60));
  controller.observeEstop(true, 70);
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask(module));
  }
  controller.observeEstop(false, 80);
  TEST_ASSERT_TRUE(controller.arm(130));
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_TRUE(controller.pulse(module, 7, 1000, 140));
  }
  controller.tick(640);
  TEST_ASSERT_FALSE(controller.armed());
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask(module));
  }
}

void test_explicit_module_commands_select_downstream_and_reject_out_of_range() {
  const auto host = poofer::parseCommand("pulse 0 8 100");
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::CommandKind::Pulse), static_cast<int>(host.kind));
  TEST_ASSERT_EQUAL_UINT8(0, host.module);
  TEST_ASSERT_EQUAL_UINT8(7, host.channel);
  const auto downstream = poofer::parseCommand("pulse 2 1 250");
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::CommandKind::Pulse), static_cast<int>(downstream.kind));
  TEST_ASSERT_EQUAL_UINT8(2, downstream.module);
  TEST_ASSERT_EQUAL_UINT8(0, downstream.channel);
  TEST_ASSERT_EQUAL_UINT32(250, downstream.duration);
  const char *invalid[] = {"pulse 3 1 100", "pulse -1 1 100", "pulse 2 0 100",
                          "pulse 2 9 100", "pulse 2 1 0", "pulse 2 1 1001", "pulse 2 1 100 extra"};
  for (const auto text : invalid) {
    TEST_ASSERT_EQUAL_INT_MESSAGE(static_cast<int>(poofer::CommandKind::Invalid),
                                 static_cast<int>(poofer::parseCommand(text).kind), text);
  }
}

void test_expander_role_default_refuses_arm_and_role_removal_stops_all_modules() {
  SafetyController controller;  // Default role is inhibited until jumper is checked.
  controller.observeEstop(false, 0);
  TEST_ASSERT_FALSE(controller.hostRole());
  TEST_ASSERT_FALSE(controller.arm(50));
  TEST_ASSERT_FALSE(controller.pulse(0, 100, 50));
  controller.setHostRole(true);
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_TRUE(controller.arm(60));
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_TRUE(controller.pulse(module, 0, 1000, 70));
  }
  controller.setHostRole(false);
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_FALSE(controller.hostRole());
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    TEST_ASSERT_EQUAL_UINT8(0, controller.outputMask(module));
  }
  controller.setHostRole(true);  // Reinstalling jumper cannot revive old pulses.
  TEST_ASSERT_FALSE(controller.armed());
  TEST_ASSERT_FALSE(controller.heartbeat(80));
}

int main(int, char **) {
  UNITY_BEGIN();
  RUN_TEST(test_boot_requires_healthy_stop_and_explicit_arm);
  RUN_TEST(test_individual_pulses_expire_and_cannot_be_extended);
  RUN_TEST(test_short_stop_opening_latches_all_channels_off);
  RUN_TEST(test_control_lease_cannot_be_revived_by_late_ping);
  RUN_TEST(test_pulse_bounds_and_manual_disarm);
  RUN_TEST(test_millis_rollover_preserves_pulse_and_lease_bounds);
  RUN_TEST(test_command_parser_rejects_unbounded_and_ambiguous_commands);
  RUN_TEST(test_all_module_pulses_stop_on_estop_and_shared_lease_expiry);
  RUN_TEST(test_explicit_module_commands_select_downstream_and_reject_out_of_range);
  RUN_TEST(test_expander_role_default_refuses_arm_and_role_removal_stops_all_modules);
  return UNITY_END();
}
