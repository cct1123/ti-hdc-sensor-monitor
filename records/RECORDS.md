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
