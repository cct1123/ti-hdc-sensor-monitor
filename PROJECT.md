# HDC3020EVM local monitor

## Intent and source
User request, 2026-09-20, recorded as H001 in records/HUMAN_INPUTS.md.
Build a local Python dashboard closely modeled on cct1123/ti-tmp-sensor-monitor.
V1 priority: connect -> acquire paired temperature/RH at about 1 Hz -> live plots -> CSV logging.
Then implement measurement mode, LPM, heater, status read/clear, soft reset, and device/NIST identity.

## Observable acceptance criteria
- REQ-001: Direct USB/USB2ANY HID connection to HDC3020EVM; bounded timeouts, exact framing,
  raw I2C write/read, bridge identity and useful errors for missing/ambiguous/unplugged devices.
- REQ-002: CRC-checked temperature and RH from the same conversion at roughly 1 Hz.
  Reject short/corrupt/not-ready responses; use TI's 16-bit conversion formula.
- REQ-003: Live paired values, min/mean/max, bounded history and synchronized plots with pan/zoom/follow.
- REQ-004: Start/stop CSV logging, drained accepted rows, visible disk/queue errors, last-file download
  and current-buffer export, UTC timestamps, paired readings and configuration metadata.
- REQ-005: Basic volatile controls and CRC-checked status/manufacturer/NIST identity.
- REQ-006: A single session worker owns all device I/O; tests cover lifecycle, serialization,
  bad responses, disconnect, command failures and recording; reuse reference architecture/UI.

## Decisions and resources
Windows is the initial target (current workspace); Python/Dash and hidapi match the TMP app.
Stock EVM address is 0x44. Default I2C speed: 100 kHz. Default: on-demand LPM0, interval 1 s.
Use a clearly labeled software simulator to validate UI and lifecycle without hardware.
History limit: 7,200 paired samples, derived from TMP monitor. All clients share one local session.
References: docs/protocol.md. Reused MIT code retains LICENSE and provenance in NOTICE.md.

## Boundaries and unknowns
At initial setup, board availability, identity and firmware were unknown. H007
approved the reviewed candidate's physical integration on 2026-09-23; current
device details and validation status are in STATE.md and outputs/REPORT.md.
Follow AGENTS.md's explicit candidate-review gate for future unapproved scopes.
No firmware flashing, EEPROM/offset programming, general-call reset or board power control.
Heater controls must show their effect on measurement validity and shut off on orderly disconnect;
loss of USB communication cannot guarantee heater shutdown. Physical heater testing needs explicit scope.
Sensor accuracy and calibration require independent physical evidence.
