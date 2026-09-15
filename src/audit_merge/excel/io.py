import copy

import openpyxl
from openpyxl.cell.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet

from ..models import DocumentChecklist, Worker

HEADER_ROW = 3
DATA_START_ROW = 4

# Default column map (fallback for backwards compatibility)
DEFAULT_COLUMN_MAP = {
    "no": 1,
    "nombre": 2,
    "curp": 3,
    "nss": 4,
    "depto": 5,
    "puesto": 6,
    "salario": 7,
    "fecha_reingreso": 8,
    "fecha_baja": 9,
    "fecha_baja_2": 10,
    "fecha_baja_3": 11,
    "solicitud_empleo": 12,
    "fecha_solicitud": 13,
    "firma": 14,
    "curriculum_vitae": 15,
    "acta_nacimiento": 16,
    "ine": 17,
    "c_domicilio": 18,
    "c_estudios": 19,
    "constancia_situacion_fiscal": 20,
    "numero_imss": 21,
    "curp_checklist": 22,
    "cta_banco": 23,
    "constancias_laborales": 24,
    "examen_medico": 25,
    "validacion_fechas": 26,
    "contrato": 27,
    "infonavit": 28,
    "designacion_beneficiarios": 29,
    "alta_imss": 30,
    "contrato_asignado": 31,
    "no_caja": 32,
    "finiquito": 33,
}

CHECKLIST_FIELDS = {
    "solicitud_empleo", "acta_nacimiento", "ine", "c_domicilio", "c_estudios",
    "constancia_situacion_fiscal", "numero_imss", "curp_checklist", "cta_banco",
    "examen_medico", "validacion_fechas", "contrato", "designacion_beneficiarios",
    "constancias_laborales"
}

DATA_FIELDS = {
    "fecha_solicitud", "firma", "curriculum_vitae",
    "infonavit", "alta_imss", "contrato_asignado", "no_caja", "finiquito"
}

# Core worker fields (always mapped)
CORE_FIELDS = {
    "no", "nombre", "curp", "nss", "depto", "puesto", "salario",
    "fecha_reingreso", "fecha_baja", "fecha_baja_2", "fecha_baja_3"
}

ALL_CHECKLIST_FIELDS = CHECKLIST_FIELDS | DATA_FIELDS


def copy_cell_style(source: Cell, target: Cell):
    if source.has_style:
        target.font = copy.copy(source.font)
        target.fill = copy.copy(source.fill)
        target.border = copy.copy(source.border)
        target.alignment = copy.copy(source.alignment)
        target.number_format = source.number_format
        target.protection = copy.copy(source.protection)


def _normalize_header(text: str) -> str:
    """Normalize a header string: lowercase, strip accents, collapse whitespace."""
    import unicodedata
    text = text.strip().lower()
    # Strip accents: decomposition + remove combining marks
    nfkd = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Remove trailing/leading punctuation (e.g. "No." -> "no", "N° Caja" -> "no caja")
    text = text.strip(" .,;:()[]'\"`“”")
    # Collapse multiple spaces
    text = " ".join(text.split())
    return text


def detect_column_mapping(ws: Worksheet, header_row: int = HEADER_ROW) -> dict[str, int]:
    """
    Detect column mapping by reading headers from the header row.
    Returns a dict mapping field_name -> column_index.

    Matching strategy (in order):
    1. Exact match against normalized aliases
    2. For short aliases (1-2 words), exact word match only
    3. For longer aliases (3+ words), containment is allowed
    """
    column_map = {}
    max_col = ws.max_column

    header_aliases = {
        "no": ["no", "numero", "#"],
        "nombre": ["nombre", "nombre del colaborador", "colaborador", "trabajador"],
        "curp": ["curp"],
        "nss": ["nss", "num seguridad social", "numero de seguridad social"],
        "depto": ["depto", "departamento", "depart"],
        "puesto": ["puesto", "cargo"],
        "salario": ["salario", "sueldo"],
        "fecha_reingreso": ["fecha de reingreso", "reingreso", "fecha reingreso"],
        "fecha_baja": ["fecha de baja", "baja", "fecha baja"],
        "fecha_baja_2": ["fecha baja 2", "fecha baja (2)"],
        "fecha_baja_3": ["fecha baja 3", "fecha baja (3)"],
        "solicitud_empleo": ["solicitud de empleo", "solicitud empleo"],
        "fecha_solicitud": ["fecha solicitud"],
        "firma": ["firma"],
        "curriculum_vitae": ["curriculum vitae", "curriculum", "cv"],
        "acta_nacimiento": ["acta de nacimiento", "acta nacimiento"],
        "ine": ["ine", "credencial"],
        "c_domicilio": ["c. domicilio", "comprobante de domicilio", "comprobante domicilio", "domicilio"],
        "c_estudios": ["c. estudios", "comprobante de estudios", "comprobante estudios", "estudios"],
        "constancia_situacion_fiscal": [
            "constancia situacion fiscal", "constancia de situacion fiscal",
            "constancia fiscal", "situacion fiscal",
        ],
        "numero_imss": ["numero de imss", "numero imss", "imss"],
        "curp_checklist": ["curp checklist", "curp (checklist)"],
        "cta_banco": ["cta-banco", "cuenta banco", "cta banco", "cuenta bancaria"],
        "constancias_laborales": ["constancias laborales", "constancias"],
        "examen_medico": ["examen medico", "examen"],
        "validacion_fechas": ["validacion de fechas", "validacion fechas"],
        "contrato": ["contrato"],
        "infonavit": ["infonavit"],
        "designacion_beneficiarios": [
            "designacion beneficiarios", "designacion de beneficiarios", "beneficiarios",
        ],
        "alta_imss": ["alta imss"],
        "contrato_asignado": ["contrato asignado", "contrato asig."],
        "no_caja": ["no. caja", "no caja", "numero de caja"],
        "finiquito": ["finiquito"],
    }

    # Pre-normalize all aliases
    normalized_aliases: dict[str, list[tuple[str, list[str]]]] = {}
    for field, aliases in header_aliases.items():
        normalized_aliases[field] = [
            (alias, _normalize_header(alias).split()) for alias in aliases
        ]

    for col_idx in range(1, max_col + 1):
        cell = ws.cell(row=header_row, column=col_idx)
        header = str(cell.value or "")
        norm = _normalize_header(header)
        if not norm:
            continue

        matched_field = None
        for field, alias_list in normalized_aliases.items():
            for alias_text, _alias_words in alias_list:
                if norm == alias_text:
                    matched_field = field
                    break
            if matched_field:
                break

        if not matched_field:
            for field, alias_list in normalized_aliases.items():
                for alias_text, alias_words in alias_list:
                    if len(alias_words) >= 3 and alias_text in norm:
                        matched_field = field
                        break
                if matched_field:
                    break

        if matched_field and matched_field not in column_map:
            column_map[matched_field] = col_idx

    return column_map


def merge_column_maps(base_map: dict[str, int], updated_map: dict[str, int]) -> dict[str, int]:
    """Merge two column maps, preferring base for core fields, updated for new fields."""
    merged = base_map.copy()
    for field, col in updated_map.items():
        if field not in merged:
            merged[field] = col
    return merged


def read_workers_from_sheet(ws: Worksheet, column_map: dict[str, int] | None = None) -> tuple[list[Worker], dict[str, int]]:
    """
    Read workers from sheet using dynamic column detection.
    Returns (workers_list, column_map_used).
    The column_map includes both known fields and any extra columns detected.

    Extra (unrecognized) columns are captured FIRST, before any default fallback,
    so that real sheet columns are never masked by DEFAULT_COLUMN_MAP positions.
    Default fallback only fills free columns (no header present) to avoid writing
    values into the wrong columns.
    """
    if column_map is None:
        column_map = detect_column_mapping(ws)
    else:
        column_map = dict(column_map)

    known_cols = set(column_map.values())

    # Detect extra columns: columns with headers not mapped to any known field
    extra_columns: dict[str, int] = {}
    max_col = ws.max_column
    for col_idx in range(1, max_col + 1):
        if col_idx in known_cols:
            continue
        cell = ws.cell(row=HEADER_ROW, column=col_idx)
        header = str(cell.value or "").strip()
        if header:
            norm = _normalize_header(header)
            if norm and norm not in column_map:
                key = f"extra:{norm}"
                extra_columns[key] = col_idx
                known_cols.add(col_idx)
    column_map.update(extra_columns)

    # Ensure core fields are present, but ONLY fall back to free columns
    # (no header detected at the default position). Never overwrite a column
    # that holds a real, different header.
    for field in CORE_FIELDS:
        if field in column_map:
            continue
        col = DEFAULT_COLUMN_MAP.get(field)
        if col is None or col in known_cols:
            continue
        header_at_col = ws.cell(row=HEADER_ROW, column=col).value
        if header_at_col is None or str(header_at_col).strip() == "":
            column_map[field] = col
            known_cols.add(col)

    workers = []
    max_row = ws.max_row

    for row_idx in range(DATA_START_ROW, max_row + 1):
        # Check if row has data (using 'no' field as anchor)
        no_col = column_map.get("no", DEFAULT_COLUMN_MAP["no"])
        no_cell = ws.cell(row=row_idx, column=no_col)
        if no_cell.value is None:
            continue

        try:
            no = int(no_cell.value) if no_cell.value else None
        except (ValueError, TypeError):
            no = None

        def get_cell_value(field: str, _row: int = row_idx) -> str:
            col = column_map.get(field)
            if col is None:
                return ""
            cell = ws.cell(row=_row, column=col)
            return _format_cell_value(cell)

        worker = Worker(
            no=no,
            nombre=get_cell_value("nombre").strip(),
            curp=get_cell_value("curp").strip(),
            nss=get_cell_value("nss").strip(),
            depto=get_cell_value("depto").strip(),
            puesto=get_cell_value("puesto").strip(),
            salario=get_cell_value("salario").strip(),
            fecha_reingreso=get_cell_value("fecha_reingreso"),
            fecha_baja=get_cell_value("fecha_baja"),
            fecha_baja_2=get_cell_value("fecha_baja_2"),
            fecha_baja_3=get_cell_value("fecha_baja_3"),
            row_index=row_idx,
        )

        checklist = DocumentChecklist()
        all_fields = CHECKLIST_FIELDS | DATA_FIELDS
        for field_name in all_fields:
            value = get_cell_value(field_name)
            if hasattr(checklist, field_name):
                setattr(checklist, field_name, value)
        worker.checklist = checklist

        # Read extra fields
        extra = {}
        for field_name, col_idx in extra_columns.items():
            cell = ws.cell(row=row_idx, column=col_idx)
            extra[field_name] = _format_cell_value(cell)
        worker.extra_fields = extra

        workers.append(worker)

    return workers, column_map


def _format_cell_value(cell: Cell) -> str:
    if cell.value is None:
        return ""
    if isinstance(cell.value, (int, float)):
        return str(cell.value)
    if hasattr(cell.value, 'strftime'):
        return cell.value.strftime("%d/%m/%Y")
    return str(cell.value).strip()


def write_workers_to_sheet(ws: Worksheet, workers: list[Worker], column_map: dict[str, int] | None = None, template_row: int = DATA_START_ROW):
    """
    Write workers to sheet using the provided column map.
    Preserves formatting from template row. Writes extra_fields to their mapped columns.

    Row assignment: each worker keeps its original row_index when that row is free
    (preserving base-file layout). When two workers collide on the same row
    (e.g. a new worker from the updated file lands on a base worker's row), the
    later worker is re-assigned to the next free row, so no data is overwritten.
    """
    if column_map is None:
        column_map = DEFAULT_COLUMN_MAP.copy()

    # Capture template styles
    template_cells = {}
    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=template_row, column=col_idx)
        template_cells[col_idx] = cell

    # Assign collision-free rows, preserving original row_index when available
    assigned_rows = {}
    used_rows = set()
    next_free_row = max([w.row_index for w in workers if w.row_index >= DATA_START_ROW] + [DATA_START_ROW - 1]) + 1
    for worker in workers:
        r = worker.row_index
        if r >= DATA_START_ROW and r not in used_rows:
            used_rows.add(r)
        else:
            while next_free_row in used_rows:
                next_free_row += 1
            r = next_free_row
            next_free_row += 1
            used_rows.add(r)
        assigned_rows[id(worker)] = r

    written_cols = set()

    for worker in workers:
        row_idx = assigned_rows[id(worker)]

        # Write core fields
        for field_name in CORE_FIELDS:
            col_idx = column_map.get(field_name)
            if col_idx is None:
                continue
            cell = ws.cell(row=row_idx, column=col_idx)
            template_cell = template_cells.get(col_idx)

            value = getattr(worker, field_name, "")
            cell.value = value

            if template_cell:
                copy_cell_style(template_cell, cell)
            written_cols.add(col_idx)

        # Write checklist/data fields
        all_fields = CHECKLIST_FIELDS | DATA_FIELDS
        for field_name in all_fields:
            col_idx = column_map.get(field_name)
            if col_idx is None:
                continue
            cell = ws.cell(row=row_idx, column=col_idx)
            template_cell = template_cells.get(col_idx)

            value = getattr(worker.checklist, field_name, "")
            cell.value = value

            if template_cell:
                copy_cell_style(template_cell, cell)
            written_cols.add(col_idx)

        # Write extra fields
        for field_name, value in worker.extra_fields.items():
            col_idx = column_map.get(field_name)
            if col_idx is None:
                continue
            cell = ws.cell(row=row_idx, column=col_idx)
            template_cell = template_cells.get(col_idx)
            cell.value = value
            if template_cell:
                copy_cell_style(template_cell, cell)
            written_cols.add(col_idx)

    # Preserve any extra columns not in our map (copy from template row)
    for col_idx in range(1, ws.max_column + 1):
        if col_idx not in written_cols and col_idx in template_cells:
            for worker in workers:
                row_idx = assigned_rows[id(worker)]
                cell = ws.cell(row=row_idx, column=col_idx)
                template_cell = template_cells[col_idx]
                copy_cell_style(template_cell, cell)


def load_workbook_preserving(filename: str) -> openpyxl.Workbook:
    return openpyxl.load_workbook(filename)


def save_workbook(wb: openpyxl.Workbook, filename: str):
    wb.save(filename)


def get_sheet_names(wb: openpyxl.Workbook) -> list[str]:
    return wb.sheetnames


def find_revision_sheet(wb: openpyxl.Workbook) -> str | None:
    for name in wb.sheetnames:
        if "revis" in name.lower() or "exp" in name.lower():
            return name
    return wb.sheetnames[0] if wb.sheetnames else None


def read_workbook_with_detection(filename: str) -> tuple[list[Worker], dict[str, int], str]:
    """
    High-level function: load workbook, detect sheet, detect columns, read workers.
    Returns (workers, column_map, sheet_name).
    """
    wb = load_workbook_preserving(filename)
    sheet_name = find_revision_sheet(wb)
    ws = wb[sheet_name]
    workers, column_map = read_workers_from_sheet(ws)
    return workers, column_map, sheet_name
