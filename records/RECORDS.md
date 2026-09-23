# Evidence and decisions

## E001 - Reference inspection (2026-09-20)
Empty project worktree with unborn main branch. Public TMP reference cloned to temporary storage;
revision b8e1e4e7116943c826d3b59626059cd2b6d15923, identical to clean C:/projects/tmpsensor.
Inspected Dash UI, session/acquisition architecture, CSV worker, HID codec and tests.
TI HDC3020 datasheet SNAS778D and GUI v1.0.7 source verified command table, two CRC words,
0x44 address, conversion timings and raw USB2ANY read/write payloads. See docs/protocol.md.
No physical hardware discovery or access.

## D001 - V1 design
Reuse reference CSS and core software patterns; isolate sensor codec from USB packet codec.
Single on-demand paired conversion each second by default. Use monotonic scheduling and UTC sample times.
On CRC failures discard the whole pair; report failures and bound consecutive retries.
Persist no sensor EEPROM settings. Simulation stays visibly identified in UI and CSV.

## E002 - Software verification (2026-09-20 local / 2026-09-21 UTC)
TEST-001/002/003/004: `python -m unittest discover -s tests -v`: **36 tests PASS**;
see outputs/unit-tests.txt. Real HDC driver over a fake HID bridge also passes.
Coverage: bridge CRC/framing/errors/sequence/discovery, both sensor CRCs, conversions,
command/timing/identity/control behavior, serialized I/O and bounded command queue,
pause/reconnect/cancellation, failed writes, retries, heater deadline, CSV queue
overflow/disk-full/draining, plots and simulated Dash callback integration.
Ruff check and formatting check pass. Python 3.12.14, Dash 3.4.0, Plotly 7.1.0,
hidapi 0.15.0, Ruff 0.16.8; dependency versions captured by uv.lock.

Windows sandbox/private-temp ACL interaction initially prevented CSV tests from
opening their own temp directories. Same tests passed outside the sandbox; test
assertions were not relaxed. No physical hardware was opened in either run.

## E003 - Bounded simulation validation
TEST-003/004: `python -m hdcsensor.validate --samples 30 --output outputs/simulation-validation` PASS.
Report: outputs/simulation-validation/validation_20260921_030438_901402.json.
30 pairs, median interval 0.999076 s (range 0.975828–1.019840 s), zero failed reads,
zero dropped rows, exact CSV/value/timestamp agreement, clean close and successful
identity-preserving reopen/close. Physical validation: false.

## E004 - Browser verification
Local Dash preview, simulator only. Verified paired live values, temperature/RH
plots, zoom changes to held history, Follow live restores live mode, settings
tab persistence, auto-mode apply, recording stop and visible download readiness.
One saved browser CSV had 175 rows; final-layout run saved 77 rows with zero drops.
Final-layout session reached 267 samples with zero failed reads before clean disconnect.
Inspected full-page monitor and settings screenshots at the browser's available widths.

Found unstable graph height when relying on Plotly's responsive default; fixed
with an explicit 500 px graph container. Removed Plotly cloud-share toolbar action.
Found simulator clock incorrectly re-anchored after a late auto read; corrected
to autonomous periodic timing, covered by a regression test. These do not establish
physical board timing. Browser callback errors during intentional server restart
were resolved by reload. Embedded browser stalled on native heater dialog; replaced
native dialogs with inline heater acknowledgement and direct documented soft reset.
Final browser check confirmed acknowledgement gating, heater status on during the
simulated pulse, automatic shutoff while sampling was paused, soft reset and resumed
monitoring. Final preview is simulation, heater off, not recording.

## D002 - Candidate boundary
All meaningful hardware-free implementation and tests are complete. Retain explicit
AWAITING_HUMAN_REVIEW gate; requested physical scope is initial identity/acquisition/
CSV/close/reopen with heater kept off. Heater-on validation remains a separate scope.
No physical accuracy, calibration, firmware compatibility or thermal behavior is claimed.

## E005 - Review-gate checkpoint reconciliation (2026-09-20 22:17 America/Chicago)
Applied H002 after reading AGENTS.md, PROJECT.md, STATE.md, the human-input record,
candidate report and referenced evidence. Recomputed all source/configuration hashes:
all 33 manifest entries match the current files, with no mismatches; the manifest
digest also matches candidate `df63d639b78ab347692a7e789d91ec40972905c13d883df11c114b7e1ea6b74a`.
Inspected outputs/unit-tests.txt (36 tests PASS) and E003's saved JSON (30 samples,
0.999076 s median interval, no failed reads or dropped rows, successful close/reopen).
These remain software/simulation evidence, not newly executed tests or physical evidence.
Git status remains an uncommitted initial project. No in-flight external action or
candidate-specific hardware approval was found. No implementation change or new
hardware-independent gap was identified; E002/E003/E004 remain applicable.
No physical discovery, initialization, sampling, actuation or cleanup was performed.
Retain AWAITING_HUMAN_REVIEW under AGENTS.md; next useful action remains the prepared
TEST-005 procedure after explicit approval. Do not infer approval from the loop prompt.

## E006 - Pre-publication software review and cleanup (2026-09-20)
Under H003, reviewed application callbacks, device/session ownership and cleanup,
HID framing, sensor commands, simulation, recording, validation CLI, tests, docs,
licenses and the publication file inventory. No hardware interaction occurred.
Pruned 73 unused CSS selector branches inherited from TMP's register editor,
draft/status widgets and removed decoration, plus unused settings-card h2/hr rules.
Kept React Select and dynamic status styles. Removed redundant plot-range fallback
and per-channel layout/empty-state setup discarded when composing the final plot.
No device/session/recording changes or additional features were needed.

TEST-001–004: 36 tests PASS in 3.735 s; outputs/review-unit-tests.txt. Ruff check,
Ruff format check (22 Python files) and compileall PASS after cleanup. Existing
format conventions restored after a mixed-newline edit; no assertions were relaxed.
The before/after representative two-channel plot is identical except omission of
an empty upper-axis title object (both display no title). Existing empty-plot,
axis-range and HTTP integration tests pass. Browser reloaded updated CSS: computed
display/padding/margin/color/background/font/grid styles on 36 selected elements
were identical. Monitor and settings screenshots inspected; simulator running,
heater off, no recording. Browser process retains its already loaded Python code;
the updated plot helper was checked in the fresh test/figure processes.

E003 remains applicable to unchanged acquisition/CSV/reconnect code. Original
transcripts and simulation evidence are intentional records and retained. Scratch
downloads, recordings, caches and virtual environment remain ignored, not published.
Remote inspection (`git ls-remote --heads origin`) returned no branches; use the
existing main branch for the initial commit. Sandbox Git SSH mapping restriction
was resolved by the authorized read outside the sandbox.

Candidate hashes now normalize CRLF to LF, preventing core.autocrlf=true from
invalidating them on checkout. Digest method is explicit in candidate-manifest.json.
Reviewed candidate: `8d6349c231c8ac62431c035b6507c3c2bd55c676258b945addb94280638515f2`.
The earlier raw-byte manifest is superseded; prior E records retain their historical
candidate reference. Publication does not approve hardware access.
Final diff whitespace check identified trailing blank lines in seven text files;
trimmed only those blank lines and regenerated the candidate manifest.
Final staged diff inspected: 44 intentional files; no caches, scratch downloads,
virtual environment or browser recordings included. All 33 manifest file hashes
match both the worktree and Git index; candidate digest verified. `git diff --cached
--check` PASS. `uv --cache-dir tmp/uv-review-cache lock --check --offline` PASS
(33 packages); a workspace cache avoided the restricted user-cache ACL.

## E007 - Candidate committed and published (2026-09-20)
Created initial commit `c1794ea92c06845903356b5d003da24961913a8e` on existing branch
main after final staged-diff inspection. `git push -u origin main` succeeded;
`git ls-remote --heads origin main` returned the same hash at refs/heads/main.
Destination: git@github.com:cct1123/ti-hdc-sensor-monitor.git. No force push.
This checkpoint update is a separate documentation commit; the reviewed source/
configuration candidate remains `8d6349c231c8ac62431c035b6507c3c2bd55c676258b945addb94280638515f2`.
For publication recovery, compare local HEAD, origin/main and the remote main ref;
all must agree after the documentation commit is pushed. Physical validation remains
UNTESTED and requires the candidate-specific approval in STATE.md.

## E008 - Illustrated documentation and simulator walkthrough (2026-09-21)
H004: reviewed the referenced TMP README in the browser at revision
b8e1e4e7116943c826d3b59626059cd2b6d15923, matching the local reference checkout.
Reconciled the clean main/origin-main checkpoint at 2ac3139 and all 33 prior
candidate hashes before editing. Expanded README with simulator/USB quick starts,
record/download/export steps and screenshots; added docs/usage-guide.md for the
illustrated history/settings/CSV walkthrough and troubleshooting. Corrected the
documented Ruff invocation to include its dev extra. No runtime code changed.

TEST-007 PASS: outputs/documentation-checks.json records 29 valid relative links/
anchors, four verified JPEG images (413,707 bytes total), dimensions and SHA256s.
Screenshots are native browser captures of an isolated `app.py --simulate --port
8051` process: monitor-overview.jpg, history-held.jpg, csv-saved.jpg and
device-settings.jpg under docs/images/. No image synthesis or sensor-data editing.
All screenshots/captions explicitly identify simulation; no physical access occurred.

Observed monitoring and paired plots; Zoom in held both time axes, Follow live
restored following; Record/Stop recording saved 414 paired rows with zero drops
and enabled Download last CSV. Inspected that CSV: all rows simulated, on-demand
LPM0, heater off. Applied auto_1hz/LPM1 for the settings capture and confirmed the
Applied line. Simulator ended cleanly disconnected with 596 buffered pairs and
zero failed reads. No heater pulse was requested. CSV remains ignored scratch data.

Rendered README and guide locally through Dash Markdown: every screenshot loaded,
tables/steps rendered, and README had no horizontal overflow. Inspected the four
captures visually. Temporary preview tabs and the two session-created servers
(ports 8051/8052) were closed after disconnect; the user's reference tab was preserved.
`git diff --check` PASS. No unit rerun was needed for text/images: 32 previously
manifested files other than README remained identical, including all runtime code
and tests; E003/E006 evidence remains applicable.

Updated the manifest for README and the new text guide (34 files). Screenshot hashes
are in documentation-checks.json. Current candidate:
`999e943a3e7aba0db59543bfa003e268257e4ac5bd53f2f4f4ee493d0cc08760`.
H004 documentation changes remain local; no new commit or push performed.

## E009 - Supplied device photo in README (2026-09-21)
H005: copied the supplied PNG unchanged to docs/images/hdc3020evm.png and embedded
it below README's introduction with descriptive alt text and a device caption.
TEST-007 PASS: verified the 640 x 360 PNG, byte equality with the attachment, and
all 30 local README/guide links and anchors. Visually inspected the copied image.
Final `git diff --check` passed.
outputs/documentation-checks.json includes the photo's size and SHA256.
All 33 other candidate text files remain unchanged; no runtime tests were needed.
Updated README's manifest hash and candidate digest:
`77b87f755903242c74b0a347b5f6ea38ef05497d56855a5f87c5129a5ce557f9`.
No physical interaction or publication performed; prior simulator evidence applies.

## E010 - Documentation pruning and publication review (2026-09-21)
H006: retained all five referenced images and the illustrated guide. Removed
repeated CSV/control details from README; the guide retains the full instructions.
Corrected wording that could imply the hardware procedure was already approved.
Removed the five ignored, session-created preview helper/log files under tmp/readme;
their servers were already stopped. Preserved runtime code and historical evidence.

TEST-007 PASS: rechecked 29 local links/anchors, balanced code fences, five image
formats/dimensions/hashes and no unused image assets. Refreshed documentation-checks.json
and the 34-file candidate manifest; all 32 pre-existing candidate files other than
README match published HEAD. Candidate:
`511516293b1c4a4faf00c66b5c31351634c0c3d64b1273422b0b926211c36007`.
`ruff check app.py hdcsensor tests` PASS; `ruff format --check app.py hdcsensor tests`
PASS (22 files); `git diff --check` PASS. Existing 36-test and simulation results
remain applicable because runtime code/configuration/tests did not change.
Publication target: origin/main, normal push only; no physical access authorized.

## E011 - Documentation published (2026-09-21)
Reviewed the staged diff and committed all intended documentation/assets as
`586f9c5680bd9b1ce145198eed5fac4f7522830c` (13 files). Normal push to origin/main
succeeded. At 16:08 America/Chicago, HEAD, origin/main and `git ls-remote origin
refs/heads/main` all matched that commit; the worktree was clean.
This following checkpoint records the verified result and releases state ownership.
Publish it under H006 with a normal push; verify its own revision through Git refs.
Candidate digest remains `511516293b1c4a4faf00c66b5c31351634c0c3d64b1273422b0b926211c36007`.
Hardware review remains pending; no physical interaction occurred.

## E012 - First physical TEST-005 attempt and fault isolation (2026-09-23)
Under H007, confirmed the 34-file reviewed candidate digest
`511516293b1c4a4faf00c66b5c31351634c0c3d64b1273422b0b926211c36007`
and Python 3.12.14 / hidapi 0.15.0 / Dash 3.4.0 / Plotly 7.1.0. One matching
HID bridge enumerated: VID:PID 2047:0301, Texas Instruments USB2ANY/OneDemo,
USB serial `88F2A26E25000200`, release 0x0200. TEST-005 command:
`.venv/Scripts/python.exe -m hdcsensor.validate --hardware --samples 30 --interval 1
--output outputs/hardware-validation`. It exited 1 in 0.4 s. Report:
outputs/hardware-validation/validation_20260923_200536_567859.json; CSV has only
its header. The bridge accepted open/firmware/I2C configuration, then returned
error -54 on the first raw I2C command write (manufacturer ID); no sensor identity
or sample was read. The session closed the HID handle after open failed.
TEST-005 FAIL for this candidate; REQ-001/002 remain unverified on hardware.

TI's [USB2ANY API specification](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/14/api_5F00_reference_5F00_for_5F00_usb2any_5F00_sdk_5F00_2.7.0.pdf)
identifies -54 as ERR_I2C_NO_PULLUP_POWER: bridge-managed I2C pullups require
its 3.3V EXT output. The [EVM schematic](https://www.ti.com/lit/pdf/snau267)
shows four 10 kΩ I2C pullups to the USB-powered 3P3V rail, and the guide says
the sensor and MSP430 are supplied from USB through on-board regulation.
Thus bridge pullups need not be enabled for this stock EVM. This diagnosis is
specific to the observed error and documented board; no firmware/power command
or wiring change was attempted. A single pullup-disabled software correction
and identity check is the next discriminating test.

## D003 - Stock EVM I2C pullup selection
Configure the USB2ANY I2C interface at 100 kHz, 7-bit addressing, with its
internal pullups disabled. Keep the board's documented passive pullups and USB
power; avoid a bridge 3.3V EXT output command. Recheck all transport tests and
physical identity before resuming timed acquisition. If this produces an I2C
NAK or other distinct fault, stop and reassess the actual board connection.

## E013 - Pullup correction software regression (2026-09-23)
Changed USB2ANY I2C control payload from `00 00 01` to `00 00 00`
(100 kHz, 7-bit, bridge pullups off); mapped -54 to a useful error and aligned
the protocol and hardware-validation documents. The HID fake now asserts this
payload and the -54 diagnostic. TEST-001–004: all 36 tests PASS in 2.776 s;
transcript outputs/hardware-fix-unit-tests.txt. The first sandboxed full-suite
attempt failed only due the known Windows temporary-directory ACL issue; the
identical suite passed outside that sandbox. Ruff check PASS; formatting was
applied to hdcsensor/usb_hid.py. No physical retry yet. TEST-005 remains FAIL
until a new physical result is collected.

## E014 - Physical identity diagnostic (2026-09-23)
Ran one bounded HDC3020Sensor open/status/close on the connected EVM with
bridge-managed I2C pullups off; transcript:
outputs/hardware-validation/identity-diagnostic.txt. PASS: USB2ANY firmware
2.8.2.0, TI manufacturer 0x3000 with valid CRC, NIST ID `1A73E0120F3E` (three
CRC-checked words), stock address 0x44, status 0x8010 (heater bit 13 clear),
and orderly close. The -54 error did not recur. This establishes physical
USB/I2C identity and volatile initialization, not paired acquisition or CSV.

## E015 - Physical acquisition, CSV and reconnect (2026-09-23)
TEST-005 PASS after D003 correction: `.venv/Scripts/python.exe -m
hdcsensor.validate --hardware --samples 30 --interval 1 --output
outputs/hardware-validation` exited 0. Report:
outputs/hardware-validation/validation_20260923_200902_021356.json; paired CSV
next to it. Thirty CRC-checked pairs, no failed reads or dropped rows, CSV
values/timestamps equal the buffer, median interval 1.000613 s (range
0.978251–1.020820 s), clean close and reopen with unchanged NIST ID, and clean
final close. Temperature ranged approximately 23.14–23.19 °C in inspected
rows, RH 46.83–46.98 %RH; plausibility only, no accuracy/calibration claim.
Identity was the same as E014; heater remained off. The earlier failed attempt
remains preserved as E012. REQ-001 and REQ-002 pass their core physical method;
dashboard interaction and advanced controls still require physical checks.

## E016 - Non-heater controller procedure prepared (2026-09-23)
Added `hdcsensor.validate_controls` as a bounded TEST-006 runner using only the
DeviceSession worker. It checks status/identity, clear of the reset-detected bit,
one valid pair at each on-demand LPM0–3, valid auto 1 Hz and 0.5 Hz pairs at
each LPM0–3, three-sample auto cadence at LPM0, soft-reset defaults and a
post-reset pair, then clean disconnect. It never requests heater-on, EEPROM,
firmware, power-output, or general-call operations. Ruff check and format PASS.
Simulator rehearsal PASS in 19.0 s:
outputs/simulation-validation/controls_20260923_201128_701411.json. Physical
TEST-006 remains untested until the runner is executed on the EVM.

## E017 - Physical non-heater controller validation (2026-09-23)
TEST-006 non-heater subset PASS: `.venv/Scripts/python.exe -m
hdcsensor.validate_controls --hardware --output outputs/hardware-validation`
exited 0. Report: outputs/hardware-validation/controls_20260923_201208_417991.json.
The USB/NIST identity matched E014/E015; initial status 0x8010 cleared to
0x0000, then soft reset restored 0x8010 and on-demand LPM0 with heater off.
All 12 mode/LPM combinations returned valid CRC-checked paired measurements.
Auto 1 Hz LPM0 median interval 1.0172985 s; auto 0.5 Hz LPM0 median
2.0151055 s. Post-reset pair and clearing the reset flag passed. Zero read
failures, clean disconnect, no heater-on or persistent operations. No readable
mode register exists; mode/LPM evidence is acknowledged commands plus subsequent
valid pairs and metadata/cadence. Heater-specific TEST-006 remains untested
pending separate user scope.

## E018 - Dashboard integration procedure prepared (2026-09-23)
Added `hdcsensor.validate_dashboard`, which calls the application's actual
Dash HTTP routes/callbacks while its single DeviceSession owns the backend.
It checks live paired values, synchronized plot traces, recorded CSV, buffer
export and saved-file download, settings, pause and UI disconnect. The runner
has no heater-on action. Simulator rehearsal PASS with three samples and clean
disconnect: outputs/simulation-validation/dashboard_20260923_201353_219373.json.
Ruff check/format PASS for 24 Python files. Physical dashboard integration
remains untested until this procedure runs with `--hardware`.

## E019 - Physical dashboard integration (2026-09-23)
The prepared `hdcsensor.validate_dashboard --hardware --output
outputs/hardware-validation` exited 0; report:
outputs/hardware-validation/dashboard_20260923_201425_005010.json. Actual Dash
HTTP routes and callbacks connected to the same EVM identity as E014/E015,
displayed temperature/RH, produced two plots with aligned timestamps, recorded
three real paired rows, drained the CSV without drops, exported the current
buffer, and returned a download byte-for-byte equivalent to the saved CSV.
Auto 1 Hz/LPM1 settings applied through the UI callback, the settings page
activated, and UI disconnect closed the device cleanly with heater off. Saved
CSV: outputs/hardware-validation/hdc3020_20260923_201425_201775.csv.
This is HTTP callback integration with real hardware; visual browser rendering
was previously checked with simulation (E004/E008), not separately on hardware.

## E020 - Heater validation procedure rehearsed without hardware (2026-09-23)
Prepared `hdcsensor.validate_heater` for a single five-second minimum-element
pulse, requiring both `--hardware` and `--confirm-attended` for physical use.
It records a baseline pair, status-on and heater-marked samples, verifies the
host timer turns heater off while sampling is paused, then collects ten cooldown
pairs, CSV flags, plot markers and clean shutdown. It reports actual baseline,
peak and final temperature/RH without presuming a quantitative thermal effect.
Simulator rehearsal PASS in 15.4 s:
outputs/simulation-validation/heater_20260923_202022_661038.json. Ruff check and
format PASS. No physical heater-on action was performed; the separate H007
scope request remains pending.

## E021 - Final local evidence review (2026-09-23)
Updated PROJECT.md/README/protocol/procedure and outputs/REPORT.md to distinguish
the completed physical scope from heater-on and independent accuracy limits.
Created outputs/validation-manifest.json with 37 source/configuration files;
CRLF-normalized digest
`0f30ce5eae7ba58b663f7a32846522598af4831c1b113cf9723b9e91ce9b39e7`
matches the current files. The original H007 review-gate candidate manifest
remains unchanged. Rechecked relative document links, the three passing physical
JSON reports, 30 exact heater-off CSV rows, and the passing simulated heater
report. Ruff check and format PASS for 25 Python files; `git diff --check` PASS.
No source change followed the physical acquisition/control/dashboard runs except
new standalone validation runners and documentation; their simulator rehearsals
and the physical controls/dashboard runs provide relevant integration checks.
The physical heater test remains UNTESTED pending explicit attended-pulse scope.

## E022 - Blocked handoff at heater-scope boundary (2026-09-23)
After E021, no useful hardware-independent validation remains. The user has
approved H007's connected-board acquisition and non-heater controls; that scope
passed (E015/E017/E019). The separately required heater-on authorization has
been requested asynchronously but no answer was available by 15:22
America/Chicago. No heater-on command was issued. Checkpoint as BLOCKED,
resuming HARDWARE_VALIDATION only after an explicit yes with attended/no
heat-sensitive-setup confirmation, or a no that leaves REQ-005 physically
unvalidated. Preserve the prepared simulator-tested procedure (E020) and all
physical reports; re-identify the board and verify its state before any next
physical action. Current changes are local and uncommitted, with no Git
publication operation in flight.

## E023 - First-use guide completed (2026-09-23)
Under H008, added docs/quick-start.md with the working local PowerShell
command, USB/backend/address/interval selection, live-reading checks, CSV
record/download/export steps, Stop/Disconnect/Ctrl+C, and simulator fallback.
The image is labeled as simulation. Updated README.md and docs/usage-guide.md
to link the short guide and to reflect the completed physical core validation
while retaining the untested heater boundary. Confirmed the `.venv` Python
path exists, all new relative Markdown links resolve, and `git diff --check`
passes. Regenerated outputs/validation-manifest.json: 38 files, SHA256
`90dd49be644832364d2d6ec29aee1ac70a78df188b53bdd8b7a298a99049d9c5`.
No runtime code or hardware was touched under H008; E015/E017/E019 remain
applicable. The physical heater scope remains unanswered.

## E024 - Bash/uv guide simplification (2026-09-23)
Under H009, changed the quick start to one Bash `uv run --extra usb python
app.py` launch command and five UI steps. Removed its workspace-specific
PowerShell/.venv path. Pruned repeated setup steps from README and the
illustrated guide, removed the alternative pip/venv installation section, and
made the hardware-validation procedure's commands consistently use uv.
Official uv project documentation confirms `uv run` automatically locks/syncs
the environment and `--extra usb` includes optional dependencies:
https://docs.astral.sh/uv/concepts/projects/sync/ . Checked Markdown links,
balanced fences, no PowerShell/.venv text in the quick start, and
`git diff --check` PASS. Regenerated the 38-file normalized manifest:
`9111c1713dbe667c652141ecd7226ca79967314220731685a2819c27d7b2620a`.
No runtime code or hardware interaction occurred under H009; prior physical
results E015/E017/E019 remain applicable. Heater scope remains pending.

## E025 - H010 prepublication review (2026-09-23)
Reviewed the pending transport fix, fake HID assertion, three bounded validation
runners, report, Bash/uv quick start and evidence set. All pending artifacts are
intentional: the initial failed physical JSON/header-only CSV document E012;
the later physical JSON/CSV, identity transcript and simulation rehearsals
support E014–E020. No unrelated file or secret was found in the pending set.
The corrected physical acquisition report has 30 CSV rows, dashboard 3 rows,
non-heater controls 22 passing checks; the initial attempt remains FAIL as
recorded. The three subsequent physical reports and four simulation reports
are PASS with no errors. Software-only TEST-001–004 rerun: 36/36 PASS in
2.730 s (outputs/hardware-fix-unit-tests.txt); Ruff check and format PASS for
25 Python files; `git diff --check` PASS. The normalized 38-file validation
manifest matches digest
`9111c1713dbe667c652141ecd7226ca79967314220731685a2819c27d7b2620a`;
relative links in six documents resolve. No device command was issued under
H010. Before publication, origin/main was independently checked at
`6514201add0143c38b05099108b1a9a91a1ed516`. Heater-on remains UNTESTED.
