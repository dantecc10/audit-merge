# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-09-14

### Added
- **Native desktop GUI (PySide6)** — replaces the TUI: `run_gui.py` / `audit-merge`
  - File selection, statistics dashboard, interactive conflict review, save
  - Merge runs in a background `QThread` with progress reporting
- **Columnas nuevas** — extra columns in base and incremental documents are detected and merged into the output
- **Compartido usuario/`build_merged_workers`** — GUI and web export final workers through the same builder
- **Tests** — 22 unit tests covering column detection, the wrong-column bug, extra fields, and merge logic

### Fixed
- **Valores en columnas equivocadas** — `_normalize_header()` (minusculas, acentos, puntuación) y matching por alias estricto en `detect_column_mapping`; el fallback a columnas libres ya no pisa columnas reales
- **Colisión de filas** — los trabajadores nuevos (solo en el actualizado) se anexan a filas libres; los de base conservan su fila original
- **Sobrescritura de trabajadores en export** — la unión base+actualizado+resoluciones ya no puede sobrescribir filas ajenas

### Changed
- TUI removed (`src/audit_merge/tui/`, `run_app.py`)
- Web moved to `src/audit_merge/web/` (imports `audit_merge.*`)
- `pyproject.toml`: PySide6 replaces `textual`/`rich`; version 2.0.0
- `audit-merge.spec`: PySide6 hidden imports, `console=False`
- **Releases Linux**: workflow renombrado a `build.yml` con job `build-linux` (AppImage + binario ELF) y job `release` que publica ambos; el `.exe` de Windows ya no se sube por separado (lo unifica el job `release`)

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