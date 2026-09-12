# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release

## [1.0.3] - 2025-09-12

### Fixed
- **Linux tkinter dependency removed** — Replaced tkinter file dialog with Textual's native `DirectoryTree` widget for cross-platform file selection without system dependencies
- **GitHub Actions release permissions** — Added `permissions: contents: write` to workflow for automated release creation

### Changed
- File picker now uses directory tree browser with keyboard navigation
- Removed `tkinter` from PyInstaller hidden imports

## [1.0.2] - 2025-09-12

### Fixed
- **PowerShell compatibility** — Fixed verify step using `Get-ChildItem` instead of `ls` for Windows CI

## [1.0.1] - 2025-09-12

### Fixed
- **Build verification** — Added executable existence check in CI pipeline

## [1.0.0] - 2025-09-12

### Added
- **Core merge engine** — Worker matching by composite key (No, CURP, NSS) with fuzzy fallback
- **Diff algorithm** — Field-level comparison for 14 checklist fields + 9 data fields
- **Auto-merge** — Safe automatic merging of X-mark additions only
- **Conflict resolution** — Interactive one-by-one review with Keep Base / Use Updated / Manual Edit
- **Statistics dashboard** — Real-time counts of all change types
- **TUI Application** — Textual-based terminal interface with:
  - DirectoryTree file picker (cross-platform)
  - Statistics dashboard with action buttons
  - Conflict navigator with keyboard shortcuts
  - Manual field editor for complex conflicts
- **Excel I/O** — openpyxl-based read/write preserving:
  - Formatting (fonts, colors, borders, alignment)
  - Formulas (VLOOKUP, etc.)
  - Column widths and sheet structure
- **Output naming** — Timestamped merged files: `{basename}_Merged_YYYYMMDD_HHMMSS.xlsx`
- **PyInstaller packaging** — Single portable executable (~51MB)
- **GitHub Actions CI/CD** — Automated Windows builds on tag push
- **Documentation** — README, Architecture, Usage, Development guides

### Technical Details
- **Worker matching**: Composite key + rapidfuzz (85% threshold)
- **Conflict detection**: X added/removed, data changed, worker added/removed
- **Auto-merge criteria**: Only X additions, no removals, no data changes, worker exists in both
- **Formatting preservation**: Style copying from template row
- **Dependencies**: openpyxl, textual, rich, rapidfuzz, python-dateutil