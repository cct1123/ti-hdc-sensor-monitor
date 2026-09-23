# HDC3020EVM monitor: physical validation report

**Phase: BLOCKED; resume HARDWARE_VALIDATION after heater-scope input.** Core
acquisition, recording, dashboard integration, and non-heater controls pass on
the connected EVM. Heater-on behavior awaits separate explicit scope; sensor
accuracy has not been calibrated or compared with an independent reference.
This is not yet a fully validated release.

## Candidate and configuration

The H007 approval applied to the reviewed hardware-ready candidate SHA256
`511516293b1c4a4faf00c66b5c31351634c0c3d64b1273422b0b926211c36007`
([candidate manifest](candidate-manifest.json)); its implementation was published
as `c1794ea92c06845903356b5d003da24961913a8e`, followed by documentation
commit `586f9c5680bd9b1ce145198eed5fac4f7522830c`. The first physical
attempt found a bridge-pullup configuration error (E012). D003 corrected that
volatile setting and the diagnostic message; the corrected version is the one
tested below. The original manifest remains the review-gate record. Current
source/configuration hashes are in [validation-manifest.json](validation-manifest.json).

Actual device: one Texas Instruments USB2ANY/OneDemo HID bridge, VID:PID
`2047:0301`, USB serial `88F2A26E25000200`, firmware `2.8.2.0`, I2C address
`0x44`, manufacturer `0x3000`, CRC-checked NIST ID `1A73E0120F3E`.
Configuration: 100 kHz, 7-bit I2C, bridge-managed pullups off because the
stock EVM has passive I2C pullups to its USB-powered 3.3 V rail; on-demand
LPM0, one-second acquisition interval, heater off on normal connect/close.
Runtime: Windows, Python 3.12.14, Dash 3.4.0, Plotly 7.1.0, hidapi 0.15.0;
versions are locked in `uv.lock`.

## Delivered system

Dash callbacks → AcquisitionService → one queued DeviceSession worker →
HDC3020Sensor → USB2ANYHIDTransport. A paired sample buffer and independent
CSV writer feed live values, min/mean/max, synchronized history plots, recording,
last-file download and current-buffer export. Controls provide on-demand/auto
1 Hz/auto 0.5 Hz, LPM0–3, status read/clear, manufacturer/NIST ID, soft reset,
and a minimum-element timed heater pulse in software. The heater-on path has
only simulated and unit evidence so far.

## Validation evidence

| Method | Result | Evidence |
| --- | --- | --- |
| TEST-001–004: fake-HID/driver/session/recording/Dash software regressions | 36 PASS after pullup fix | [unit transcript](hardware-fix-unit-tests.txt), E013 |
| Lint and formatting | PASS, 25 Python files | E021 |
| First physical TEST-005 attempt | FAIL: bridge error -54 before sensor identity | [failure report](hardware-validation/validation_20260923_200536_567859.json), E012 |
| Physical identity diagnostic after D003 | PASS: manufacturer/NIST/firmware, heater off, clean close | [transcript](hardware-validation/identity-diagnostic.txt), E014 |
| Physical TEST-005: 30 samples, CSV, close/reopen | PASS: median 1.000613 s (0.978251–1.020820 s); 0 read failures/lost rows | [report](hardware-validation/validation_20260923_200902_021356.json), [CSV](hardware-validation/hardware-validation_20260923_200902_021356.csv), E015 |
| Physical non-heater TEST-006: modes/LPM/status/reset | PASS: all 12 combinations; auto cadence 1.0172985/2.0151055 s; 0 failures | [report](hardware-validation/controls_20260923_201208_417991.json), E017 |
| Dash HTTP callback integration with actual EVM | PASS: paired values/plots, 3 CSV rows, export/download, settings, disconnect | [report](hardware-validation/dashboard_20260923_201425_005010.json), [CSV](hardware-validation/hdc3020_20260923_201425_201775.csv), E019 |
| Browser layout, zoom/follow and controls in simulation | PASS, simulation scope | E004/E008 |
| Physical heater pulse and cooldown | UNTESTED: specific authorization pending; simulator rehearsal PASS | TEST-006, E020 |
| Independent accuracy/calibration check | UNTESTED: no reference instrument supplied | Limitation, not an acceptance claim |

The physical samples were about 23 °C and 45–47 %RH during this session. Their
CRC and raw-word conversion checks, continuity and timing support normal sensor
communication; they do not establish absolute measurement accuracy. One 0.5 Hz
LPM3 humidity result was lower than the other mode readings; no accuracy or
noise claim is inferred from these brief tests.

## Failure diagnosis and correction

The initial configuration enabled bridge-managed I2C pullups. USB2ANY returned
error `-54` on the first sensor command. TI defines this as missing 3.3 V EXT
power for those bridge pullups, while the EVM schematic shows its own 10 kΩ
pullups on the USB-powered 3.3 V rail ([protocol details](../docs/protocol.md),
E012/D003). Disabling bridge pullups resolved the error without a board-power
command. The identity diagnostic preceded renewed acquisition; all subsequent
physical checks passed. No firmware, EEPROM, offset, threshold, general-call
reset or external power setting was changed.

## Remaining validation and operation

The [physical procedure](../docs/hardware-validation.md) documents exact
commands and expected results; the [quick start](../docs/quick-start.md) covers
normal use. The only remaining physical control check is
one attended, minimum-element (`0x0001`) five-second heater pulse with no
heat-sensitive sample or equipment nearby, followed by status-off verification
and cooldown observation. A bounded runner is prepared and has passed its
simulator rehearsal (E020). Keep the heater off until that separate scope is
explicitly granted. A connection loss can prevent software from confirming
heater shutdown; unplug the EVM if heater status is uncertain. Physical browser
rendering was not separately inspected; actual HTTP callbacks were exercised
with hardware and browser visuals were checked in simulation.

**Resumption condition:** an explicit yes/no answer to the single-pulse request
in STATE.md. A yes must confirm the board will be attended and no heat-sensitive
samples or equipment are nearby. A no leaves the heater requirement physically
unvalidated. No useful independent work remains at this checkpoint (E022).

For normal shutdown, stop recording, stop monitoring and disconnect. The worker
attempts heater-off, exit-auto and HID close. On a fault, preserve JSON/CSV
evidence and check actual device state before reconnecting. Volatile mode/LPM
changes and soft reset are restored to on-demand LPM0 at the next connection;
no persistent sensor memory is intentionally written. Run only one local
process per board. The system makes no calibrated accuracy or production
readiness claim until the outstanding requirements are addressed.
