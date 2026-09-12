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
| `textual` | TUI framework | ≥0.52.0 |
| `rich` | Terminal formatting | ≥13.7.0 |
| `rapidfuzz` | Fuzzy string matching | ≥3.9.0 |
| `python-dateutil` | Date parsing | ≥2.8.2 |
| `pyinstaller` | Executable building | ≥6.5.0 |

## Running the Application

### From Source
```bash
python run_app.py
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
│       └── build-windows.yml    # CI/CD for Windows builds
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
│       └── tui/
│           └── app.py          # Textual TUI application
├── audit-merge.spec             # PyInstaller configuration
├── pyproject.toml               # Project metadata & build config
├── run_app.py                   # Entry point
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

### Adding TUI Screens
1. Create new `Screen` subclass in `tui/app.py`
2. Add `BINDINGS` for keyboard shortcuts
3. Implement `compose()`, event handlers, actions
4. Navigate with `self.app.push_screen(Screen(...))`

### Extending Excel Output
- Modify `write_workers_to_sheet()` in `excel/io.py`
- Add new columns to `COLUMN_MAP`
- Preserve formatting via `copy_cell_style()`

## Building Executables

### Linux
```bash
pyinstaller audit-merge.spec --clean
# Output: dist/audit-merge
```

### Windows
```bash
# On Windows machine or via GitHub Actions
pyinstaller audit-merge.spec --clean
# Output: dist/audit-merge.exe
```

### Cross-Platform Notes
- **PyInstaller cannot cross-compile** — build on target OS
- Linux binary won't run on Windows and vice versa
- GitHub Actions handles Windows builds automatically

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
| Textual widget not found | Add to `hiddenimports` in spec |
| Excel formatting lost | Check `copy_cell_style()` |
| Worker not matched | Verify CURP/NSS normalization |

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit: `git commit -am "Release vX.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push: `git push origin main --tags`
6. GitHub Actions builds and creates release

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/name`
3. Make changes with tests
4. Run quality checks: `black && ruff && pytest`
5. Submit PR with description

## Architecture Decisions

### Why Textual?
- Native terminal UI (no X11/Wayland dependencies)
- Keyboard-first navigation
- Cross-platform (Linux, Windows, macOS)
- Built-in widgets (DirectoryTree, DataTable, etc.)

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
python -m cProfile -o profile.stats -m audit_merge.tui.app
# Analyze with snakeviz
snakeviz profile.stats
```

## License

MIT License — see LICENSE file for details.