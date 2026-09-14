# Audit Merge Tool

Herramienta para fusionar cambios en hojas de cálculo de auditoría en flujos de verificación de nómina. Disponible como **aplicación de escritorio (PySide6)** para uso sin conexión y como **aplicación web (Flask)** para uso con red.

## Características

- **Comparar archivos Excel**: Selecciona un archivo base (plantilla) y un archivo actualizado (del trabajador)
- **Auto-merge**: Aplica automáticamente cambios seguros (solo adiciones de marca X)
- **Resolución de conflictos**: Revisión interactiva uno a uno de eliminaciones, cambios de datos, trabajadores nuevos/eliminados
- **Soporte de nuevas columnas**: Detecta columnas nuevas tanto en el archivo base como en el incremental y las preserva en la salida
- **Dashboard de estadísticas**: Conteos en tiempo real de todos los tipos de cambio
- **Salida con timestamp**: Genera `{basename}_Merged_YYYYMMDD_HHMMSS.xlsx`
- **Portable**: Ejecutable único para Windows (`.exe`) y Linux
- **Dos interfaces**: GUI nativa (offline) y Web (con red)

## Requisitos

- Python 3.11+
- Dependencias: `openpyxl`, `PySide6`, `rapidfuzz`, `python-dateutil` (base)
- Web: `flask`, `python-dotenv`, `werkzeug`

## Quick Start

### GUI nativa (desktop, sin conexión)

```bash
pip install -e .
audit-merge
```

o desde el código:

```bash
python run_gui.py
```

### Web

```bash
pip install -e ".[web]"
python run_web.py
# Abre http://localhost:5001
```

### Linux / Windows desde fuente

```bash
git clone https://github.com/dantecc10/audit-merge
cd audit-merge
pip install -e .
python run_gui.py        # GUI desktop
# o
python run_web.py        # Web
```

### Compilar ejecutable

```bash
pip install pyinstaller
pyinstaller audit-merge.spec --clean
# Output: dist/audit-merge (Linux) o dist/audit-merge.exe (Windows)
```

## Formato de Archivo

Funciona con archivos Excel (`.xlsx`, `.xls`) que contienen una hoja "Revisión Exp" con:
- Datos del trabajador: No, Nombre, CURP, NSS, Depto, Puesto, Salario, fechas
- Columnas de checklist de documentos (marcas X): Solicitud empleo, Acta nacimiento, INE, etc.
- Campos auxiliares: Fecha solicitud, Firma, Curriculum, etc.
- **Columnas nuevas**: Cualquier columna adicional con encabezado es detectada y preservada

## Estrategia de Emparejamiento

Los trabajadores se emparejan por clave compuesta: `(No, CURP, NSS)` con fallback difuso por nombre (umbral 85%).

## Salida

El archivo fusionado preserva:
- Formato original, estilos y anchos de columna
- Fórmulas (ej. VLOOKUP en la columna Salario)
- Todas las hojas del libro base
- Columnas nuevas de ambos archivos (base e incremental)

## License

MIT License