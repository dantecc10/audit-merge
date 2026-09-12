# User Guide

## Getting Started

### Windows
1. Download `audit-merge.exe` from the [Releases page](https://github.com/dantecc10/audit-merge/releases)
2. Double-click to run (or run from Command Prompt/PowerShell)

### Linux
```bash
# Option 1: Run from source
git clone https://github.com/dantecc10/audit-merge
cd audit-merge
pip install -e .
python run_app.py

# Option 2: Build and run executable
pip install pyinstaller
pyinstaller audit-merge.spec --clean
./dist/audit-merge
```

## Step-by-Step Workflow

### 1. Select Base Document
When the app starts, you'll see the **File Picker** screen:

```
┌─────────────────────────────────────────────────────────────┐
│ Select base File                                            │
├─────────────────────────────────────────────────────────────┤
│ Selected file path will appear here...                      │
├─────────────────────────────────────────────────────────────┤
│ 📂 home                                                     │
│ ├── 📁 user                                                 │
│ │   ├── 📁 Documents                                        │
│ │   │   ├── 📄 plantilla.xlsx        ← Navigate with ↑/↓   │
│ │   │   └── 📄 otros.xlsx             ← Enter to select    │
│ │   └── 📁 Downloads                                      │
│ └── 📁 ...                                                │
├─────────────────────────────────────────────────────────────┤
│ [Confirm] (disabled until .xlsx selected)   [Cancel]       │
└─────────────────────────────────────────────────────────────┘
```

**Actions:**
- `↑/↓` — Navigate directory tree
- `←/→` — Collapse/expand folders
- `Enter` — Select file (only `.xlsx`/`.xls` enabled)
- `Esc` — Cancel and exit

### 2. Select Updated Document
Same file picker appears for the worker's updated file.

### 3. Statistics Dashboard
After both files are loaded, the **Statistics Dashboard** shows:

```
┌─────────────────────────────────────────────────────────────┐
│ Statistics Dashboard                                        │
├─────────────────────────────────────────────────────────────┤
│ Base file workers:        859                               │
│ Updated file workers:     847                               │
│                                                                 │
│ ✓ Auto-mergeable:         723                               │
│ ⚠ Conflicts to review:    124                               │
│                                                                 │
│   X's added:              1,234                             │
│   X's removed:            45                                │
│   Data fields changed:    32                                │
│   Workers added:          35                                │
│   Workers removed:        12                                │
├─────────────────────────────────────────────────────────────┤
│ [A] Apply Auto-Merge    [R] Review Conflicts               │
│ [S] Save Output         [Esc] Back                          │
└─────────────────────────────────────────────────────────────┘
```

**Understanding the counts:**

| Metric | Meaning |
|--------|---------|
| **Auto-mergeable** | Workers where only X marks were added (safe to merge automatically) |
| **Conflicts** | Workers needing manual review (X removed, data changed, or worker added/removed) |
| **X's added** | Total checklist items newly marked with X |
| **X's removed** | Total checklist items unmarked (potential issues) |
| **Data fields changed** | Non-checklist fields modified (name, dept, dates, etc.) |
| **Workers added/removed** | Rows present in one file but not the other |

### 4. Apply Auto-Merge (Optional but Recommended)
Press **`A`** to automatically merge all safe changes:
- Only applies to workers with **only X additions**
- No data removed or modified
- Updates statistics dashboard after completion

### 5. Review Conflicts
Press **`R`** to open the **Conflict Review** screen for each conflicted worker:

```
┌─────────────────────────────────────────────────────────────┐
│ Conflict 1/124: Worker #1641 BALTAZAR ESPINOSA...          │
├─────────────────────────────────────────────────────────────┤
│ Field: Acta de Nacimiento (checklist)                       │
│ Base:    [X]    Updated: [ ]   ← REMOVED                    │
│ Field: Fecha de baja (data)                                 │
│ Base:    [22/08/2025]  Updated: [ ]  ← CLEARED              │
├─────────────────────────────────────────────────────────────┤
│ [K] Keep Base    [U] Use Updated    [M] Manual Edit         │
│ [N] Next         [P] Previous     [Esc] Done               │
└─────────────────────────────────────────────────────────────┘
```

**Resolution Options:**
| Key | Action | When to Use |
|-----|--------|-------------|
| `K` | **Keep Base** | X was removed by mistake; base is correct |
| `U` | **Use Updated** | Worker intentionally unmarked document; updated is correct |
| `M` | **Manual Edit** | Need field-by-field control (opens detailed form) |
| `N` / `P` | Next / Previous | Navigate without resolving |
| `Esc` | Done | Return to dashboard |

### 6. Manual Edit (For Complex Conflicts)
Press **`M`** to edit all fields individually:

```
┌─────────────────────────────────────────────────────────────┐
│ Manual Edit: Worker #1641 BALTAZAR ESPINOSA...             │
├─────────────────────────────────────────────────────────────┤
│ Nombre:              [BALTAZAR ESPINOSA...           ]      │
│ CURP:                [BAEA800823HPLLSR02            ]      │
│ NSS:                 [48008074162                  ]      │
│ Depto:               [TALACHERIA                  ]      │
│ Puesto:              [OF TALACHERO B              ]      │
│ Acta Nacimiento:     [X                            ]      │
│ INE:                 [X                            ]      │
│ ...                                                           │
├─────────────────────────────────────────────────────────────┤
│ [Save]    [Cancel]                                          │
└─────────────────────────────────────────────────────────────┘
```

### 7. Save Output
Press **`S`** on the dashboard to generate the merged file:

```
Output: Expedientes-Plantilla_Jaes_2025_Merged_20250912_143022.xlsx
```

The file is saved in the same directory as the base document.

## Keyboard Shortcuts Reference

| Screen | Key | Action |
|--------|-----|--------|
| **File Picker** | `↑/↓` | Navigate tree |
| | `←/→` | Collapse/expand folder |
| | `Enter` | Select file |
| | `Esc` | Cancel |
| **Dashboard** | `A` | Apply auto-merge |
| | `R` | Review conflicts |
| | `S` | Save output |
| | `Esc` | Back to file picker |
| **Conflict Review** | `K` | Keep base version |
| | `U` | Use updated version |
| | `M` | Manual edit |
| | `N` / `P` | Next / Previous conflict |
| | `Esc` | Return to dashboard |
| **Manual Edit** | `Tab` / `Shift+Tab` | Navigate fields |
| | `Enter` | Save |
| | `Esc` | Cancel |
| **Global** | `Ctrl+C` / `Q` | Quit application |

## Tips & Best Practices

### File Preparation
- Ensure both files have the same sheet structure ("Revisión Exp" sheet)
- Base file should be the master template
- Updated files should come from individual workers

### Reviewing Conflicts
- **X removed** = Document was unmarked — verify if intentional
- **Data changed** = Name, department, dates modified — verify correctness
- **Worker added** = New hire — confirm details
- **Worker removed** = Termination or error — verify

### Auto-Merge Safety
Auto-merge only applies when:
- ✅ X marks only added (never removed)
- ✅ No data field changes
- ✅ Worker exists in both files

This ensures zero-risk automatic merging.

### Output Files
- Original base file is **never modified**
- Output includes timestamp to prevent overwrites
- All original formatting preserved

## Troubleshooting

### "tkinter not available" (Old versions)
Fixed in v1.0.3+ — uses Textual's native DirectoryTree.

### File picker shows empty
- Navigate with arrow keys
- Press `Enter` on folders to expand
- Ensure you're selecting `.xlsx` or `.xls` files

### Statistics show unexpected counts
- Check that both files use the same sheet name ("Revisión Exp")
- Verify worker matching keys (No, CURP, NSS) are consistent

### Executable won't run on Linux
```bash
chmod +x audit-merge
./audit-merge
```

### Permission denied on output
- Run from a directory you own
- Check write permissions on base file directory

## Support

- **Issues**: [GitHub Issues](https://github.com/dantecc10/audit-merge/issues)
- **Documentation**: [Architecture Guide](architecture.md)
- **Changelog**: [Releases](https://github.com/dantecc10/audit-merge/releases)