#pragma once

#include <stdint.h>
#include "SafetyController.h"

namespace poofer {

// Adapter owns inhibit(), clearOutputs(), safePermit(), hardwareRun(),
// eventPending(), tryReleaseInhibit(), waitMicros(us), and nowMillis().
// Only this explicit arming handshake may lower MCU_OE_N. It must stay LOW
// during an armed session, including between pulses, to avoid new re-arm edges.
template <typename Adapter>
class HardwareArming {
 public:
  static constexpr uint16_t kInhibitSettleUs = 1000;
  static constexpr uint16_t kFeedbackTimeoutUs = 1000;
  static constexpr uint16_t kPollUs = 10;

  explicit HardwareArming(Adapter &adapter) : adapter_(adapter) {}

  bool arm(SafetyController &controller, uint32_t now) {
    if (!controller.canArm(now)) {
      adapter_.inhibit();
      controller.disarm();
      adapter_.clearOutputs();
      return false;
    }
    adapter_.inhibit();
    adapter_.clearOutputs();  // Zero storage BEFORE producing a fresh arm edge.
    adapter_.waitMicros(kInhibitSettleUs);  // Conservative inhibit setup before the HC74 arm edge.
    if (!adapter_.safePermit() || adapter_.eventPending() ||
        !adapter_.tryReleaseInhibit()) return fail(controller);

    for (uint16_t waited = 0; waited <= kFeedbackTimeoutUs; waited += kPollUs) {
      if (!adapter_.safePermit() || adapter_.eventPending()) return fail(controller);
      if (adapter_.hardwareRun()) {
        if (controller.arm(adapter_.nowMillis())) return true;
        return fail(controller);
      }
      if (waited < kFeedbackTimeoutUs) adapter_.waitMicros(kPollUs);
    }
    return fail(controller);
  }

 private:
  bool fail(SafetyController &controller) {
    adapter_.inhibit();
    controller.hardwareArmFailed();
    adapter_.clearOutputs();
    return false;
  }
  Adapter &adapter_;
};

}  // namespace poofer
