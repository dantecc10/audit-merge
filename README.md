# Audit Merge Tool

A portable TUI (Text-based User Interface) tool for merging audit spreadsheet changes in payroll verification workflows.

## Features

- **Compare Excel files**: Select a base template and an updated worker file
- **Auto-merge**: Automatically applies safe changes (X-mark additions only)
- **Conflict resolution**: Interactive one-by-one review of removals, data changes, new/removed workers
- **Statistics dashboard**: Real-time counts of all change types
- **Timestamped output**: Generates `{basename}_Merged_YYYYMMDD_HHMMSS.xlsx`
- **Portable**: Single executable for Windows (`.exe`) and Linux
- **No external dependencies**: Uses Textual's native DirectoryTree for file selection

## Quick Start

### Windows
1. Download `audit-merge.exe` from [Releases](https://github.com/dantecc10/audit-merge/releases)
2. Run `audit-merge.exe`

### Linux
```bash
# From source
git clone https://github.com/dantecc10/audit-merge
cd audit-merge
pip install -e .
python run_app.py

# Or build your own executable
pip install pyinstaller
pyinstaller audit-merge.spec --clean
./dist/audit-merge
```

## Usage Workflow

```
┌─ Audit Merge Tool ────────────────────────────────────┐
│  1. Select BASE file (template/master)                │
│  2. Select UPDATED file (worker's version)            │
│  3. View Statistics Dashboard                         │
│     ✓ Auto-mergeable: 723  (only X's added)           │
│     ⚠ Conflicts to review: 124                        │
│        - X's removed: 45                              │
│        - Data changed: 32                             │
│        - Workers added: 35                            │
│        - Workers removed: 12                          │
│  4. [A] Apply auto-merges                             │
│  5. [R] Review conflicts one-by-one                   │
│     [K] Keep base  [U] Use updated  [M] Manual edit   │
│  6. [S] Save merged output                            │
└────────────────────────────────────────────────────────┘
```

## File Format

Works with Excel files (`.xlsx`, `.xls`) containing a "Revisión Exp" sheet with:
- Worker data: No, Nombre, CURP, NSS, Depto, Puesto, Salario, dates
- Document checklist columns (X marks): Solicitud empleo, Acta nacimiento, INE, etc.
- Auxiliary fields: Fecha solicitud, Firma, Curriculum, etc.

## Matching Strategy

Workers are matched by composite key: `(No, CURP, NSS)` with fuzzy name fallback (85% threshold).

## Output

Merged file preserves:
- Original formatting, styles, column widths
- Formulas (e.g., VLOOKUP in Salario column)
- All sheets from the base workbook

## Requirements

- Python 3.11+
- Dependencies: `openpyxl`, `textual`, `rich`, `rapidfuzz`, `python-dateutil`

## Building from Source

```bash
pip install -e .
pip install pyinstaller
pyinstaller audit-merge.spec --clean
# Output: dist/audit-merge (Linux) or dist/audit-merge.exe (Windows)
```

## License

MIT License