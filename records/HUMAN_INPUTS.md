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
