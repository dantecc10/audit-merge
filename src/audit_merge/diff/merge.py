from rapidfuzz import fuzz, process
from typing import Optional
from collections import defaultdict

from ..models import Worker, WorkerDiff, FieldDiff, ChangeType, MergeStats, DocumentChecklist


def match_workers(base_workers: list[Worker], updated_workers: list[Worker]) -> dict[tuple, tuple[Optional[Worker], Optional[Worker]]]:
    base_by_key = {w.key: w for w in base_workers}
    updated_by_key = {w.key: w for w in updated_workers}
    
    all_keys = set(base_by_key.keys()) | set(updated_by_key.keys())
    matches = {}
    
    for key in all_keys:
        base_w = base_by_key.get(key)
        updated_w = updated_by_key.get(key)
        
        if base_w and updated_w:
            matches[key] = (base_w, updated_w)
        elif base_w and not updated_w:
            matches[key] = (base_w, None)
        elif updated_w and not base_w:
            fuzzy_match = _find_fuzzy_match(updated_w, base_workers)
            if fuzzy_match:
                matches[fuzzy_match.key] = (fuzzy_match, updated_w)
            else:
                matches[key] = (None, updated_w)
    
    return matches


def _find_fuzzy_match(worker: Worker, candidates: list[Worker], threshold: int = 85) -> Optional[Worker]:
    if not worker.nombre:
        return None
    
    best_match = None
    best_score = 0
    
    for candidate in candidates:
        if candidate.key in [w.key for w in candidates if w.key == worker.key]:
            continue
        
        score = fuzz.ratio(worker.nombre.upper(), candidate.nombre.upper())
        if score > best_score and score >= threshold:
            if worker.curp and candidate.curp:
                curp_score = fuzz.ratio(worker.curp, candidate.curp)
                score = (score + curp_score) / 2
            if worker.nss and candidate.nss:
                nss_score = fuzz.ratio(worker.nss, candidate.nss)
                score = (score + nss_score) / 2
            
            if score > best_score:
                best_score = score
                best_match = candidate
    
    return best_match


def diff_workers(base: Optional[Worker], updated: Optional[Worker]) -> WorkerDiff:
    diff = WorkerDiff(
        worker_key=base.key if base else updated.key,
        base_worker=base,
        updated_worker=updated,
    )
    
    if base is None and updated is not None:
        diff.field_diffs.append(FieldDiff("worker", "", "NEW", ChangeType.ADDED))
        return diff
    
    if base is not None and updated is None:
        diff.field_diffs.append(FieldDiff("worker", "EXISTING", "", ChangeType.REMOVED))
        return diff
    
    if base is None or updated is None:
        return diff
    
    data_fields = [
        ("nombre", base.nombre, updated.nombre),
        ("curp", base.curp, updated.curp),
        ("nss", base.nss, updated.nss),
        ("depto", base.depto, updated.depto),
        ("puesto", base.puesto, updated.puesto),
        ("salario", base.salario, updated.salario),
        ("fecha_reingreso", base.fecha_reingreso, updated.fecha_reingreso),
        ("fecha_baja", base.fecha_baja, updated.fecha_baja),
        ("fecha_baja_2", base.fecha_baja_2, updated.fecha_baja_2),
        ("fecha_baja_3", base.fecha_baja_3, updated.fecha_baja_3),
    ]
    
    for field_name, base_val, updated_val in data_fields:
        if _normalize_value(base_val) != _normalize_value(updated_val):
            change_type = ChangeType.MODIFIED
            if not base_val and updated_val:
                change_type = ChangeType.ADDED
            elif base_val and not updated_val:
                change_type = ChangeType.REMOVED
            
            diff.field_diffs.append(FieldDiff(field_name, base_val, updated_val, change_type))
            if field_name not in ["no"]:
                diff.data_changed.append(field_name)
    
    base_checklist = base.checklist
    updated_checklist = updated.checklist
    
    diff.checklist_added = base_checklist.has_x_added(updated_checklist)
    diff.checklist_removed = base_checklist.has_x_removed(updated_checklist)
    
    for field in diff.checklist_added:
        diff.field_diffs.append(FieldDiff(field, "", "X", ChangeType.ADDED))
    for field in diff.checklist_removed:
        diff.field_diffs.append(FieldDiff(field, "X", "", ChangeType.REMOVED))
    
    for field in DocumentChecklist.DATA_FIELDS:
        base_val = getattr(base_checklist, field)
        updated_val = getattr(updated_checklist, field)
        if _normalize_value(base_val) != _normalize_value(updated_val):
            change_type = ChangeType.MODIFIED
            if not base_val and updated_val:
                change_type = ChangeType.ADDED
            elif base_val and not updated_val:
                change_type = ChangeType.REMOVED
            diff.field_diffs.append(FieldDiff(field, base_val, updated_val, change_type))
            diff.data_changed.append(field)
    
    return diff


def _normalize_value(val: str) -> str:
    if val is None:
        return ""
    return str(val).strip().upper()


def compute_stats(diffs: list[WorkerDiff]) -> MergeStats:
    stats = MergeStats()
    stats.total_base = sum(1 for d in diffs if d.base_worker is not None)
    stats.total_updated = sum(1 for d in diffs if d.updated_worker is not None)
    stats.auto_mergeable = sum(1 for d in diffs if d.is_auto_mergeable)
    stats.conflicts = sum(1 for d in diffs if d.has_conflicts)
    stats.workers_added = sum(1 for d in diffs if d.base_worker is None and d.updated_worker is not None)
    stats.workers_removed = sum(1 for d in diffs if d.base_worker is not None and d.updated_worker is None)
    
    for d in diffs:
        stats.checklist_added_total += len(d.checklist_added)
        stats.checklist_removed_total += len(d.checklist_removed)
        stats.data_changed_total += len(d.data_changed)
    
    return stats


def apply_auto_merge(base_worker: Worker, updated_worker: Worker) -> Worker:
    merged = Worker(
        no=base_worker.no,
        nombre=base_worker.nombre,
        curp=base_worker.curp,
        nss=base_worker.nss,
        depto=base_worker.depto,
        puesto=base_worker.puesto,
        salario=base_worker.salario,
        fecha_reingreso=base_worker.fecha_reingreso,
        fecha_baja=base_worker.fecha_baja,
        fecha_baja_2=base_worker.fecha_baja_2,
        fecha_baja_3=base_worker.fecha_baja_3,
        row_index=base_worker.row_index,
    )
    
    merged_checklist = DocumentChecklist()
    base_cl = base_worker.checklist
    updated_cl = updated_worker.checklist
    
    for field in DocumentChecklist.CHECKLIST_FIELDS:
        base_val = getattr(base_cl, field)
        updated_val = getattr(updated_cl, field)
        if base_val.strip().upper() == "X" or updated_val.strip().upper() == "X":
            setattr(merged_checklist, field, "X")
        else:
            setattr(merged_checklist, field, base_val)
    
    for field in DocumentChecklist.DATA_FIELDS:
        updated_val = getattr(updated_cl, field)
        base_val = getattr(base_cl, field)
        if updated_val.strip():
            setattr(merged_checklist, field, updated_val)
        else:
            setattr(merged_checklist, field, base_val)
    
    merged.checklist = merged_checklist
    return merged


def apply_conflict_resolution(base_worker: Worker, updated_worker: Worker, 
                               resolution: dict[str, str]) -> Worker:
    merged = Worker(
        no=base_worker.no,
        nombre=resolution.get("nombre", base_worker.nombre),
        curp=resolution.get("curp", base_worker.curp),
        nss=resolution.get("nss", base_worker.nss),
        depto=resolution.get("depto", base_worker.depto),
        puesto=resolution.get("puesto", base_worker.puesto),
        salario=resolution.get("salario", base_worker.salario),
        fecha_reingreso=resolution.get("fecha_reingreso", base_worker.fecha_reingreso),
        fecha_baja=resolution.get("fecha_baja", base_worker.fecha_baja),
        fecha_baja_2=resolution.get("fecha_baja_2", base_worker.fecha_baja_2),
        fecha_baja_3=resolution.get("fecha_baja_3", base_worker.fecha_baja_3),
        row_index=base_worker.row_index,
    )
    
    merged_checklist = DocumentChecklist()
    base_cl = base_worker.checklist
    updated_cl = updated_worker.checklist
    
    all_fields = DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS
    for field in all_fields:
        resolved_val = resolution.get(field)
        if resolved_val is not None:
            setattr(merged_checklist, field, resolved_val)
        else:
            base_val = getattr(base_cl, field)
            updated_val = getattr(updated_cl, field)
            if field in DocumentChecklist.CHECKLIST_FIELDS:
                if base_val.strip().upper() == "X" or updated_val.strip().upper() == "X":
                    setattr(merged_checklist, field, "X")
                else:
                    setattr(merged_checklist, field, base_val)
            else:
                setattr(merged_checklist, field, updated_val if updated_val.strip() else base_val)
    
    merged.checklist = merged_checklist
    return merged