# Consequential human inputs

## H001 - Initial objective (2026-09-20, user in this task)
User supplied agentic-engineering-template, then requested:
"Build a local Python dashboard for the TI HDC3020EVM, modeled closely after cct1123/ti-tmp-sensor-monitor."
Requirements: direct USB/USB2ANY HID; about 1 Hz temperature and RH; commands, raw I2C,
CRC and conversion; live values/statistics/synchronized history; CSV logging/export;
measurement/LPM/heater/status/reset/device/NIST controls; reuse TMP architecture/UI;
single device-session layer, robust errors and tests.
Priority verbatim: "Prioritize V1: connect → acquire temperature/RH → live plots → CSV logging.
Add advanced controls after the core acquisition path is reliable."
Applied to PROJECT.md and STATE.md. No explicit candidate-specific hardware approval yet.

## H002 - Resume engineering loop and preserve review gate (2026-09-20, user in this task)
User requested ownership of the repository objective, reading AGENTS.md first,
reconciling STATE.md against actual artifacts, closing useful gaps with evidence,
and checkpointing before stopping at validation, a review gate, or an external dependency.
Authority limit verbatim: "Do not interact with physical hardware before the explicit
approval AGENTS.md requires."
Applied to STATE.md; reconciliation is E005. This steering preserves H001's objective
and priorities and does not approve the candidate for physical access. No requirement
or existing software validation was changed.

## H003 - Review, minimally clean up, commit and push (2026-09-20, user in this task)
User explicitly requested review of current changes, pruning unnecessary or obsolete
code/files, only minimal justified fixes, relevant checks, final diff inspection,
then commit and push. Preserve intentional work and report changes, validation,
commit hash and pushed branch. This authorizes software review and Git publication
while the candidate awaits hardware review; it does not authorize device access.
Applied to STATE.md. Hardware approval remains pending.

## H004 - Illustrated README and usage demonstration (2026-09-21, user in this task)
User requested improving README, showing how to use the dashboard, and including
screenshots demonstrating functions, with the TMP monitor README as the reference:
https://github.com/cct1123/ti-tmp-sensor-monitor/blob/main/README.md.
Scope: documentation and authentic screenshots from this application's simulator.
No physical-device authorization; retain the candidate hardware review gate.

## H005 - Add supplied device photograph (2026-09-21, user in this task)
User requested placing the attached device picture in README. Source attachment:
codex-clipboard-b5a2e497-62b7-4a6f-9efd-e9220e3fbbe0.png.
Scope: preserve the supplied picture as a repository asset and embed it in README.
No change to runtime behavior or hardware authorization.

## H006 - Prune, commit and push documentation (2026-09-21, user in this task)
User requested "prune commit push" for the pending README, guide, images and records.
Review and remove unnecessary material, validate, then publish to the existing
main branch on origin. Preserve intentional work and the physical review gate.

## H007 - Approve connected-board validation (2026-09-23, user in this task)
User reported that the HDC sensor is connected to this computer and explicitly
approved testing the controller software with the HDC3020EVM to complete validation.
Applied to the reviewed candidate in outputs/REPORT.md (SHA256
`511516293b1c4a4faf00c66b5c31351634c0c3d64b1273422b0b926211c36007`):
authorize TEST-005 identity, 30 approximately one-second paired samples, CSV checks,
close/reopen, and then non-heater volatile controls in TEST-006 under
docs/hardware-validation.md. Preserve its no-EEPROM/firmware and heater-off bounds.
The separate minimum-element heater pulse scope has been requested from the user
and remains unresolved until an explicit answer is received.

## H008 - Easy software usage guide (2026-09-23, user in this task)
User requested: "easy step by step guide use the software". Add a short,
first-use guide for the existing local dashboard and correct stale documentation
that still says all physical validation is pending. This changes documentation
only; H007 hardware authority and the separately pending heater scope are
unchanged. Applied to README.md, docs/quick-start.md, docs/usage-guide.md and
STATE.md; evidence is E023.

## H009 - Bash and uv documentation preference (2026-09-23, user in this task)
User requested: "prefer sh, bash. use uv for the management. simplify and prune".
Update the first-use instructions and related README/illustrated-guide commands
to Bash with uv; remove redundant setup and the alternative pip/venv path.
This is a documentation preference, not a change to hardware authority,
requirements or passing validation. Applied to README.md, docs/quick-start.md,
docs/usage-guide.md, docs/hardware-validation.md and STATE.md; evidence is E024.

## H010 - Review, clean up, commit and push (2026-09-23, user in this task)
User requested: "clean up. review commit. push". Review and prune the pending
hardware-validation changes and evidence, run relevant software checks, then
commit and push to the existing main branch on origin. Preserve physical test
evidence and the separately pending heater authorization. This request does not
authorize another device interaction.

## H011 - Re-test the connected sensor (2026-09-24, user in this task)
User reported that an HDC3020 sensor is connected to this computer and requested
testing the repository with it, explicitly approving uv, Python, and a browser
for hardware testing. Apply this to the already reviewed, published non-heater
candidate and its TEST-005/dashboard procedures. This general testing permission
does not resolve the pending request for a specific attended heater pulse; leave
the heater off unless the user separately confirms that pulse and its conditions.

## H012 - Identify the HDC3020EVM among two bridges (2026-09-24, user in this task)
USB enumeration found two USB2ANY bridges, neither with H007's prior serial.
The user asked the agent to evaluate them and find the HDC3020EVM. Scope:
sequentially query the HDC3020 manufacturer/NIST identity at address 0x44 on
each bridge, then run non-heater testing only on a positively identified board.
This does not approve a heater-on pulse.

## H013 - Clarify the device's purpose (2026-09-24, user in this task)
User corrected the framing: "hdc3020EVM is not a heater. it's a temperature and
humidity sensor". The EVM's primary purpose is temperature/RH measurement.
TI's HDC3020 includes an optional integrated heater for condensation handling;
that feature does not make the board a heater. This clarification does not by
itself authorize activating the feature or explicitly remove the previously
requested heater control from the project's acceptance criteria. A focused
scope question was sent; no device interaction is needed to resolve it.

## H014 - Retain optional heater control (2026-09-24, user in this task)
In response to the focused acceptance-scope question, the user answered
"No, keep heater control." Retain the originally requested HDC3020 integrated
heater control in REQ-005. This answer alone did not approve a physical pulse.

## H015 - Approve one bounded integrated-heater pulse (2026-09-24, user in this task)
The user explicitly answered "Yes, conditions confirmed" to one attended
five-second pulse of the HDC3020's optional integrated heater at minimum element
0x0001 on USB serial `87F2A26E08002500`, confirming no heat-sensitive samples
or equipment nearby. Scope: the prepared TEST-006 pulse, status-off/cooldown,
CSV/plot-marker checks and safe cleanup only. No repeated pulse, higher heater
setting, persistent writes or firmware action is authorized. Verify the board
identity and initial state before acting; preserve actual measurements and
shutdown result. This resolves the H007 heater-scope request for this candidate
and these exact conditions.

## H016 - Automatic CSV capture for monitoring (2026-09-24, user in this task)
After asking whether long recordings should save automatically, the user agreed
with the proposed monitoring behavior: "yes it makes sense for the monitoring".
The immediately preceding proposal was to open a CSV automatically after a
successful Start monitoring connection, show filename/write errors, rotate to a
new file each UTC day, and retain a manual option for quick checks. Apply this
to REQ-004 and the local dashboard. A failed connection must not create a
recording; files must drain and close on disconnect/shutdown. The prior H015
single heater-pulse authorization is already consumed and does not authorize
another pulse. This is a new software candidate, with affected logging/UI
validation invalidated until retested.

## H017 - Remove sample-interval helper note (2026-09-24, user in this task)
The user requested removal of the GUI note "1 Hz by default. Live plots retain
up to 7,200 paired samples." Remove that text from Device setup only. Keep the
actual default interval, buffer size, automatic CSV behavior, and pending H016
hardware review intact. This is a visual copy change, not hardware approval.

## H018 - Documentation cleanup and publication (2026-09-25, user in this task)
The user requested "update readme, doc, clean up, prune, commit push". Scope:
bring the README and guides into agreement with the H016/H017 candidate and
preserved physical evidence, remove only confirmed obsolete material, and
commit/push the reviewed source and evidence to the existing repository.
This is publication authority, not approval to operate the revised candidate
with hardware. Keep the H016 physical review gate pending.
