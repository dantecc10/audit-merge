# Technical Architecture

## Overview

Audit Merge is a Python-based TUI application for comparing and merging Excel spreadsheet changes in payroll audit workflows. Built with Textual for the terminal UI and openpyxl for Excel processing.

## Project Structure

```
src/audit_merge/
├── __init__.py              # Package entry point
├── models/__init__.py       # Data models (Worker, DocumentChecklist, WorkerDiff, MergeStats)
├── excel/
│   └── io.py               # Excel read/write with formatting preservation
├── diff/
│   └── merge.py            # Diff algorithm, worker matching, merge logic
└── tui/
    └── app.py              # Textual TUI application
```

## Data Models

### Worker
Represents a single worker row from the "Revisión Exp" sheet.

```python
@dataclass
class Worker:
    no: Optional[int]           # Employee number (primary key part 1)
    nombre: str                 # Full name
    curp: str                   # CURP (primary key part 2)
    nss: str                    # NSS/IMSS (primary key part 3)
    depto: str                  # Department
    puesto: str                 # Position
    salario: str                # Salary (often VLOOKUP formula)
    fecha_reingreso: str        # Rehire date
    fecha_baja: str             # Termination date
    fecha_baja_2: str           # Additional termination date
    fecha_baja_3: str           # Additional termination date
    checklist: DocumentChecklist
    row_index: int              # Original Excel row for write-back
```

**Matching Key**: `(no, curp.upper(), nss)` — composite for robustness against single-field changes.

### DocumentChecklist
14 checklist fields (X-mark columns) + 9 data fields (date/text columns).

```python
CHECKLIST_FIELDS = [
    "solicitud_empleo", "acta_nacimiento", "ine", "c_domicilio", "c_estudios",
    "constancia_situacion_fiscal", "numero_imss", "curp_checklist", "cta_banco",
    "examen_medico", "validacion_fechas", "contrato", "designacion_beneficiarios",
    "constancias_laborales"
]

DATA_FIELDS = [
    "fecha_solicitud", "firma", "curriculum_vitae",
    "infonavit", "alta_imss", "contrato_asignado", "no_caja", "finiquito"
]
```

### WorkerDiff
Captures all differences between base and updated worker.

```python
@dataclass
class WorkerDiff:
    worker_key: tuple
    base_worker: Optional[Worker]
    updated_worker: Optional[Worker]
    field_diffs: list[FieldDiff]      # All field-level changes
    checklist_added: list[str]        # X added in updated
    checklist_removed: list[str]      # X removed in updated
    data_changed: list[str]           # Non-checklist fields changed
    
    @property
    def has_conflicts(self) -> bool:
        """True if any X removed, data changed, or worker added/removed"""
    
    @property
    def is_auto_mergeable(self) -> bool:
        """True if only X added (no removals, no data changes, both exist)"""
```

### MergeStats
Aggregate statistics for the dashboard.

```python
@dataclass
class MergeStats:
    total_base: int
    total_updated: int
    auto_mergeable: int
    conflicts: int
    checklist_added_total: int
    checklist_removed_total: int
    data_changed_total: int
    workers_added: int
    workers_removed: int
```

## Diff Algorithm

### Worker Matching (`match_workers`)
1. Build dicts keyed by `(no, curp, nss)` for both base and updated
2. For each key in union:
   - Both present → direct match
   - Only in base → worker removed
   - Only in updated → try fuzzy match on name (85% threshold + CURP/NSS bonus)
   - No fuzzy match → new worker

### Field Diffing (`diff_workers`)
For matched workers:
1. Compare all data fields (nombre, curp, nss, depto, puesto, salario, dates)
2. Compare checklist fields: detect X added/removed
3. Compare data fields: detect value changes
4. Build `FieldDiff` list with `ChangeType` (ADDED/REMOVED/MODIFIED)

### Auto-Merge (`apply_auto_merge`)
Only applies when `is_auto_mergeable == True`:
- Checklist: union of X marks (base ∪ updated)
- Data fields: prefer updated if non-empty, else base

### Conflict Resolution (`apply_conflict_resolution`)
User choices per conflict:
- **Keep Base**: Use base worker entirely
- **Use Updated**: Use updated worker entirely  
- **Manual Edit**: Field-by-field selection via input form

## Excel I/O

### Reading (`read_workers_from_sheet`)
- Detects header row (row 3) dynamically
- Reads from row 4 to max_row
- Parses all 33 mapped columns
- Preserves formulas as strings
- Normalizes dates to DD/MM/YYYY strings

### Writing (`write_workers_to_sheet`)
- Uses template row (row 4) for style copying
- Copies font, fill, border, alignment, number_format, protection
- Writes merged workers in sorted order (by No, then nombre)
- Maintains original column structure

### Formatting Preservation
```python
def copy_cell_style(source: Cell, target: Cell):
    target.font = copy.copy(source.font)
    target.fill = copy.copy(source.fill)
    target.border = copy.copy(source.border)
    target.alignment = copy.copy(source.alignment)
    target.number_format = source.number_format
    target.protection = copy.copy(source.protection)
```

## TUI Architecture

### Screens
1. **FilePickerScreen** (×2) — DirectoryTree-based file selection
2. **StatsScreen** — Dashboard with counts and action buttons
3. **ConflictReviewScreen** — One-by-one conflict navigator
4. **ManualEditScreen** — Field-by-field editor for complex conflicts

### Navigation Flow
```
FilePicker(base) → FilePicker(updated) → StatsScreen
    ↓                                           ↓
    ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
    ↓                                           ↓
ConflictReviewScreen (per conflict) → ManualEditScreen (optional)
    ↓
StatsScreen (updated stats) → Save → Output file
```

### Key Bindings
| Screen | Keys |
|--------|------|
| FilePicker | ↑/↓ navigate, Enter select, Esc cancel |
| Stats | A=auto-merge, R=review, S=save, Esc=back |
| ConflictReview | N/P=next/prev, K=keep base, U=use updated, M=manual, Esc=done |
| ManualEdit | Enter save, Esc cancel |

## Output Naming

```
{basename}_Merged_{YYYYMMDD_HHMMSS}.xlsx
Example: Expedientes-Plantilla_Jaes_2025_Merged_20250912_143022.xlsx
```

## Build & Distribution

### PyInstaller Spec
- Single file executable (`onefile=True`)
- Console mode (`console=True`)
- Hidden imports for all Textual widgets
- UPX compression enabled
- Custom icon (Windows/macOS)

### CI/CD
GitHub Actions workflow:
- Triggers on `v*` tags
- Builds on `windows-latest`
- Uploads artifact + creates GitHub Release

## Performance

| Metric | Value |
|--------|-------|
| Workers processed | ~860 |
| Diff time | <500ms |
| Memory | ~50MB |
| Executable size | ~51MB |

## Future Improvements

- Multi-file batch merge (queue multiple updated files)
- Export conflict report (CSV/PDF)
- Undo/redo in conflict review
- Keyboard shortcuts for common actions
- Dark/light theme toggle