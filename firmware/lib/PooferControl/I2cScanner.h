#pragma once

#include <stdint.h>

namespace poofer {
enum class ScanState { Idle, Active, Complete, Cancelled, Deadline, BusError };

// Pure scheduler. The hardware adapter may perform at most one address-only
// transaction for each successful nextAddress() call. No scans while armed.
class I2cScanner {
 public:
  static constexpr uint8_t kFirstAddress = 0x08;
  static constexpr uint8_t kLastAddress = 0x77;
  static constexpr uint32_t kProbeGapMs = 2;
  static constexpr uint32_t kMaxScanMs = 1500;

  bool start(uint32_t now, bool hostRole, bool armed, bool ready) {
    if (!eligible(hostRole, armed, ready) || active()) return false;
    state_ = ScanState::Active;
    started_ = now;
    lastProbe_ = now - kProbeGapMs;
    next_ = kFirstAddress;
    probes_ = 0;
    found_ = 0;
    error_ = 0;
    return true;
  }

  bool nextAddress(uint32_t now, bool hostRole, bool armed, bool ready, uint8_t &address) {
    if (!active()) return false;
    if (!eligible(hostRole, armed, ready)) {
      cancel();
      return false;
    }
    if (now - started_ >= kMaxScanMs) {
      state_ = ScanState::Deadline;
      return false;
    }
    if (now - lastProbe_ < kProbeGapMs) return false;
    lastProbe_ = now;
    address = next_++;
    ++probes_;
    if (address == kLastAddress) state_ = ScanState::Complete;
    return true;
  }

  void recordResult(uint8_t status) {
    if (status == 0) ++found_;
    else if (status != 2) {  // Wire code 2 is normal address NACK.
      error_ = status;
      state_ = ScanState::BusError;
    }
  }

  void cancel() { if (active()) state_ = ScanState::Cancelled; }
  bool active() const { return state_ == ScanState::Active; }
  ScanState state() const { return state_; }
  uint8_t probes() const { return probes_; }
  uint8_t found() const { return found_; }
  uint8_t error() const { return error_; }

 private:
  static bool eligible(bool hostRole, bool armed, bool ready) {
    return hostRole && !armed && ready;
  }
  ScanState state_ = ScanState::Idle;
  uint32_t started_ = 0;
  uint32_t lastProbe_ = 0;
  uint8_t next_ = kFirstAddress;
  uint8_t probes_ = 0;
  uint8_t found_ = 0;
  uint8_t error_ = 0;
};
}  // namespace poofer
