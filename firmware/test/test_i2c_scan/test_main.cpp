#include <unity.h>
#include "I2cScanner.h"

void setUp() {}
void tearDown() {}

void test_scan_requires_disarmed_host_and_initialized_bus() {
  poofer::I2cScanner scan;
  TEST_ASSERT_FALSE(scan.start(0, false, false, true));
  TEST_ASSERT_FALSE(scan.start(0, true, true, true));
  TEST_ASSERT_FALSE(scan.start(0, true, false, false));
  TEST_ASSERT_TRUE(scan.start(0, true, false, true));
  TEST_ASSERT_FALSE(scan.start(10, true, false, true));  // No deadline-extending restart.
}

void test_scan_returns_one_normal_address_per_scheduled_step() {
  poofer::I2cScanner scan;
  uint8_t address = 0;
  TEST_ASSERT_TRUE(scan.start(0, true, false, true));
  TEST_ASSERT_TRUE(scan.nextAddress(0, true, false, true, address));
  TEST_ASSERT_EQUAL_HEX8(0x08, address);
  scan.recordResult(2);
  TEST_ASSERT_FALSE(scan.nextAddress(0, true, false, true, address));
  TEST_ASSERT_FALSE(scan.nextAddress(1, true, false, true, address));
  TEST_ASSERT_TRUE(scan.nextAddress(2, true, false, true, address));
  TEST_ASSERT_EQUAL_HEX8(0x09, address);
  TEST_ASSERT_EQUAL_UINT8(2, scan.probes());
}

void test_full_scan_excludes_reserved_addresses_and_completes() {
  poofer::I2cScanner scan;
  TEST_ASSERT_TRUE(scan.start(100, true, false, true));
  for (uint8_t expected = 0x08; expected <= 0x77; ++expected) {
    uint8_t address = 0;
    const uint32_t now = 100 + 2 * (expected - 0x08);
    TEST_ASSERT_TRUE(scan.nextAddress(now, true, false, true, address));
    TEST_ASSERT_EQUAL_HEX8(expected, address);
    scan.recordResult(address % 2 == 0 ? 0 : 2);
  }
  TEST_ASSERT_FALSE(scan.active());
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::ScanState::Complete), static_cast<int>(scan.state()));
  TEST_ASSERT_EQUAL_UINT8(112, scan.probes());
  TEST_ASSERT_EQUAL_UINT8(56, scan.found());
  TEST_ASSERT_EQUAL_UINT8(0, scan.error());
}

void test_arming_role_loss_and_bus_loss_cancel_scan_before_another_probe() {
  const bool roles[] = {true, false, true};
  const bool armed[] = {true, false, false};
  const bool ready[] = {true, true, false};
  for (uint8_t condition = 0; condition < 3; ++condition) {
    poofer::I2cScanner scan;
    uint8_t address = 0;
    scan.start(0, true, false, true);
    TEST_ASSERT_TRUE(scan.nextAddress(0, true, false, true, address));
    scan.recordResult(2);
    TEST_ASSERT_FALSE(scan.nextAddress(2, roles[condition], armed[condition], ready[condition], address));
    TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::ScanState::Cancelled), static_cast<int>(scan.state()));
    TEST_ASSERT_EQUAL_UINT8(1, scan.probes());
  }
}

void test_bus_timeout_aborts_and_overall_deadline_handles_millis_rollover() {
  poofer::I2cScanner scan;
  uint8_t address = 0;
  scan.start(0, true, false, true);
  TEST_ASSERT_TRUE(scan.nextAddress(0, true, false, true, address));
  scan.recordResult(5);
  TEST_ASSERT_FALSE(scan.nextAddress(2, true, false, true, address));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::ScanState::BusError), static_cast<int>(scan.state()));
  TEST_ASSERT_EQUAL_UINT8(5, scan.error());
  const uint32_t start = UINT32_MAX - 100;
  TEST_ASSERT_TRUE(scan.start(start, true, false, true));
  TEST_ASSERT_TRUE(scan.nextAddress(start, true, false, true, address));
  scan.recordResult(2);
  TEST_ASSERT_FALSE(scan.nextAddress(start + 1500, true, false, true, address));
  TEST_ASSERT_EQUAL_INT(static_cast<int>(poofer::ScanState::Deadline), static_cast<int>(scan.state()));
  TEST_ASSERT_EQUAL_UINT8(1, scan.probes());
}

int main(int, char **) {
  UNITY_BEGIN();
  RUN_TEST(test_scan_requires_disarmed_host_and_initialized_bus);
  RUN_TEST(test_scan_returns_one_normal_address_per_scheduled_step);
  RUN_TEST(test_full_scan_excludes_reserved_addresses_and_completes);
  RUN_TEST(test_arming_role_loss_and_bus_loss_cancel_scan_before_another_probe);
  RUN_TEST(test_bus_timeout_aborts_and_overall_deadline_handles_millis_rollover);
  return UNITY_END();
}
