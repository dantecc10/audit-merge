import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.cell.cell import Cell
from openpyxl.styles import Font, PatternFill, Border, Alignment, Protection
from typing import Optional, Dict, List
import copy

from ..models import Worker, DocumentChecklist


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


def detect_column_mapping(ws: Worksheet, header_row: int = HEADER_ROW) -> Dict[str, int]:
    """
    Detect column mapping by reading headers from the header row.
    Returns a dict mapping field_name -> column_index.
    """
    column_map = {}
    max_col = ws.max_column
    
    # Normalized header names for matching
    header_aliases = {
        "no": ["no", "número", "numero", "#"],
        "nombre": ["nombre", "nombre del colaborador", "colaborador", "trabajador"],
        "curp": ["curp"],
        "nss": ["nss", "num seguridad social", "número de seguridad social"],
        "depto": ["depto", "departamento", "depart"],
        "puesto": ["puesto", "cargo"],
        "salario": ["salario", "sueldo"],
        "fecha_reingreso": ["fecha de reingreso", "reingreso", "fecha reingreso"],
        "fecha_baja": ["fecha de baja", "baja", "fecha baja"],
        "fecha_baja_2": ["fe cha de baja", "fecha baja 2", "fecha baja (2)"],
        "fecha_baja_3": ["fe cha de baja", "fecha baja 3", "fecha baja (3)"],
        "solicitud_empleo": ["solicitud de empleo", "solicitud empleo"],
        "fecha_solicitud": ["fecha solicitud"],
        "firma": ["firma"],
        "curriculum_vitae": ["curriculum vitae", "curriculum", "cv"],
        "acta_nacimiento": ["acta de nacimiento", "acta nacimiento"],
        "ine": ["ine", "credencial"],
        "c_domicilio": ["c. domicilio", "comprobante domicilio", "domicilio"],
        "c_estudios": ["c. estudios", "comprobante estudios", "estudios"],
        "constancia_situacion_fiscal": ["constancia situación fiscal", "constancia fiscal", "situación fiscal"],
        "numero_imss": ["número de imss", "numero imss", "imss"],
        "curp_checklist": ["curp ", "curp (checklist)", "curp checklist"],
        "cta_banco": ["cta-banco", "cuenta banco", "cta banco", "cuenta bancaria"],
        "constancias_laborales": ["constancias laborales", "constancias"],
        "examen_medico": ["examen médico", "examen medico", "examen"],
        "validacion_fechas": ["validación de fechas", "validacion fechas", "validación fechas"],
        "contrato": ["contrato"],
        "infonavit": ["infonavit"],
        "designacion_beneficiarios": ["designación beneficiarios", "designacion beneficiarios", "beneficiarios"],
        "alta_imss": ["alta imss", "alta imss"],
        "contrato_asignado": ["contrato asignado", "contrato asig."],
        "no_caja": ["no. caja", "no caja", "número de caja"],
        "finiquito": ["finiquito"],
    }
    
    # Read headers from header row
    for col_idx in range(1, max_col + 1):
        cell = ws.cell(row=header_row, column=col_idx)
        header = str(cell.value or "").strip().lower()
        if not header:
            continue
        
        # Try to match header to known fields
        matched_field = None
        for field, aliases in header_aliases.items():
            if header in aliases or any(alias in header for alias in aliases):
                matched_field = field
                break
        
        if matched_field:
            column_map[matched_field] = col_idx
    
    return column_map


def merge_column_maps(base_map: Dict[str, int], updated_map: Dict[str, int]) -> Dict[str, int]:
    """Merge two column maps, preferring base for core fields, updated for new fields."""
    merged = base_map.copy()
    for field, col in updated_map.items():
        if field not in merged:
            merged[field] = col
    return merged


def read_workers_from_sheet(ws: Worksheet, column_map: Optional[Dict[str, int]] = None) -> tuple[List[Worker], Dict[str, int]]:
    """
    Read workers from sheet using dynamic column detection.
    Returns (workers_list, column_map_used).
    """
    if column_map is None:
        column_map = detect_column_mapping(ws)
    
    # Ensure core fields are present, fall back to defaults
    for field in CORE_FIELDS:
        if field not in column_map and field in DEFAULT_COLUMN_MAP:
            column_map[field] = DEFAULT_COLUMN_MAP[field]
    
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
        
        # Helper to get cell value by field name
        def get_cell_value(field: str) -> str:
            col = column_map.get(field)
            if col is None:
                return ""
            cell = ws.cell(row=row_idx, column=col)
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


def write_workers_to_sheet(ws: Worksheet, workers: List[Worker], column_map: Optional[Dict[str, int]] = None, template_row: int = DATA_START_ROW):
    """
    Write workers to sheet using the provided column map.
    Preserves formatting from template row.
    """
    if column_map is None:
        column_map = DEFAULT_COLUMN_MAP.copy()
    
    # Capture template styles
    template_cells = {}
    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=template_row, column=col_idx)
        template_cells[col_idx] = cell
    
    # Track which columns we've written to (for preserving extra columns)
    written_cols = set()
    
    for worker in workers:
        row_idx = worker.row_index
        if row_idx < DATA_START_ROW:
            row_idx = DATA_START_ROW + workers.index(worker)
        
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
    
    # Preserve any extra columns not in our map (copy from template row)
    for col_idx in range(1, ws.max_column + 1):
        if col_idx not in written_cols and col_idx in template_cells:
            # For each worker row, copy template cell
            for worker in workers:
                row_idx = worker.row_index
                if row_idx < DATA_START_ROW:
                    row_idx = DATA_START_ROW + workers.index(worker)
                cell = ws.cell(row=row_idx, column=col_idx)
                template_cell = template_cells[col_idx]
                copy_cell_style(template_cell, cell)


def load_workbook_preserving(filename: str) -> openpyxl.Workbook:
    return openpyxl.load_workbook(filename)


def save_workbook(wb: openpyxl.Workbook, filename: str):
    wb.save(filename)


def get_sheet_names(wb: openpyxl.Workbook) -> list[str]:
    return wb.sheetnames


def find_revision_sheet(wb: openpyxl.Workbook) -> Optional[str]:
    for name in wb.sheetnames:
        if "revis" in name.lower() or "exp" in name.lower():
            return name
    return wb.sheetnames[0] if wb.sheetnames else None


def read_workbook_with_detection(filename: str) -> tuple[List[Worker], Dict[str, int], str]:
    """
    High-level function: load workbook, detect sheet, detect columns, read workers.
    Returns (workers, column_map, sheet_name).
    """
    wb = load_workbook_preserving(filename)
    sheet_name = find_revision_sheet(wb)
    ws = wb[sheet_name]
    workers, column_map = read_workers_from_sheet(ws)
    return workers, column_map, sheet_name