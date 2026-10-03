#pragma once

#include <stdint.h>
#include "board_pins.h"

namespace poofer {

enum class StopReason : uint8_t { Boot, Manual, Estop, HardwareInhibit, ExpanderRole, LeaseExpired, InternalFault };

// Pure logic, independent of Arduino and tested on the host. All time comparisons
// use elapsed uint32_t values so normal millis() rollover remains safe.
class SafetyController {
 public:
  static constexpr uint8_t kChannels = 8;
  static constexpr uint8_t kModules = board::kModuleCount;
  static constexpr uint32_t kMaxPulseMs = 1000;
  static constexpr uint32_t kLeaseMs = 500;
  static constexpr uint32_t kEstopRestoreMs = 50;
  explicit SafetyController(bool hostRole = false) : hostRole_(hostRole) {}

  void setHostRole(bool host) {
    hostRole_ = host;
    if (!host) disarm(StopReason::ExpanderRole);
  }

  void observeEstop(bool fault, uint32_t now) {
    faultPresent_ = fault;
    if (fault) {
      healthySinceValid_ = false;
      estopLatched_ = true;
      disarm(StopReason::Estop);
    } else if (!healthySinceValid_) {
      healthySince_ = now;
      healthySinceValid_ = true;
    }
  }

  bool canArm(uint32_t now) {
    tick(now);
    if (!hostRole_ || armed_ || faultPresent_ || !healthySinceValid_ ||
        elapsed(now, healthySince_) < kEstopRestoreMs) {
      return false;
    }
    return true;
  }

  bool arm(uint32_t now) {
    if (!canArm(now)) return false;
    clearPulses();
    estopLatched_ = false;
    hardwareFaultLatched_ = false;
    armed_ = true;
    lastLease_ = now;
    return true;
  }

  void observeHardwareRun(bool run) {
    if (armed_ && !run) hardwareArmFailed();
  }

  void hardwareArmFailed() {
    hardwareFaultLatched_ = true;
    disarm(StopReason::HardwareInhibit);
  }

  bool heartbeat(uint32_t now) {
    tick(now);
    if (!armed_) return false;
    lastLease_ = now;
    return true;
  }

  bool pulse(uint8_t channel, uint32_t durationMs, uint32_t now) {
    return pulse(0, channel, durationMs, now);
  }

  bool pulse(uint8_t module, uint8_t channel, uint32_t durationMs, uint32_t now) {
    tick(now);
    if (!armed_ || faultPresent_ || module >= kModules || channel >= kChannels || durationMs == 0 ||
        durationMs > kMaxPulseMs || pulses_[module][channel].active) {
      return false;
    }
    pulses_[module][channel] = {now, durationMs, true};
    lastLease_ = now;
    return true;
  }

  void tick(uint32_t now) {
    if (!armed_) return;
    if (elapsed(now, lastLease_) >= kLeaseMs) {
      disarm(StopReason::LeaseExpired);
      return;
    }
    for (auto &module : pulses_) {
      for (auto &pulse : module) {
        if (pulse.active && elapsed(now, pulse.start) >= pulse.duration) {
          pulse.active = false;
        }
      }
    }
  }

  void disarm(StopReason reason = StopReason::Manual) {
    armed_ = false;
    clearPulses();
    reason_ = reason;
  }

  bool armed() const { return armed_; }
  bool hostRole() const { return hostRole_; }
  bool faultPresent() const { return faultPresent_; }
  bool estopLatched() const { return estopLatched_; }
  bool hardwareFaultLatched() const { return hardwareFaultLatched_; }
  StopReason stopReason() const { return reason_; }

  uint8_t outputMask(uint8_t module = 0) const {
    if (!armed_ || faultPresent_ || estopLatched_ || module >= kModules) return 0;
    uint8_t mask = 0;
    for (uint8_t channel = 0; channel < kChannels; ++channel) {
      if (pulses_[module][channel].active) mask |= static_cast<uint8_t>(1U << channel);
    }
    return mask;
  }

 private:
  struct Pulse { uint32_t start; uint32_t duration; bool active; };
  static uint32_t elapsed(uint32_t now, uint32_t then) { return now - then; }
  void clearPulses() {
    for (auto &module : pulses_) {
      for (auto &pulse : module) pulse = {0, 0, false};
    }
  }

  Pulse pulses_[kModules][kChannels] = {};
  uint32_t lastLease_ = 0;
  uint32_t healthySince_ = 0;
  bool healthySinceValid_ = false;
  bool faultPresent_ = true;
  bool estopLatched_ = false;
  bool hardwareFaultLatched_ = false;
  bool armed_ = false;
  bool hostRole_ = false;
  StopReason reason_ = StopReason::Boot;
};

}  // namespace poofer
