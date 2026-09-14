"""Tests for diff/merge logic including extra fields."""

from audit_merge.diff.merge import (
    apply_conflict_resolution,
    compute_stats,
    diff_workers,
    match_workers,
)
from audit_merge.models import Worker


def _worker(no=1, nombre="Juan", curp="CURP1", nss="NSS1", **kw):
    w = Worker(no=no, nombre=nombre, curp=curp, nss=nss, row_index=4)
    for k, v in kw.items():
        if hasattr(w, k):
            setattr(w, k, v)
    return w


class TestDiff:
    def test_auto_mergeable_detection(self):
        base = _worker()
        base.checklist.solicitud_empleo = ""
        updated = _worker()
        updated.checklist.solicitud_empleo = "X"
        d = diff_workers(base, updated)
        assert d.is_auto_mergeable
        assert "solicitud_empleo" in d.checklist_added
        assert not d.has_conflicts

    def test_x_removed_is_conflict(self):
        base = _worker()
        base.checklist.ine = "X"
        updated = _worker()
        updated.checklist.ine = ""
        d = diff_workers(base, updated)
        assert d.has_conflicts
        assert "ine" in d.checklist_removed

    def test_data_change_is_conflict(self):
        base = _worker(salario="10000")
        updated = _worker(salario="12000")
        d = diff_workers(base, updated)
        assert d.has_conflicts
        assert "salario" in d.data_changed

    def test_new_worker_added(self):
        base = [
            _worker(1, "Juan", "CURP1", "NSS1"),
            _worker(2, "Ana", "CURP2", "NSS2"),
        ]
        updated = [
            _worker(1, "Juan", "CURP1", "NSS1"),
            _worker(2, "Ana", "CURP2", "NSS2"),
            _worker(3, "Pedro", "CURP3", "NSS3"),
        ]
        matches = match_workers(base, updated)
        diffs = [diff_workers(b, u) for _, (b, u) in matches.items()]
        assert sum(1 for d in diffs if d.base_worker is None) == 1

    def test_removed_worker(self):
        base = [_worker(1, "Juan", "CURP1", "NSS1"), _worker(2, "Ana", "CURP2", "NSS2")]
        updated = [_worker(1, "Juan", "CURP1", "NSS1")]
        matches = match_workers(base, updated)
        diffs = [diff_workers(b, u) for _, (b, u) in matches.items()]
        assert sum(1 for d in diffs if d.updated_worker is None) == 1


class TestExtraFields:
    def test_extra_field_added_is_conflict(self):
        base = _worker()
        base.extra_fields = {"extra:telefono": ""}
        updated = _worker()
        updated.extra_fields = {"extra:telefono": "555-1234"}
        d = diff_workers(base, updated)
        assert not d.is_auto_mergeable
        assert d.has_conflicts
        assert "extra:telefono" in d.extra_added

    def test_extra_field_auto_merge_prefers_updated(self):
        base = _worker()
        base.extra_fields = {"extra:nota": "viejo"}
        updated = _worker()
        updated.extra_fields = {"extra:nota": "nuevo"}
        # Auto-merge only applies when purely checklist adds; extra not applicable
        d = diff_workers(base, updated)
        assert not d.is_auto_mergeable

        # Manual merge / conflict resolution should pick updated
        res = {"extra:nota": "nuevo"}
        merged = apply_conflict_resolution(base, updated, res)
        assert merged.extra_fields["extra:nota"] == "nuevo"

    def test_extra_field_merge_resolution(self):
        base = _worker()
        base.extra_fields = {"extra:comentario": "sin cambios"}
        updated = _worker()
        updated.extra_fields = {"extra:comentario": "actualizado"}

        # Keep base
        res_keep = {"extra:comentario": "sin cambios"}
        merged = apply_conflict_resolution(base, updated, res_keep)
        assert merged.extra_fields["extra:comentario"] == "sin cambios"

        # Use updated
        res_use = {"extra:comentario": "actualizado"}
        merged = apply_conflict_resolution(base, updated, res_use)
        assert merged.extra_fields["extra:comentario"] == "actualizado"

    def test_extra_field_removed(self):
        base = _worker()
        base.extra_fields = {"extra:campo": "valor"}
        updated = _worker()
        updated.extra_fields = {"extra:campo": ""}
        d = diff_workers(base, updated)
        assert "extra:campo" in d.extra_removed

    def test_merge_combines_base_and_updated_extra(self):
        base = _worker()
        base.extra_fields = {"extra:a": "base-a"}
        updated = _worker()
        updated.extra_fields = {"extra:b": "upd-b"}
        res = {"extra:a": "base-a", "extra:b": "upd-b"}
        merged = apply_conflict_resolution(base, updated, res)
        assert merged.extra_fields["extra:a"] == "base-a"
        assert merged.extra_fields["extra:b"] == "upd-b"


class TestStats:
    def test_compute_stats_includes_extra(self):
        base = _worker()
        base.extra_fields = {"extra:x": "a"}
        updated = _worker()
        updated.extra_fields = {"extra:x": "b"}
        d = diff_workers(base, updated)
        stats = compute_stats([d])
        assert stats.conflicts == 1
        assert stats.auto_mergeable == 0
