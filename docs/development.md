# Development Guide

## Environment Setup

### Prerequisites
- Python 3.11+
- Git
- (Windows) Visual Studio Build Tools for PyInstaller

### Install Dependencies
```bash
git clone https://github.com/dantecc10/audit-merge
cd audit-merge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e .[dev]
```

### Dependencies
| Package | Purpose | Version |
|---------|---------|---------|
| `openpyxl` | Excel read/write | ≥3.1.2 |
| `PySide6` | Desktop GUI framework | ≥6.6.0 |
| `rapidfuzz` | Fuzzy string matching | ≥3.9.0 |
| `python-dateutil` | Date parsing | ≥2.8.2 |
| `flask` | Web frontend (extra `web`) | ≥3.0.0 |
| `python-dotenv` | Web env config (extra `web`) | ≥1.0.0 |
| `pyinstaller` | Executable building (extra `build`) | ≥6.5.0 |

## Running the Application

### GUI (desktop, offline)
```bash
python run_gui.py
```

### Web
```bash
pip install -e ".[web]"
python run_web.py
# http://localhost:5001
```

### Run Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Format
black src/

# Lint
ruff check src/

# Type check (if mypy configured)
mypy src/
```

## Project Structure

```
audit-merge/
├── .github/
│   └── workflows/
│       └── build.yml             # CI/CD: Windows exe + Linux AppImage + release
├── assets/
│   └── icon.ico                 # Application icon
├── docs/
│   ├── architecture.md          # Technical design
│   └── usage.md                 # User guide
├── src/
│   └── audit_merge/
│       ├── __init__.py          # Package exports
│       ├── models/__init__.py   # Data models
│       ├── excel/
│       │   └── io.py           # Excel I/O with formatting
│       ├── diff/
│       │   └── merge.py        # Diff & merge algorithms
│       ├── gui/
│       │   └── app.py          # PySide6 desktop GUI
│       └── web/
│           ├── app.py          # Flask web application
│           ├── static/
│           └── templates/
├── audit-merge.spec             # PyInstaller configuration
├── pyproject.toml               # Project metadata & build config
├── run_gui.py                   # Desktop entry point
├── run_web.py                   # Web entry point
├── README.md
├── CHANGELOG.md
└── .gitignore
```

## Key Development Workflows

### Adding a New Checklist Field
1. Add field to `DocumentChecklist` in `models/__init__.py`
2. Add to `CHECKLIST_FIELDS` or `DATA_FIELDS` list
3. Add column mapping in `excel/io.py` (`COLUMN_MAP`, `CHECKLIST_COLUMNS`)
4. Rebuild: `pyinstaller audit-merge.spec --clean`

### Modifying Matching Logic
Edit `diff/merge.py`:
- `_find_fuzzy_match()` — adjust threshold, add fields
- `match_workers()` — change key composition
- `build_merged_workers()` — final row assignment for export (base rows preserved, new workers appended to free rows)

### Adding GUI Screens
1. Create a new `QWidget` subclass in `gui/app.py`
2. Add it to the `QStackedWidget` in `MainWindow`
3. Wire navigation with `self.stack.setCurrentIndex(n)`
4. Mirror the route/action in the web templates if needed

### Adding Web Routes
1. Define the route in `web/app.py`
2. Add/extend the template in `web/templates/`
3. Reuse core functions from `diff/merge.py` and `excel/io.py`; keep serialization helpers (`_serialize_worker`/`_deserialize_worker`) in sync
4. Ensure `export_merged` uses `build_merged_workers`

### Extending Excel Output
- Modify `write_workers_to_sheet()` in `excel/io.py`
- Add new columns to `COLUMN_MAP`
- Preserve formatting via `copy_cell_style()`

## Building Executables

### Linux
```bash
pip install pyinstaller
pyinstaller audit-merge.spec --clean
# Output: dist/audit-merge

# Empaquetar AppImage
wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool*
mkdir -p AppDir/usr/bin && cp dist/audit-merge AppDir/usr/bin/
cp assets/audit-merge.desktop assets/audit-merge.png AppDir/
cat > AppDir/AppRun <<'EOF'
#!/bin/bash
SELF="$(readlink -f "$0")"
HERE="${SELF%/*}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${HERE}/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/audit-merge" "$@"
EOF
chmod +x AppDir/AppRun
ARCH=x86_64 ./appimagetool*x86_64.AppImage --appimage-extract-and-run AppDir dist/audit-merge-<version>-x86_64.AppImage
```

> Compila sobre la distro más antigua que quieras soportar (glibc): el CI usa `ubuntu-22.04`. En la AppImage el ícono lo aporta `assets/audit-merge.png` (PyInstaller ignora `icon.ico` en Linux).

### Windows
```bash
# On Windows machine or via GitHub Actions
pyinstaller audit-merge.spec --clean
# Output: dist/audit-merge.exe
```

### Cross-Platform Notes
- **PyInstaller cannot cross-compile** — build on target OS
- Linux binary won't run on Windows and vice versa
- GitHub Actions builds both (`.exe` en `windows-latest`, AppImage en `ubuntu-22.04`) y publica la release desde un job `release` separado

## Testing Strategy

### Unit Tests (models, diff)
```python
# tests/test_models.py
def test_worker_key():
    w = Worker(no=123, curp="ABC123", nss="456")
    assert w.key == (123, "ABC123", "456")

# tests/test_diff.py
def test_auto_mergeable():
    # Only X added, no removals
    assert diff.is_auto_mergeable == True
```

### Integration Tests
```python
# tests/test_integration.py
def test_full_merge():
    base = load_workbook("base.xlsx")
    updated = load_workbook("updated.xlsx")
    # ... run full pipeline
    assert output_exists
```

### Manual Testing Checklist
- [ ] File picker navigates directories
- [ ] Only .xlsx/.xls selectable
- [ ] Statistics match expected counts
- [ ] Auto-merge applies correctly
- [ ] Conflict review shows all diffs
- [ ] Manual edit saves all fields
- [ ] Output file opens in Excel
- [ ] Formatting preserved (colors, borders, formulas)

## Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues
| Issue | Solution |
|-------|----------|
| Import errors | Run `pip install -e .` |
| PySide6 widget/import not found | Add to `hiddenimports` in spec |
| Excel formatting lost | Check `copy_cell_style()` |
| Worker not matched | Verify CURP/NSS normalization |

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit: `git commit -am "Release vX.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push: `git push origin main --tags`
6. GitHub Actions builds (`build.yml`) y el job `release` publica:
   - `audit-merge-windows-<v>.exe`
   - `audit-merge-<v>-x86_64.AppImage` y binario `audit-merge`
   - GitHub además genera source code `.zip`/`.tar.gz` automáticamente

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/name`
3. Make changes with tests
4. Run quality checks: `black && ruff && pytest`
5. Submit PR with description

## Architecture Decisions

### Why PySide6 (GUI)?
- Native desktop UI (works offline, Linux + Windows)
- Same workflow as the web version, sharing the same core
- Threaded merge via `QThread` keeps the UI responsive

### Why Flask (Web)?
- Network access for users that need it
- Same core engine, routes delegate to `diff/merge.py` and `excel/io.py`

### Why openpyxl?
- Full formatting preservation
- Formula support
- Mature, well-maintained

### Why RapidFuzz?
- Fast fuzzy matching (C++ backend)
- Flexible scoring
- No external dependencies

### Why Composite Key?
- `No` alone can change (re-numbering)
- `CURP` alone can have typos
- `NSS` alone may be missing
- Combination = robust matching

## Performance Profiling

```bash
# Profile diff algorithm
python -m cProfile -o profile.stats -m audit_merge.gui.app
# Analyze with snakeviz
snakeviz profile.stats
```

## License

MIT License — see LICENSE file for details.