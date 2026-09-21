# Current checkpoint

Phase: **AWAITING_HUMAN_REVIEW**
Checkpoint: 2026-09-21 16:08 America/Chicago (21:08 UTC), documentation ready to publish (E010)
Last applied human input: H006
Owner: current Codex session, reviewing and publishing documentation. Staleness window 24 h, after checking task liveness.

## Current result
Hardware-ready dashboard. Review outputs/REPORT.md and outputs/candidate-manifest.json.
Source/configuration candidate SHA256:
`511516293b1c4a4faf00c66b5c31351634c0c3d64b1273422b0b926211c36007`.
Hashes normalize CRLF to LF; see manifest for digest method. Implementation commit
`c1794ea92c06845903356b5d003da24961913a8e` pushed to origin/main under H003 (E007).
Published checkpoint: 2ac3139. H004/H005 documentation changes are local, uncommitted;
runtime code is unchanged. Python 3.12.14 / Dash 3.4.0 /
hidapi 0.15.0; packages in uv.lock.
Defaults: USB2ANY 2047:0301, I2C 0x44, 100 kHz, on-demand LPM0, 1 s, heater off.

| Requirement | Software evidence | Overall status / remaining method |
| --- | --- | --- |
| REQ-001 USB/raw I2C | TEST-001, E002 PASS (fake HID) | UNTESTED: actual EVM, TEST-005 |
| REQ-002 paired 1 Hz/CRC/conversion | TEST-001/002/003, E002/E003 PASS | UNTESTED: physical readings, TEST-005 |
| REQ-003 values/stats/history | TEST-004, E002/E004 PASS | PASS simulated UI; physical integration pending |
| REQ-004 CSV/log/export | TEST-003/004, E002/E003/E004 PASS | PASS simulator/disk; physical integration pending |
| REQ-005 basic controls | TEST-002/003/004, E002/E004 PASS | UNTESTED: physical controls, TEST-006 |
| REQ-006 single session/reuse/errors/tests | TEST-001–004, E002 PASS | PASS software; physical failure modes pending |

36 tests, Ruff lint/format and compile check pass after review cleanup (E006).
Thirty-sample simulation median
interval 0.999076 s, no read failures/lost rows, successful close/reopen (E003).
No physical HID enumeration/open performed.
E005 reconciled the original candidate. E006 pruned unused CSS/plot setup and
verified unchanged output; the updated manifest supersedes the original digest.
Saved simulation evidence remains applicable. E008–E010/TEST-007 verifies the illustrated
README/guide, 29 relative links/anchors, four simulator screenshots and the supplied device photo.
E010 pruned duplicated README detail; lint/format checks pass. The documentation candidate
includes 34 text files; H004–H006 preserve the hardware gate.

## Architecture
Dash callbacks -> AcquisitionService -> queued DeviceSession worker -> HDC3020Sensor
-> USB2ANYHIDTransport (or simulator). Paired sample buffer and separate CSV writer.
See ARCHITECTURE.md and docs/protocol.md.

## Human action required
Approve the candidate in outputs/REPORT.md for initial USB validation: identity,
thirty approximately one-second paired samples, CSV checks and clean close/reopen.
Connect one stock HDC3020EVM and close TI's GUI. Keep heater off; no EEPROM/firmware
changes. Identify a USB serial if several boards are attached. Record approval as
H007 (or the next unused H ID) with candidate and scope before acting.

Next: follow docs/hardware-validation.md TEST-005, starting with filtered HID
discovery/identity. Preserve reports and reconcile actual hardware assumptions.
Control validation follows reliable V1 acquisition; heater testing needs explicit scope.

## Loop continuity
No hardware authorization recorded. H003 publication completed (E006/E007);
local main and origin/main both 2ac3139. H004/H005 README/guide/images and evidence are
local changes; H006 authorizes pruning, committing and pushing them to origin/main.
In flight: commit reviewed documentation/evidence with subject "Document dashboard usage
with screenshots and device photo", then `git push origin main`. Pre-operation HEAD:
2ac313965e2a5808e23edd3994f04d68ff05285c. Expected result: new local and remote main
contain the reviewed 34-file candidate and five images. Verify commit contents and
compare HEAD, origin/main and `git ls-remote origin refs/heads/main`; inspect before any
retry, never force-push. A following checkpoint commit may record the observed result.
Documentation demonstration finished and its isolated simulator/Markdown servers on
8051/8052 were stopped after clean disconnect (E008). No other server was changed.
Current gap: physical validation; zero physical attempts.
Test/browser recordings in recordings/ are ignored scratch data. Reproducible
simulation evidence is under outputs/simulation-validation/.

Ruled-out approaches:
- TMP one-byte register reads: HDC uses 16-bit commands and delayed raw reads (E001).
- Empty auto fetch as a valid measurement: all-FF latch means no fresh result (E001/E002).
- Native heater confirmation: embedded-browser stall; use inline acknowledgement (E004).
- Shift simulated auto clock on fetch: inaccurate; use autonomous periodic timing (E004).

No further hardware-independent gap found in final review. Resume at the candidate
gate; software/simulation PASS is not physical validation.
