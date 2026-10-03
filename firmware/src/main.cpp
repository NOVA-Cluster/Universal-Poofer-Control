#include <Arduino.h>
#include <Wire.h>
#include <esp_task_wdt.h>
#include <soc/gpio_reg.h>
#include <soc/soc.h>

#include "board_pins.h"
#include "Commands.h"
#include "HardwareArming.h"
#include "I2cScanner.h"
#include "SafetyController.h"
#include "ShiftRegisters.h"

namespace {
class ArduinoIo {
 public:
  void write(uint8_t pin, bool high) { digitalWrite(pin, high ? HIGH : LOW); }
  bool read(uint8_t pin) { return digitalRead(pin) == HIGH; }
  void waitMicros(uint8_t micros) { delayMicroseconds(micros); }
};

ArduinoIo gpio;
poofer::ShiftRegisters<ArduinoIo> shifts(gpio);
poofer::SafetyController controller;
portMUX_TYPE estopMux = portMUX_INITIALIZER_UNLOCKED;
volatile bool estopInterruptSeen = false;
volatile bool runLatchDropSeen = false;
bool watchdogReady = false;
bool outputsEnabled = false;
bool bootHostRole = false;
bool i2cReady = false;
bool i2cScanAnnounced = true;
poofer::I2cScanner i2cScanner;
poofer::OutputMasks storedOutputs = {};
poofer::InputSnapshots inputState = {};
uint32_t lastInputSample = 0;
char line[48] = {};
uint8_t lineLength = 0;
bool discardLine = false;
char transmit[512] = {};
uint16_t transmitHead = 0;
uint16_t transmitTail = 0;
bool queueResponse(const char *text);
bool statusPending = false;
bool statusHeaderPending = false;
uint8_t statusNextModule = 0;

void IRAM_ATTR inhibitFromInterrupt() {
  // Fixed GPIO15 is verified by board_pins.h. A register write avoids calls into
  // flash and raises MCU_OE_N immediately; hardware also cuts coil power.
  REG_WRITE(GPIO_OUT_W1TS_REG, 1UL << board::kRelayOeN);
}

void IRAM_ATTR onEstopFault() {
  inhibitFromInterrupt();
  portENTER_CRITICAL_ISR(&estopMux);
  estopInterruptSeen = true;
  portEXIT_CRITICAL_ISR(&estopMux);
}

void IRAM_ATTR onHardwareRunDrop() {
  inhibitFromInterrupt();
  portENTER_CRITICAL_ISR(&estopMux);
  runLatchDropSeen = true;
  portEXIT_CRITICAL_ISR(&estopMux);
}

bool faultPresent() {
  return (digitalRead(board::kSafePermit) == HIGH) != board::kSafePermitHealthyLevel;
}

bool hardwareRun() {
  return (digitalRead(board::kHardwareRun) == HIGH) == board::kHardwareRunLevel;
}

bool localMasterRole() {
  return (digitalRead(board::kLocalMasterN) == HIGH) == board::kHostRoleLevel;
}

bool hostRoleActive() { return bootHostRole && localMasterRole(); }

class ArmAdapter {
 public:
  void inhibit() {
    shifts.setEnabled(false);
    outputsEnabled = false;
  }
  void clearOutputs() {
    if (hostRoleActive()) shifts.writeOutputs(0);
    storedOutputs.fill(0);
  }
  bool safePermit() { return hostRoleActive() && !faultPresent(); }
  bool hardwareRun() { return ::hardwareRun(); }
  bool eventPending() {
    portENTER_CRITICAL(&estopMux);
    const bool pending = estopInterruptSeen || runLatchDropSeen;
    portEXIT_CRITICAL(&estopMux);
    return pending;
  }
  bool tryReleaseInhibit() {
    portENTER_CRITICAL(&estopMux);
    const bool allow = hostRoleActive() && !estopInterruptSeen && !runLatchDropSeen && !faultPresent();
    if (allow) {
      shifts.setEnabled(true);
      outputsEnabled = true;
    }
    portEXIT_CRITICAL(&estopMux);
    return allow;
  }
  void waitMicros(uint16_t us) { delayMicroseconds(us); }
  uint32_t nowMillis() { return millis(); }
};
ArmAdapter armAdapter;
poofer::HardwareArming<ArmAdapter> hardwareArming(armAdapter);

void observeSafety(uint32_t now) {
  controller.setHostRole(hostRoleActive());
  portENTER_CRITICAL(&estopMux);
  const bool event = estopInterruptSeen;
  const bool runDrop = runLatchDropSeen;
  estopInterruptSeen = false;
  runLatchDropSeen = false;
  portEXIT_CRITICAL(&estopMux);
  if (event) controller.observeEstop(true, now);  // Latch even a brief opening.
  controller.observeEstop(faultPresent(), now);
  if (runDrop) controller.observeHardwareRun(false);
  controller.observeHardwareRun(hardwareRun());
  controller.tick(now);
}

void applyOutputs() {
  if (!hostRoleActive()) {
    controller.setHostRole(false);
    shifts.setEnabled(false);
    outputsEnabled = false;
    storedOutputs.fill(0);
    return;  // Expander firmware must not clock, clear, or latch the host's bus.
  }
  if (controller.armed() && !hardwareRun()) controller.observeHardwareRun(false);
  if (controller.armed() && !outputsEnabled) controller.hardwareArmFailed();
  if (!controller.armed() || faultPresent()) {
    shifts.setEnabled(false);
    outputsEnabled = false;
  }
  poofer::OutputMasks desired = {};
  for (uint8_t module = 0; module < board::kModuleCount; ++module) {
    desired[module] = controller.outputMask(module);
  }
  if (desired != storedOutputs) {
    shifts.writeOutputs(desired);
    storedOutputs = desired;
  }
  // Never lower MCU_OE_N here. Only a new explicit arm handshake creates that
  // edge. Empty pulse masks keep the inhibit LOW while the armed lease is alive.
}

const char *reasonName(poofer::StopReason reason) {
  switch (reason) {
    case poofer::StopReason::Boot: return "boot";
    case poofer::StopReason::Manual: return "manual";
    case poofer::StopReason::Estop: return "estop";
    case poofer::StopReason::HardwareInhibit: return "hardware_inhibit";
    case poofer::StopReason::ExpanderRole: return "expander_role";
    case poofer::StopReason::LeaseExpired: return "lease_expired";
    case poofer::StopReason::InternalFault: return "internal_fault";
  }
  return "unknown";
}

void reportStatus() {
  statusPending = true;
  statusHeaderPending = true;
  statusNextModule = 0;
}

void serviceStatus() {
  if (!statusPending) return;
  char response[256];
  if (statusHeaderPending) {
    snprintf(response, sizeof(response),
             "role=%s armed=%u safe_permit=%u hw_run=%u estop_latched=%u hw_fault_latched=%u modules=%u needs_reset=%u i2c_ready=%u i2c_scan=%u last_stop=%s\n",
             controller.hostRole() ? "host" : "expander", controller.armed(), !controller.faultPresent(), hardwareRun(), controller.estopLatched(),
             controller.hardwareFaultLatched(), board::kModuleCount, !bootHostRole && localMasterRole(),
             i2cReady, i2cScanner.active(), reasonName(controller.stopReason()));
    if (!queueResponse(response)) return;
    statusHeaderPending = false;
  }
  if (!controller.hostRole()) {
    statusPending = false;
    return;  // Local firmware cannot report host-controlled relay/input states.
  }
  const auto &inputs = inputState[statusNextModule];
  snprintf(response, sizeof(response),
           "module=%u contacts_n=0x%02X input_faults=0x%02X closed=0x%02X outputs=0x%02X\n",
           statusNextModule, inputs.contactsN, inputs.faults, inputs.closed,
           controller.outputMask(statusNextModule));
  if (queueResponse(response)) {
    if (++statusNextModule >= board::kModuleCount) statusPending = false;
  }
}

bool queueResponse(const char *text) {
  const size_t length = strlen(text);
  const uint16_t available = static_cast<uint16_t>((transmitTail + sizeof(transmit) -
                                                   transmitHead - 1) % sizeof(transmit));
  if (length > available) return false;  // Do not delay safety for a stalled host.
  while (*text != '\0') {
    transmit[transmitHead] = *text++;
    transmitHead = static_cast<uint16_t>((transmitHead + 1) % sizeof(transmit));
  }
  return true;
}

void serviceTransmit() {
  // Never block pulse deadlines on a disconnected or slow host. Only write the
  // reported available FIFO/buffer space, with at most 32 bytes in each loop.
  const int available = Serial.availableForWrite();
  const uint16_t pending = static_cast<uint16_t>((transmitHead + sizeof(transmit) -
                                                transmitTail) % sizeof(transmit));
  if (available <= 0 || pending == 0) return;
  uint16_t count = pending > 32 ? 32 : pending;
  if (count > available) count = static_cast<uint16_t>(available);
  const uint16_t contiguous = static_cast<uint16_t>(sizeof(transmit) - transmitTail);
  if (count > contiguous) count = contiguous;
  const size_t written = Serial.write(reinterpret_cast<const uint8_t *>(&transmit[transmitTail]), count);
  transmitTail = static_cast<uint16_t>((transmitTail + written) % sizeof(transmit));
}

const char *scanStateName(poofer::ScanState state) {
  switch (state) {
    case poofer::ScanState::Idle: return "idle";
    case poofer::ScanState::Active: return "active";
    case poofer::ScanState::Complete: return "complete";
    case poofer::ScanState::Cancelled: return "cancelled";
    case poofer::ScanState::Deadline: return "deadline";
    case poofer::ScanState::BusError: return "bus_error";
  }
  return "unknown";
}

void serviceI2cScan() {
  if (!hostRoleActive() && i2cReady) {
    i2cScanner.cancel();
    Wire.end();
    i2cReady = false;  // Reset after a role change to initialize I2C again.
  }
  uint8_t address = 0;
  if (i2cScanner.nextAddress(millis(), controller.hostRole(), controller.armed(), i2cReady, address)) {
    // Address-only probe with STOP, no register/data writes. One transaction per
    // loop, 5 ms driver timeout, and never while any valve session is armed.
    Wire.beginTransmission(address);
    const uint8_t result = Wire.endTransmission(true);
    i2cScanner.recordResult(result);
    if (result == 0) {
      char response[32];
      snprintf(response, sizeof(response), "i2c_found=0x%02X\n", address);
      queueResponse(response);
    }
  }
  if (!i2cScanner.active() && !i2cScanAnnounced) {
    char response[96];
    snprintf(response, sizeof(response), "i2c_scan=%s probed=%u found=%u error=%u\n",
             scanStateName(i2cScanner.state()), i2cScanner.probes(), i2cScanner.found(), i2cScanner.error());
    if (queueResponse(response)) i2cScanAnnounced = true;
  }
}

void handleCommand(const char *text) {
  const uint32_t now = millis();
  observeSafety(now);
  const poofer::Command command = poofer::parseCommand(text);
  bool accepted = false;
  switch (command.kind) {
    case poofer::CommandKind::Arm:
      i2cScanner.cancel();
      if (watchdogReady) accepted = hardwareArming.arm(controller, now);
      else controller.disarm(poofer::StopReason::InternalFault);
      break;
    case poofer::CommandKind::Disarm:
      controller.disarm();
      accepted = true;
      break;
    case poofer::CommandKind::Ping:
      accepted = controller.heartbeat(now);
      break;
    case poofer::CommandKind::Status:
      applyOutputs();
      reportStatus();
      return;
    case poofer::CommandKind::Pulse:
      accepted = controller.pulse(command.module, command.channel, command.duration, now);
      break;
    case poofer::CommandKind::I2cScan:
      accepted = i2cScanner.start(now, controller.hostRole(), controller.armed(), i2cReady);
      if (accepted) i2cScanAnnounced = false;
      break;
    case poofer::CommandKind::Invalid:
      break;
  }
  if (!accepted && command.kind != poofer::CommandKind::Arm) controller.disarm();
  applyOutputs();  // Never perform potentially blocking serial I/O before off.
  queueResponse(accepted ? "ok\n" : (controller.hostRole() ?
                "rejected; outputs disarmed\n" : "rejected; expander firmware has no bus control\n"));
}

void serviceSerial() {
  // Bound work per loop. Flooding serial cannot postpone safety deadlines.
  for (uint8_t received = 0; received < 32 && Serial.available(); ++received) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') continue;
    if (c == '\n') {
      if (!discardLine && lineLength != 0) {
        line[lineLength] = '\0';
        handleCommand(line);
      }
      lineLength = 0;
      discardLine = false;
    } else if (c < 32 || c > 126 || lineLength >= sizeof(line) - 1) {
      controller.disarm();
      applyOutputs();
      discardLine = true;
    } else if (!discardLine) {
      line[lineLength++] = c;
    }
  }
}

void safeOutputPin(uint8_t pin, bool initialHigh) {
  digitalWrite(pin, initialHigh ? HIGH : LOW);
  pinMode(pin, OUTPUT);
}
}  // namespace

// Espressif's task-watchdog hook runs before its configured panic/reset path.
// Hardware EStop remains independent, and reset restores the external defaults.
extern "C" void IRAM_ATTR esp_task_wdt_isr_user_handler(void) {
  inhibitFromInterrupt();
}

void setup() {
  safeOutputPin(board::kRelayOeN, true);  // Inhibit before any other peripheral.
  pinMode(board::kLocalMasterN, INPUT_PULLUP);
  bootHostRole = localMasterRole();
  controller.setHostRole(bootHostRole);
  if (bootHostRole) {
    safeOutputPin(board::kRelayClearN, false);
    safeOutputPin(board::kRelayLatch, false);
    safeOutputPin(board::kSerialClock, false);
    safeOutputPin(board::kRelayData, false);
    safeOutputPin(board::kInputLoadN, true);
  }
  pinMode(board::kInputData, INPUT);
  pinMode(board::kSafePermit, INPUT_PULLDOWN);  // An absent protected sense signal inhibits.
  pinMode(board::kHardwareRun, INPUT_PULLDOWN);
  if (bootHostRole) shifts.initialize();
  for (auto &inputs : inputState) inputs = {0xFF, 0, 0};
  attachInterrupt(digitalPinToInterrupt(board::kSafePermit), onEstopFault,
                  board::kSafePermitHealthyLevel ? FALLING : RISING);
  attachInterrupt(digitalPinToInterrupt(board::kHardwareRun), onHardwareRunDrop,
                  board::kHardwareRunLevel ? FALLING : RISING);
  controller.observeEstop(faultPresent(), millis());

  watchdogReady = esp_task_wdt_init(2, true) == ESP_OK && esp_task_wdt_add(nullptr) == ESP_OK;
  if (!watchdogReady) controller.disarm(poofer::StopReason::InternalFault);
  if (bootHostRole) {
    i2cReady = Wire.begin(board::kI2cSda, board::kI2cScl, board::kI2cFrequencyHz);
    Wire.setTimeOut(board::kI2cTimeoutMs);
  }
  Serial.begin(115200);  // UART0 in default environment; native CDC in USB environment.
  queueResponse(bootHostRole ?
                "Universal Poofer Control: HOST DISARMED. Commands: status, arm, disarm, ping, pulse [module] <1..8> <1..1000 ms>, i2cscan\n" :
                "Universal Poofer Control: EXPANDER READ ONLY. Host controls the serial bus. Command: status\n");
}

void loop() {
  const uint32_t now = millis();
  observeSafety(now);
  applyOutputs();
  if (controller.hostRole() && now - lastInputSample >= 5) {
    inputState = shifts.readInputs();
    lastInputSample = now;
  }
  serviceSerial();
  observeSafety(millis());
  applyOutputs();
  serviceI2cScan();
  serviceStatus();
  serviceTransmit();
  if (watchdogReady) esp_task_wdt_reset();
  delay(1);
}
