import sys
from pathlib import Path

import openpyxl
import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from audit_merge.models import DocumentChecklist, Worker  # noqa: E402  # noqa: E402


@pytest.fixture
def make_sheet():
    """Factory fixture that returns a function to build an in-memory worksheet."""

    def _make(headers):
        wb = openpyxl.Workbook()
        ws = wb.active
        for col, h in enumerate(headers, start=1):
            ws.cell(row=3, column=col, value=h)
        return wb, ws

    return _make


@pytest.fixture
def sample_headers():
    return [
        "No", "Nombre", "CURP", "NSS", "Depto", "Puesto", "Salario",
        "Fecha Reingreso", "Fecha Baja", "Fecha Baja 2", "Fecha Baja 3",
        "Solicitud de Empleo", "Fecha Solicitud", "Firma", "Curriculum Vitae",
        "Acta de Nacimiento", "INE", "C. Domicilio", "C. Estudios",
        "Constancia Situación Fiscal", "Número de IMSS", "CURP (checklist)",
        "Cta-Banco", "Constancias Laborales", "Examen Médico",
        "Validación de Fechas", "Contrato", "Infonavit",
        "Designación Beneficiarios", "Alta IMSS", "Contrato Asignado",
        "No. Caja", "Finiquito",
    ]


@pytest.fixture
def sample_worker():
    def _make(no=1, nombre="Juan Pérez", curp="PJ", nss="12345"):
        w = Worker(
            no=no,
            nombre=nombre,
            curp=curp,
            nss=nss,
            depto="RH",
            puesto="Analista",
            salario="15000",
            row_index=4,
        )
        cl = DocumentChecklist()
        cl.solicitud_empleo = "X"
        w.checklist = cl
        return w

    return _make


def build_worker_row(ws, row, values: dict):
    """Write a worker row into a worksheet using the given field->col map."""
    for field, col in values.items():
        ws.cell(row=row, column=col, value=values[field])
