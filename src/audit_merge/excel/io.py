import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.cell.cell import Cell
from openpyxl.styles import Font, PatternFill, Border, Alignment, Protection
from typing import Optional
import copy

from ..models import Worker, DocumentChecklist


HEADER_ROW = 3
DATA_START_ROW = 4

COLUMN_MAP = {
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

REVERSE_COLUMN_MAP = {v: k for k, v in COLUMN_MAP.items()}

CHECKLIST_COLUMNS = {
    "solicitud_empleo", "acta_nacimiento", "ine", "c_domicilio", "c_estudios",
    "constancia_situacion_fiscal", "numero_imss", "curp_checklist", "cta_banco",
    "examen_medico", "validacion_fechas", "contrato", "designacion_beneficiarios",
    "constancias_laborales"
}


def copy_cell_style(source: Cell, target: Cell):
    if source.has_style:
        target.font = copy.copy(source.font)
        target.fill = copy.copy(source.fill)
        target.border = copy.copy(source.border)
        target.alignment = copy.copy(source.alignment)
        target.number_format = source.number_format
        target.protection = copy.copy(source.protection)


def read_workers_from_sheet(ws: Worksheet) -> list[Worker]:
    workers = []
    max_row = ws.max_row
    
    for row_idx in range(DATA_START_ROW, max_row + 1):
        no_cell = ws.cell(row=row_idx, column=COLUMN_MAP["no"])
        if no_cell.value is None:
            continue
        
        try:
            no = int(no_cell.value) if no_cell.value else None
        except (ValueError, TypeError):
            no = None
        
        worker = Worker(
            no=no,
            nombre=str(ws.cell(row=row_idx, column=COLUMN_MAP["nombre"]).value or "").strip(),
            curp=str(ws.cell(row=row_idx, column=COLUMN_MAP["curp"]).value or "").strip(),
            nss=str(ws.cell(row=row_idx, column=COLUMN_MAP["nss"]).value or "").strip(),
            depto=str(ws.cell(row=row_idx, column=COLUMN_MAP["depto"]).value or "").strip(),
            puesto=str(ws.cell(row=row_idx, column=COLUMN_MAP["puesto"]).value or "").strip(),
            salario=str(ws.cell(row=row_idx, column=COLUMN_MAP["salario"]).value or "").strip(),
            fecha_reingreso=_format_cell_value(ws.cell(row=row_idx, column=COLUMN_MAP["fecha_reingreso"])),
            fecha_baja=_format_cell_value(ws.cell(row=row_idx, column=COLUMN_MAP["fecha_baja"])),
            fecha_baja_2=_format_cell_value(ws.cell(row=row_idx, column=COLUMN_MAP["fecha_baja_2"])),
            fecha_baja_3=_format_cell_value(ws.cell(row=row_idx, column=COLUMN_MAP["fecha_baja_3"])),
            row_index=row_idx,
        )
        
        checklist = DocumentChecklist()
        for field_name, col_idx in COLUMN_MAP.items():
            if field_name in CHECKLIST_COLUMNS or field_name in DocumentChecklist.DATA_FIELDS:
                cell = ws.cell(row=row_idx, column=col_idx)
                value = _format_cell_value(cell)
                if hasattr(checklist, field_name):
                    setattr(checklist, field_name, value)
        
        worker.checklist = checklist
        workers.append(worker)
    
    return workers


def _format_cell_value(cell: Cell) -> str:
    if cell.value is None:
        return ""
    if isinstance(cell.value, (int, float)):
        return str(cell.value)
    if hasattr(cell.value, 'strftime'):
        return cell.value.strftime("%d/%m/%Y")
    return str(cell.value).strip()


def write_workers_to_sheet(ws: Worksheet, workers: list[Worker], template_row: int = DATA_START_ROW):
    template_cells = {}
    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=template_row, column=col_idx)
        template_cells[col_idx] = cell
    
    for worker in workers:
        row_idx = worker.row_index
        if row_idx < DATA_START_ROW:
            row_idx = DATA_START_ROW + workers.index(worker)
        
        for field_name, col_idx in COLUMN_MAP.items():
            cell = ws.cell(row=row_idx, column=col_idx)
            template_cell = template_cells.get(col_idx)
            
            if field_name == "no":
                cell.value = worker.no
            elif field_name == "nombre":
                cell.value = worker.nombre
            elif field_name == "curp":
                cell.value = worker.curp
            elif field_name == "nss":
                cell.value = worker.nss
            elif field_name == "depto":
                cell.value = worker.depto
            elif field_name == "puesto":
                cell.value = worker.puesto
            elif field_name == "salario":
                cell.value = worker.salario
            elif field_name == "fecha_reingreso":
                cell.value = worker.fecha_reingreso
            elif field_name == "fecha_baja":
                cell.value = worker.fecha_baja
            elif field_name == "fecha_baja_2":
                cell.value = worker.fecha_baja_2
            elif field_name == "fecha_baja_3":
                cell.value = worker.fecha_baja_3
            elif hasattr(worker.checklist, field_name):
                cell.value = getattr(worker.checklist, field_name)
            
            if template_cell:
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