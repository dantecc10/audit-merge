# Technical Architecture

## Overview

Audit Merge is a Python application for comparing and merging Excel spreadsheet changes in payroll audit workflows. Available as a **native desktop GUI (PySide6)** for offline use and as a **web application (Flask)** for networked use. Both frontends share the same core: `models`, `excel`, and `diff`.

## Project Structure

```
src/audit_merge/
├── __init__.py              # Package entry point
├── models/__init__.py       # Data models (Worker, DocumentChecklist, WorkerDiff, MergeStats)
├── excel/
│   ├── __init__.py
│   └── io.py               # Excel read/write with formatting preservation
├── diff/
│   ├── __init__.py
│   └── merge.py            # Diff algorithm, worker matching, merge logic
├── gui/
│   ├── __init__.py
│   └── app.py              # PySide6 desktop GUI
└── web/
    ├── __init__.py
    ├── app.py              # Flask web application
    ├── static/
    └── templates/
```

Entry points: `run_gui.py` (desktop) and `run_web.py` (web, port 5001).

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

## UI Architecture

Both interfaces expose the same workflow: select files → statistics → review conflicts → save.

### Desktop GUI (`gui/app.py`)
Native PySide6/Qt application:
1. **MainWindow** hosts a `QStackedWidget` with four screens.
2. **MergeWorker** (`QThread`) runs the diff pipeline off the UI thread and reports progress via signals.
3. **FileSelectionScreen** — pick base and updated `.xlsx` files.
4. **StatsScreen** — dashboard with live counts and action buttons (Apply Auto-Merge, Review Conflicts, Save).
5. **ConflictReviewScreen** — one-by-one conflict navigation with Keep Base / Use Updated / Manual Edit.

### Web (`web/app.py`)
Flask application with server-side session state:
- Routes: upload base/updated, process, auto-merge (POST), conflict resolution (POST), export/save.
- Templates: `index.html`, `conflicts.html`, base layout in `templates/base.html`.
- State stored per browser session; files kept in an `uploads/` folder.
- `export_merged` serializes and runs the same merge pipeline as the GUI, reusing `build_merged_workers`.

### Shared Merge Builder (`build_merged_workers`)
Both the GUI save handler and the web `export_merged` finalize the merged result through the same function in `diff/merge.py`:
- Unions base + updated workers (base-only workers are kept).
- Applies auto-merged workers and manual resolutions.
- Base workers keep their original rows; brand-new workers are appended to the first free rows, preventing row collisions that could overwrite existing workers.

## Output Naming

```
{basename}_Merged_{YYYYMMDD_HHMMSS}.xlsx
Example: Expedientes-Plantilla_Jaes_2025_Merged_20250912_143022.xlsx
```

## Build & Distribution

### PyInstaller Spec
- Single file executable (`onefile=True`)
- Windowed mode (`console=False`)
- Hidden imports for PySide6, openpyxl, rapidfuzz, dateutil
- Custom icon (Windows/macOS)

### CI/CD
GitHub Actions workflow (`build.yml`):
- Triggers on `v*` tags (y `workflow_dispatch`)
- `build-windows`: PyInstaller en `windows-latest` → `audit-merge-windows-<v>.exe`
- `build-linux`: PyInstaller en `ubuntu-22.04` (glibc 2.35) + `appimagetool` → `audit-merge-<v>-x86_64.AppImage` y binario ELF
- `release`: job separado que descarga ambos artifacts y crea la GitHub Release (evita carreras). GitHub además genera los `.zip`/`.tar.gz` de source automáticamente.

## Performance

| Metric | Value |
|--------|-------|
| Workers processed | ~860 |
| Diff time | <500ms |
| Memory | ~50MB |
| Executable size (onefile) | ~72MB (ELF) / ~72MB (AppImage) |

## Future Improvements

- Multi-file batch merge (queue multiple updated files)
- Export conflict report (CSV/PDF)
- Undo/redo in conflict review
- Keyboard shortcuts for common actions
- Dark/light theme toggle