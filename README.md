# Audit Merge Tool

Herramienta para fusionar cambios en hojas de cálculo de auditoría en flujos de verificación de nómina. Disponible como **aplicación de escritorio (PySide6)** para uso sin conexión y como **aplicación web (Flask)** para uso con red.

## Características

- **Comparar archivos Excel**: Selecciona un archivo base (plantilla) y un archivo actualizado (del trabajador)
- **Auto-merge**: Aplica automáticamente cambios seguros (solo adiciones de marca X)
- **Resolución de conflictos**: Revisión interactiva uno a uno de eliminaciones, cambios de datos, trabajadores nuevos/eliminados
- **Soporte de nuevas columnas**: Detecta columnas nuevas tanto en el archivo base como en el incremental y las preserva en la salida
- **Dashboard de estadísticas**: Conteos en tiempo real de todos los tipos de cambio
- **Salida con timestamp**: Genera `{basename}_Merged_YYYYMMDD_HHMMSS.xlsx`
- **Portable**: Ejecutable único para Windows (`.exe`) y AppImage para Linux
- **Dos interfaces**: GUI nativa (offline) y Web (con red)

## Descargas (Releases)

En la [página de releases](https://github.com/dantecc10/audit-merge/releases) se publica por versión:

| Archivo | Plataforma | Uso |
|---------|------------|-----|
| `audit-merge-windows-<versión>.exe` | Windows | Doble clic |
| `audit-merge-<versión>-x86_64.AppImage` | Linux | `chmod +x` y doble clic (o `./audit-merge-*.AppImage`) |
| `audit-merge` (binario ELF) | Linux | Útil si no hay FUSE: acompañado del AppImage |
| Source code (`.zip` / `.tar.gz`) | — | Generados automáticamente por GitHub para compilar desde fuente |

> Si el AppImage no monta (sistema sin FUSE), ejecuta `./audit-merge-*.AppImage --appimage-extract-and-run`, o usa el binario ELF incluido.

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

# (Opcional) Empaquetar AppImage Linux
wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool*
mkdir -p AppDir/usr/bin && cp dist/audit-merge AppDir/usr/bin/
cp assets/audit-merge.desktop assets/audit-merge.png AppDir/
ARCH=x86_64 ./appimagetool*x86_64.AppImage --appimage-extract-and-run AppDir dist/audit-merge-x86_64.AppImage
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