from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class DocumentChecklist:
    solicitud_empleo: str = ""
    fecha_solicitud: str = ""
    firma: str = ""
    curriculum_vitae: str = ""
    acta_nacimiento: str = ""
    ine: str = ""
    c_domicilio: str = ""
    c_estudios: str = ""
    constancia_situacion_fiscal: str = ""
    numero_imss: str = ""
    curp_checklist: str = ""
    cta_banco: str = ""
    constancias_laborales: str = ""
    examen_medico: str = ""
    validacion_fechas: str = ""
    contrato: str = ""
    infonavit: str = ""
    designacion_beneficiarios: str = ""
    alta_imss: str = ""
    contrato_asignado: str = ""
    no_caja: str = ""
    finiquito: str = ""

    CHECKLIST_FIELDS = [
        "solicitud_empleo", "acta_nacimiento", "ine", "c_domicilio", "c_estudios",
        "constancia_situacion_fiscal", "numero_imss", "curp_checklist", "cta_banco",
        "examen_medico", "validacion_fechas", "contrato", "designacion_beneficiarios",
        "constancias_laborales"
    ]

    DATA_FIELDS = [
        "fecha_solicitud", "firma", "curriculum_vitae",
        "infonavit", "alta_imss", "contrato_asignado", "no_caja", "finiquito"
    ]

    def get_checklist_values(self) -> dict[str, str]:
        return {k: getattr(self, k) for k in self.CHECKLIST_FIELDS}

    def get_data_values(self) -> dict[str, str]:
        return {k: getattr(self, k) for k in self.DATA_FIELDS}

    def count_x_marks(self) -> int:
        return sum(1 for v in self.get_checklist_values().values() if v.strip().upper() == "X")

    def has_x_removed(self, other: "DocumentChecklist") -> list[str]:
        removed = []
        for field in self.CHECKLIST_FIELDS:
            self_val = getattr(self, field).strip().upper()
            other_val = getattr(other, field).strip().upper()
            if self_val == "X" and other_val != "X":
                removed.append(field)
        return removed

    def has_x_added(self, other: "DocumentChecklist") -> list[str]:
        added = []
        for field in self.CHECKLIST_FIELDS:
            self_val = getattr(self, field).strip().upper()
            other_val = getattr(other, field).strip().upper()
            if self_val != "X" and other_val == "X":
                added.append(field)
        return added


@dataclass
class Worker:
    no: Optional[int] = None
    nombre: str = ""
    curp: str = ""
    nss: str = ""
    depto: str = ""
    puesto: str = ""
    salario: str = ""
    fecha_reingreso: str = ""
    fecha_baja: str = ""
    fecha_baja_2: str = ""
    fecha_baja_3: str = ""
    checklist: DocumentChecklist = field(default_factory=DocumentChecklist)
    row_index: int = 0

    @property
    def key(self) -> tuple:
        return (self.no, self.curp.strip().upper(), self.nss.strip())

    @property
    def display_name(self) -> str:
        return f"#{self.no} {self.nombre}" if self.no else self.nombre


@dataclass
class FieldDiff:
    field_name: str
    base_value: str
    updated_value: str
    change_type: ChangeType


@dataclass
class WorkerDiff:
    worker_key: tuple
    base_worker: Optional[Worker] = None
    updated_worker: Optional[Worker] = None
    field_diffs: list[FieldDiff] = field(default_factory=list)
    checklist_added: list[str] = field(default_factory=list)
    checklist_removed: list[str] = field(default_factory=list)
    data_changed: list[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.checklist_removed or self.data_changed or 
                   (self.base_worker is None) != (self.updated_worker is None))

    @property
    def is_auto_mergeable(self) -> bool:
        return (self.checklist_added and 
                not self.checklist_removed and 
                not self.data_changed and
                self.base_worker is not None and 
                self.updated_worker is not None)

    @property
    def conflict_summary(self) -> str:
        parts = []
        if self.checklist_removed:
            parts.append(f"X removed: {len(self.checklist_removed)}")
        if self.checklist_added:
            parts.append(f"X added: {len(self.checklist_added)}")
        if self.data_changed:
            parts.append(f"Data changed: {len(self.data_changed)}")
        if self.base_worker is None:
            parts.append("New worker")
        if self.updated_worker is None:
            parts.append("Worker removed")
        return "; ".join(parts) if parts else "No changes"


@dataclass
class MergeStats:
    total_base: int = 0
    total_updated: int = 0
    auto_mergeable: int = 0
    conflicts: int = 0
    checklist_added_total: int = 0
    checklist_removed_total: int = 0
    data_changed_total: int = 0
    workers_added: int = 0
    workers_removed: int = 0

    def to_dict(self) -> dict:
        return {
            "Workers in base": self.total_base,
            "Workers in updated": self.total_updated,
            "Auto-mergeable": self.auto_mergeable,
            "Conflicts to review": self.conflicts,
            "X's added": self.checklist_added_total,
            "X's removed": self.checklist_removed_total,
            "Data fields changed": self.data_changed_total,
            "Workers added": self.workers_added,
            "Workers removed": self.workers_removed,
        }