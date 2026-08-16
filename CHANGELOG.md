# Changelog

All notable changes to this project are documented here.

## [1.1.0] - 2026-08-14

### Added
- NVMe support in `lib/smart_parser.py` — previously NVMe disks (e.g. zblade's `eider`) silently returned zero SMART attributes because only the SATA numbered-attribute-table format was parsed. NVMe's named `SMART/Health Information` block (Critical Warning, Available Spare, Percentage Used, Media and Data Integrity Errors) is now parsed and analyzed via a dedicated `analyze_nvme_disk()` rule set.
- `--json` / `--json-out FILE` flags — structured snapshot output, bypassing the rendering path. Explicitly a spot-check tool, not a history/monitoring mechanism (see `docs/03-design-decisions.md`).
- Optional `rich` dependency — falls back to a plain-text renderer reproducing the same report structure (headers, per-issue blocks, summary table) without color, so the tool runs on hosts without guaranteed `pip` access.

### Changed
- Project restructured from two flat sibling folders (`disk-health-checker/`, `disk-temp-monitor/`) into `bin/`, `lib/`, `etc/`, `docs/`, `examples/`, `analysis/` — shared parsing logic extracted to `lib/smart_parser.py` instead of duplicated between the health checker and the temp monitor's SMART reads.
- `analyze-temp.py` (requires `pandas` + `rich`) moved to `analysis/` and marked optional/deferred — not part of the default install path.
- `disks.conf` moved to `etc/disks.conf.template`; real host-specific config is gitignored, not committed.
- `temperature_log.csv` untracked from git (`git rm --cached`) — generated data, not source. Full history purge deferred as a separate action item (git history rewrites are irreversible, done once the project structure is otherwise stable — same principle already applied to `docs-versioning`'s `restic-repo.key` scrub).

### Fixed
- Broken cross-reference in `docs/01-problem-definition.md` pointing to a nonexistent `02-ai-collaboration-process.md` — corrected to the actual `02-prompt-engineering.md`, including the specific section anchor (was pointing at "Phase 5," actually "Phase 7: Real-World Bug Discovery").
- `bin/monitor-temp.sh` resolving `disks.conf` and the log file as paths relative to the current working directory rather than the script's own location — broke once the script moved into `bin/` while its config moved into `etc/`.

## [1.0.0-alpha] - 2026-02-10

### Added
- Initial release: SATA/SAS SMART attribute analysis with 10 monitored attributes, context-aware rules (HDD/SSD-specific), severity classification (HEALTHY/WARNING/CRITICAL), exit codes (0/1/2) for automation.
- `monitor-temp.sh` + `analyze-temp.py` temperature logging and trend visualization, migrated from hardcoded disk paths to `disks.conf`-driven configuration (see `docs/05-temp-monitor-migration.md`).
- Manufacturer-specific handling for Seagate `Raw_Read_Error_Rate` (threshold-relative headroom check instead of a hardcoded cutoff) after a real production false positive — see `docs/02-prompt-engineering.md`, Phase 7.