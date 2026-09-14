# User Guide

## Interfaces

The tool has two interfaces that share the same workflow:

- **GUI nativa (escritorio)**: `python run_gui.py` — funciona sin conexión.
- **Web**: `python run_web.py` y abrir `http://localhost:5001` — desde un navegador, con red.

## Getting Started

### Windows
1. Download `audit-merge.exe` from the [Releases page](https://github.com/dantecc10/audit-merge/releases)
2. Double-click to run (or run from Command Prompt/PowerShell)

### Linux / Fuente
```bash
git clone https://github.com/dantecc10/audit-merge
cd audit-merge
pip install -e .
python run_gui.py    # GUI desktop
# o
python run_web.py    # Web (http://localhost:5001)
```

## Step-by-Step Workflow

### 1. Select Base Document
En la GUI: haz clic en **Seleccionar archivo base**. En la web: usa el formulario de subida en la página principal.

### 2. Select Updated Document
Selecciona igualmente el archivo actualizado del trabajador.

### 3. Statistics Dashboard
Después de procesar ambos archivos, el **panel de estadísticas** muestra:

| Metric | Meaning |
|--------|---------|
| **Auto-mergeable** | Trabajadores donde solo se añadieron marcas X (seguro de fusionar automáticamente) |
| **Conflicts** | Trabajadores que requieren revisión manual (X eliminadas, datos cambiados, o trabajador añadido/eliminado) |
| **X's added** | Total de ítems de checklist marcados nuevos con X |
| **X's removed** | Total de ítems de checklist desmarcados (posibles problemas) |
| **Data fields changed** | Campos no-checklist modificados (nombre, depto, fechas, etc.) |
| **Workers added/removed** | Filas presentes en un archivo pero no en el otro |

### 4. Apply Auto-Merge (Optional but Recommended)
Pulsa **Aplicar Auto-Merge**:
- Solo aplica a trabajadores con **únicamente adiciones de X**
- Sin datos eliminados o modificados
- Actualiza el panel tras completarse

### 5. Review Conflicts
Pulsa **Revisar Conflictos** para revisar uno a uno cada conflicto.

**Opciones de resolución:**
| Opción | Acción | Cuándo usar |
|--------|--------|-------------|
| **Mantener Base** | Conserva la versión base | La X fue eliminada por error; la base es correcta |
| **Usar Actualizado** | Usa la versión del archivo actualizado | El desmarque es intencional; el actualizado es correcto |
| **Edición Manual** | Control campo por campo (abre formulario) | Necesitas control fino por campo |

En la web, las mismas decisiones están disponibles dentro de `conflicts.html` mediante formularios.

### 6. Save Output
Pulsa **Guardar** para generar el archivo fusionado:

```
Output: Expedientes-Plantilla_Jaes_2025_Merged_20250912_143022.xlsx
```

El archivo se guarda en el mismo directorio que el documento base (en la web, se descarga el archivo generado).

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

### GUI no abre en Linux
```bash
# Si no hay display: ejecutar la versión web en su lugar
python run_web.py
```

### Web no responde
- Verifica que el puerto 5001 esté libre (`FLASK_PORT` para cambiarlo)
- Revisa que tengas instalado el extra: `pip install -e ".[web]"`

### Statistics show unexpected counts
- Check that both files use the same sheet name ("Revisión Exp")
- Verify worker matching keys (No, CURP, NSS) are consistent

### Executable won't run on Linux
```bash
chmod +x audit-merge
./audit-merge
```

## Support

- **Issues**: [GitHub Issues](https://github.com/dantecc10/audit-merge/issues)
- **Documentation**: [Architecture Guide](architecture.md)
- **Changelog**: [Releases](https://github.com/dantecc10/audit-merge/releases)