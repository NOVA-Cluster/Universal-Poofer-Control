#pragma once

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "board_pins.h"

namespace poofer {
enum class CommandKind { Invalid, Arm, Disarm, Ping, Status, Pulse, I2cScan };
struct Command {
  CommandKind kind;
  uint8_t module;
  uint8_t channel;  // zero based internally
  uint32_t duration;
};

inline bool number(const char *begin, size_t count, uint32_t limit, uint32_t &out) {
  if (count == 0) return false;
  out = 0;
  for (size_t i = 0; i < count; ++i) {
    if (begin[i] < '0' || begin[i] > '9') return false;
    const uint32_t digit = static_cast<uint32_t>(begin[i] - '0');
    if (out > limit / 10 || (out == limit / 10 && digit > limit % 10)) return false;
    out = out * 10 + digit;
  }
  return true;
}

inline Command parseCommand(const char *line) {
  const Command invalid = {CommandKind::Invalid, 0, 0, 0};
  if (strcmp(line, "arm") == 0) return {CommandKind::Arm, 0, 0, 0};
  if (strcmp(line, "disarm") == 0) return {CommandKind::Disarm, 0, 0, 0};
  if (strcmp(line, "ping") == 0) return {CommandKind::Ping, 0, 0, 0};
  if (strcmp(line, "status") == 0) return {CommandKind::Status, 0, 0, 0};
  if (strcmp(line, "i2cscan") == 0) return {CommandKind::I2cScan, 0, 0, 0};
  if (strncmp(line, "pulse ", 6) != 0) return invalid;
  const char *channelStart = line + 6;
  const char *separator = strchr(channelStart, ' ');
  if (separator == nullptr) return invalid;
  const char *secondSeparator = strchr(separator + 1, ' ');
  uint32_t module = 0;
  if (secondSeparator != nullptr) {
    if (!number(channelStart, static_cast<size_t>(separator - channelStart),
                board::kModuleCount - 1, module)) return invalid;
    channelStart = separator + 1;
    separator = secondSeparator;
  }
  uint32_t channel = 0;
  uint32_t duration = 0;
  if (!number(channelStart, static_cast<size_t>(separator - channelStart), 8, channel) ||
      channel == 0 || !number(separator + 1, strlen(separator + 1), 1000, duration) ||
      duration == 0) return invalid;
  return {CommandKind::Pulse, static_cast<uint8_t>(module), static_cast<uint8_t>(channel - 1), duration};
}
}  // namespace poofer
