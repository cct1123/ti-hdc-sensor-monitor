# HDC3020EVM monitor: physical validation report

**Phase: HARDWARE_READY, awaiting human review for the H016 candidate.** The
previous manual-recording candidate passed physical acquisition, dashboard,
CSV and volatile-control checks (E034). Automatic CSV start and UTC-day rotation
passed software and simulator checks (E035), but the changed recording/session
path has not yet been checked with an EVM. The HDC3020EVM is a temperature/RH sensor
evaluation board; its integrated heater is an optional feature for condensation
handling and stays off during normal monitoring ([TI EVM overview](https://www.ti.com/tool/HDC3020EVM),
[HDC3020 datasheet](https://www.ti.com/lit/ds/symlink/hdc3020.pdf)). Sensor accuracy was not
calibrated or compared with an independent reference.

## Candidate and configuration

The H007 approval applied to the reviewed hardware-ready candidate SHA256
`511516293b1c4a4faf00c66b5c31351634c0c3d64b1273422b0b926211c36007`
([candidate manifest](candidate-manifest.json)); its implementation was published
as `c1794ea92c06845903356b5d003da24961913a8e`, followed by documentation
commit `586f9c5680bd9b1ce145198eed5fac4f7522830c`. The first physical
attempt found a bridge-pullup configuration error (E012). D003 corrected that
volatile setting and the diagnostic message; the corrected version is the one
tested below. The original manifest remains the review-gate record. The H010
source/configuration snapshot is in [validation-manifest.json](validation-manifest.json).
H016 changes runtime recording and session lifecycle; its distinct reviewed
snapshot is [auto-record-candidate-manifest.json](auto-record-candidate-manifest.json).
H019 adds bridge-selection and I²C timeout diagnostics after a user-reported
blank-serial connection failure. With two enumerated USB2ANY bridges, blank
serial is rejected before opening either; it does not search for an HDC3020.
The user reports that explicitly selecting `87F2A26E08002500` succeeds.
Software regression tests cover the new error paths (E040); no connected-board
check of this revised source has run. The reported `-49` means an I²C write
timeout; without a fresh enumeration from that failed session, its selected
bridge and precise bus cause remain unknown.
The previous H007/H010 physical results do not validate the new auto-save path.

First validated device: one Texas Instruments USB2ANY/OneDemo HID bridge, VID:PID
`2047:0301`, USB serial `88F2A26E25000200`, firmware `2.8.2.0`, I2C address
`0x44`, manufacturer `0x3000`, CRC-checked NIST ID `1A73E0120F3E`.
Configuration: 100 kHz, 7-bit I2C, bridge-managed pullups off because the
stock EVM has passive I2C pullups to its USB-powered 3.3 V rail; on-demand
LPM0, one-second acquisition interval, heater off on normal connect/close.
Runtime: Windows; Python 3.12.14 on the first board and 3.12.13 on the second;
Dash 3.4.0, Plotly 7.1.0, hidapi 0.15.0; packages are locked in `uv.lock`.

## Delivered system

Dash callbacks → AcquisitionService → one queued DeviceSession worker →
HDC3020Sensor → USB2ANYHIDTransport. A paired sample buffer and independent
CSV writer feed live values, min/mean/max, synchronized history plots, recording,
last-file download and current-buffer export. Controls provide on-demand/auto
1 Hz/auto 0.5 Hz, LPM0–3, status read/clear, manufacturer/NIST ID, soft reset,
and a minimum-element timed pulse of the sensor's integrated heater. The
heater-on path also passed one H015-approved physical pulse (E033).
For H016, successful **Start monitoring** opens a CSV automatically unless the
operator opts out. The writer rotates at the first accepted sample of a new UTC
day; Stop pauses sampling while the file remains open, and disconnect drains and
closes it. Manual Record remains available.

## Validation evidence

| Method | Result | Evidence |
| --- | --- | --- |
| TEST-001–004: fake-HID/driver/session/recording/Dash software regressions | 36 PASS, repeated before the second-board run | [earlier unit transcript](hardware-fix-unit-tests.txt), E013/E027 |
| Lint and formatting | Ruff check PASS on current runtime; earlier format check PASS | E021/E027 |
| First physical TEST-005 attempt | FAIL: bridge error -54 before sensor identity | [failure report](hardware-validation/validation_20260923_200536_567859.json), E012 |
| Physical identity diagnostic after D003 | PASS: manufacturer/NIST/firmware, heater off, clean close | [transcript](hardware-validation/identity-diagnostic.txt), E014 |
| Physical TEST-005: 30 samples, CSV, close/reopen | PASS: median 1.000613 s (0.978251–1.020820 s); 0 read failures/lost rows | [report](hardware-validation/validation_20260923_200902_021356.json), [CSV](hardware-validation/hardware-validation_20260923_200902_021356.csv), E015 |
| Physical non-heater TEST-006: modes/LPM/status/reset | PASS: all 12 combinations; auto cadence 1.0172985/2.0151055 s; 0 failures | [report](hardware-validation/controls_20260923_201208_417991.json), E017 |
| Dash HTTP callback integration with actual EVM | PASS: paired values/plots, 3 CSV rows, export/download, settings, disconnect | [report](hardware-validation/dashboard_20260923_201425_005010.json), [CSV](hardware-validation/hdc3020_20260923_201425_201775.csv), E019 |
| Browser layout, zoom/follow and controls in simulation | PASS, simulation scope | E004/E008 |
| H016 automatic-recording software regression | PASS: 42 tests, Ruff check/format; UTC rollover, error and lifecycle cases, repeated for publication | E035/E038 |
| H016 browser simulator | PASS: checked opt-in, seven paired rows, pause, disconnect and closed-file download readiness | E035 |
| H016 physical automatic-recording check | UNTESTED pending review of this candidate | [procedure](../docs/hardware-validation.md), REQ-004/006 |
| Physical integrated-heater pulse and cooldown | PASS: one 5.047 s minimum-element pulse, status-on/off, cooldown pairs, CSV/plot flags, clean close | [report](hardware-validation/heater_20260924_211939_857607.json), [CSV](hardware-validation/heater-validation_20260924_211940_043252.csv), E033 |
| Independent accuracy/calibration check | UNTESTED: no reference instrument supplied | Limitation, not an acceptance claim |

The physical samples were about 23 °C and 45–47 %RH during this session. Their
CRC and raw-word conversion checks, continuity and timing support normal sensor
communication; they do not establish absolute measurement accuracy. One 0.5 Hz
LPM3 humidity result was lower than the other mode readings; no accuracy or
noise claim is inferred from these brief tests.

## Connected-board retest, 2026-09-24

The newly connected HDC3020EVM was positively identified among two USB2ANY
bridges: serial `87F2A26E08002500`, firmware 2.8.2.0, manufacturer 0x3000,
CRC-valid NIST ID `1BADE0120F3E` (E028). The other bridge did not acknowledge
the sensor at 0x44. This is a different serial from the board used on 2026-09-23.

Software regressions passed 36/36 and Ruff passed (E027). On the new board,
TEST-005 passed 30 paired samples at median interval 0.999964 s, zero failed
reads, matching CSV rows and clean close/reopen/close (E029). Physical Dash HTTP
callbacks passed live values, paired plots, recording/export/download, one
non-heater settings change and disconnect (E030). A live browser session showed
about 22.7 °C and 43 %RH, updating plots, zero failed reads, a seven-row CSV
with zero dropped, and normal Stop/Disconnect; the local app exited (E031).
Supporting reports and CSVs are in `outputs/hardware-validation/` with
20260924 timestamps. These observations do not establish absolute sensor
accuracy. The prior all-mode/LPM control result applies to the earlier board;
only auto 1 Hz/LPM1 was repeated on this board during monitoring; the integrated
heater stayed off during that run.

Under H014/H015, the user retained the optional heater control and approved
one attended pulse on this board, with no heat-sensitive samples or equipment
nearby. Fresh preflight matched the board identity and confirmed heater-off
status (E032). The single minimum-element pulse lasted 5.047 s; status turned
on, then off automatically. Thirteen paired samples and their CSV flags passed,
including two heater-on rows and a final off row. Baseline, heater-on peak and
final temperatures were 22.509, 23.144 and 22.573 °C. The final status read
was off, zero reads failed, zero rows were lost, and disconnect was clean (E033).
This demonstrates the control and recovery path, not a calibrated thermal effect.

## Failure diagnosis and correction

The initial configuration enabled bridge-managed I2C pullups. USB2ANY returned
error `-54` on the first sensor command. TI defines this as missing 3.3 V EXT
power for those bridge pullups, while the EVM schematic shows its own 10 kΩ
pullups on the USB-powered 3.3 V rail ([protocol details](../docs/protocol.md),
E012/D003). Disabling bridge pullups resolved the error without a board-power
command. The identity diagnostic preceded renewed acquisition; all subsequent
physical checks passed. No firmware, EEPROM, offset, threshold, general-call
reset or external power setting was changed.

## Operation and limits

The [physical procedure](../docs/hardware-validation.md) documents exact
commands and expected results; the [quick start](../docs/quick-start.md) covers
normal temperature/RH monitoring. H013 clarified the EVM's primary purpose;
H014 retained its optional integrated-heater control and H015 authorized the
one physical check. A connection loss can prevent software from confirming
heater shutdown; unplug the EVM if heater status is uncertain. Physical browser
rendering was inspected with live readings and plots on the second board (E031).

For normal shutdown, stop monitoring and disconnect; disconnect drains an active
recording. Stop recording first only when ending a file while remaining connected. The worker
attempts heater-off, exit-auto and HID close. On a fault, preserve JSON/CSV
evidence and check actual device state before reconnecting. Volatile mode/LPM
changes and soft reset are restored to on-demand LPM0 at the next connection;
no persistent sensor memory is intentionally written. Run only one local
process per board. E034 established the prior candidate's criteria; H016's new
REQ-004 path and affected REQ-006 integration await physical confirmation.
Absolute sensor accuracy and production deployment qualification were not
acceptance claims and have not been independently established.
