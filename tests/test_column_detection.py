"""Tests for column mapping detection and the wrong-column placement bug."""

from audit_merge.excel.io import (
    detect_column_mapping,
    merge_column_maps,
    read_workers_from_sheet,
    write_workers_to_sheet,
)
from audit_merge.models import Worker


class TestColumnDetection:
    def test_detect_standard_headers(self, make_sheet, sample_headers):
        wb, ws = make_sheet(sample_headers)
        col_map = detect_column_mapping(ws)
        assert col_map["no"] == 1
        assert col_map["nombre"] == 2
        assert col_map["curp"] == 3
        assert col_map["salario"] == 7
        assert col_map["finiquito"] == 33

    def test_no_does_not_match_numero(self, make_sheet):
        """Regression: 'No' must not match 'Numero' as a substring."""
        headers = [
            "No.", "Nombre", "CURP", "NSS", "Dep", "Puesto", "Sueldo",
            "Numero de Expediente", "Numero de IMSS",
        ]
        wb, ws = make_sheet(headers)
        col_map = detect_column_mapping(ws)
        assert col_map["no"] == 1
        assert "numero_imss" in col_map  # 'Numero de IMSS' matches alias
        assert col_map["numero_imss"] == 9

    def test_nss_not_colliding_with_no(self, make_sheet):
        headers = [
            "No", "Nombre", "CURP", "NSS", "Depto", "Puesto", "Salario",
        ]
        wb, ws = make_sheet(headers)
        col_map = detect_column_mapping(ws)
        assert col_map["no"] == 1
        assert col_map["nss"] == 4

    def test_accent_normalization(self, make_sheet):
        """Situation with accents should still match."""
        headers = ["No", "Nombre", "CURP", "NSS", "Constancia Situación Fiscal"]
        wb, ws = make_sheet(headers)
        col_map = detect_column_mapping(ws)
        assert col_map["constancia_situacion_fiscal"] == 5

    def test_generic_prefix_not_false_positive(self, make_sheet):
        """A generic header like 'Proyecto' should not map to 'Puesto'."""
        headers = ["No", "Nombre", "CURP", "NSS", "Depto", "Puesto", "Proyecto"]
        wb, ws = make_sheet(headers)
        col_map = detect_column_mapping(ws)
        # No known field should be assigned to 'Proyecto'
        assert "proyecto" not in col_map
        assert col_map.get("puesto") == 6

    def test_extra_columns_detected(self, make_sheet, sample_headers):
        headers = sample_headers + ["Observaciones", "Nuevo Campo"]
        wb, ws = make_sheet(headers)
        workers, col_map = read_workers_from_sheet(ws)
        assert "extra:observaciones" in col_map
        assert "extra:nuevo campo" in col_map


class TestColumnPlacementBug:
    def test_write_respects_detected_map(self, make_sheet):
        """Regression: values must go into their actual columns, not DEFAULT_COLUMN_MAP."""
        # Salario in column 3, Puesto in column 4 (shifted from defaults)
        headers = ["No", "Nombre", "Salario", "Puesto", "CURP", "NSS"]
        wb, ws = make_sheet(headers)
        col_map = detect_column_mapping(ws)
        assert col_map["salario"] == 3
        assert col_map["puesto"] == 4

        # Add a worker
        w = Worker(
            no=1, nombre="Ana", curp="A1", nss="111",
            salario="20000", puesto="Gerente", row_index=4,
        )
        ws.cell(row=4, column=1, value=1)
        write_workers_to_sheet(ws, [w], column_map=col_map)

        assert ws.cell(row=4, column=3).value == "20000"
        assert ws.cell(row=4, column=4).value == "Gerente"

    def test_full_roundtrip_repositioned(self, make_sheet):
        """Round-trip read -> write with reordered columns must preserve placement."""
        headers = ["Nombre", "No", "CURP", "NSS", "Salario", "Puesto"]
        wb, ws = make_sheet(headers)
        ws.cell(row=4, column=1, value="Carlos")
        ws.cell(row=4, column=2, value=10)
        ws.cell(row=4, column=3, value="C1")
        ws.cell(row=4, column=4, value="NS1")
        ws.cell(row=4, column=5, value="18000")
        ws.cell(row=4, column=6, value="Analista")

        workers, col_map = read_workers_from_sheet(ws)
        assert len(workers) == 1
        w = workers[0]
        assert w.nombre == "Carlos"
        assert w.no == 10
        assert w.salario == "18000"
        assert w.puesto == "Analista"

        wb2, ws2 = make_sheet(headers)
        write_workers_to_sheet(ws2, workers, column_map=col_map)
        ws2 = ws2
        assert ws2.cell(row=4, column=1).value == "Carlos"
        assert ws2.cell(row=4, column=2).value == 10
        assert ws2.cell(row=4, column=5).value == "18000"
        assert ws2.cell(row=4, column=6).value == "Analista"

    def test_extra_field_roundtrip(self, make_sheet):
        headers = ["No", "Nombre", "CURP", "NSS", "Teléfono"]
        wb, ws = make_sheet(headers)
        ws.cell(row=4, column=1, value=1)
        ws.cell(row=4, column=2, value="Maria")
        ws.cell(row=4, column=3, value="M1")
        ws.cell(row=4, column=4, value="NS1")
        ws.cell(row=4, column=5, value="555-1234")

        workers, col_map = read_workers_from_sheet(ws)
        assert "extra:telefono" in col_map
        assert workers[0].extra_fields.get("extra:telefono") == "555-1234"

        # Write it back
        wb2, ws2 = make_sheet(headers)
        write_workers_to_sheet(ws2, workers, column_map=col_map)
        assert ws2.cell(row=4, column=5).value == "555-1234"


class TestMergeColumnMaps:
    def test_base_preferred_for_core(self):
        base = {"nombre": 2, "salario": 7}
        updated = {"nombre": 3, "salario": 8, "extra:telefono": 30}
        merged = merge_column_maps(base, updated)
        assert merged["nombre"] == 2
        assert merged["salario"] == 7
        assert merged["extra:telefono"] == 30

    def test_updated_extra_added(self):
        base = {"nombre": 2}
        updated = {"extra:nuevo": 40}
        merged = merge_column_maps(base, updated)
        assert merged["extra:nuevo"] == 40
