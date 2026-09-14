"""PySide6 main application for Audit Merge Tool."""

import datetime
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from audit_merge.diff.merge import (
    apply_auto_merge,
    apply_conflict_resolution,
    build_merged_workers,
    compute_stats,
    diff_workers,
    match_workers,
)
from audit_merge.excel.io import (
    find_revision_sheet,
    load_workbook_preserving,
    merge_column_maps,
    read_workers_from_sheet,
    save_workbook,
    write_workers_to_sheet,
)
from audit_merge.models import DocumentChecklist, MergeStats, WorkerDiff

# ── Worker thread for background processing ─────────────────────────────────

class MergeWorker(QThread):
    """Background thread for merge processing."""
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, base_path: str, updated_path: str, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.updated_path = updated_path

    def run(self):
        try:
            base_wb = load_workbook_preserving(self.base_path)
            base_sheet = find_revision_sheet(base_wb)
            base_workers, base_col_map = read_workers_from_sheet(base_wb[base_sheet])

            updated_wb = load_workbook_preserving(self.updated_path)
            updated_sheet = find_revision_sheet(updated_wb)
            updated_workers, updated_col_map = read_workers_from_sheet(updated_wb[updated_sheet])

            merged_col_map = merge_column_maps(base_col_map, updated_col_map)

            matches = match_workers(base_workers, updated_workers)
            diffs = []
            for _key, (base_w, updated_w) in matches.items():
                diffs.append(diff_workers(base_w, updated_w))

            stats = compute_stats(diffs)

            result = {
                "base_wb": base_wb,
                "base_sheet": base_sheet,
                "base_workers": base_workers,
                "base_col_map": base_col_map,
                "updated_wb": updated_wb,
                "updated_sheet": updated_sheet,
                "updated_workers": updated_workers,
                "updated_col_map": updated_col_map,
                "merged_col_map": merged_col_map,
                "diffs": diffs,
                "stats": stats,
            }
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ── Color palette ────────────────────────────────────────────────────────────

COLORS = {
    "primary": "#1e3a5f",
    "primary_light": "#2d6a9e",
    "surface": "#ffffff",
    "surface_alt": "#f8f9fa",
    "border": "#dee2e6",
    "text": "#1a1a2e",
    "text_secondary": "#4a4a6a",
    "text_muted": "#888899",
    "success": "#2e7d32",
    "success_bg": "#e8f5e9",
    "warning": "#f57c00",
    "warning_bg": "#fff3e0",
    "error": "#c62828",
    "error_bg": "#fce4ec",
    "info": "#0288d1",
    "info_bg": "#e3f2fd",
    "added": "#0288d1",
    "removed": "#c62828",
    "modified": "#6a1b9a",
}


def _stylesheet() -> str:
    return f"""
    QMainWindow, QWidget {{
        background-color: {COLORS['surface']};
        color: {COLORS['text']};
        font-family: 'Segoe UI', 'Noto Sans', sans-serif;
        font-size: 13px;
    }}

    QLabel#title {{
        font-size: 20px;
        font-weight: bold;
        color: {COLORS['primary']};
    }}

    QLabel#subtitle {{
        font-size: 14px;
        color: {COLORS['text_secondary']};
    }}

    QPushButton {{
        background-color: {COLORS['primary']};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 22px;
        font-size: 13px;
        font-weight: bold;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['primary_light']};
    }}
    QPushButton:disabled {{
        background-color: {COLORS['border']};
        color: {COLORS['text_muted']};
    }}

    QPushButton#success {{
        background-color: {COLORS['success']};
    }}
    QPushButton#success:hover {{
        background-color: #1b5e20;
    }}

    QPushButton#warning {{
        background-color: {COLORS['warning']};
    }}
    QPushButton#warning:hover {{
        background-color: #e65100;
    }}

    QPushButton#error {{
        background-color: {COLORS['error']};
    }}
    QPushButton#error:hover {{
        background-color: #b71c1c;
    }}

    QPushButton#secondary {{
        background-color: transparent;
        color: {COLORS['primary']};
        border: 2px solid {COLORS['primary']};
    }}
    QPushButton#secondary:hover {{
        background-color: {COLORS['info_bg']};
    }}

    QFrame#card {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 16px;
    }}

    QFrame#stat_card {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-left: 4px solid {COLORS['primary']};
        border-radius: 8px;
        padding: 14px;
    }}

    QFrame#stat_card_success {{
        border-left-color: {COLORS['success']};
    }}

    QFrame#stat_card_warning {{
        border-left-color: {COLORS['warning']};
    }}

    QFrame#stat_card_error {{
        border-left-color: {COLORS['error']};
    }}

    QLabel#stat_value {{
        font-size: 28px;
        font-weight: bold;
        color: {COLORS['text']};
    }}

    QLabel#stat_label {{
        font-size: 12px;
        color: {COLORS['text_secondary']};
    }}

    QScrollArea {{
        border: none;
        background-color: transparent;
    }}

    QProgressBar {{
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        text-align: center;
        height: 22px;
    }}
    QProgressBar::chunk {{
        background-color: {COLORS['primary']};
        border-radius: 3px;
    }}
    """


# ── Helper widgets ───────────────────────────────────────────────────────────

def _make_stat_card(value: str, label: str, variant: str = "") -> QFrame:
    frame = QFrame()
    frame.setObjectName(f"stat_card{'_' + variant if variant else ''}")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 10, 14, 10)
    val_label = QLabel(value)
    val_label.setObjectName("stat_value")
    val_label.setAlignment(Qt.AlignCenter)
    txt_label = QLabel(label)
    txt_label.setObjectName("stat_label")
    txt_label.setAlignment(Qt.AlignCenter)
    txt_label.setWordWrap(True)
    layout.addWidget(val_label)
    layout.addWidget(txt_label)
    return frame


def _make_diff_badge(change_type: str) -> QLabel:
    colors = {
        "added": (COLORS["added"], COLORS["info_bg"]),
        "removed": (COLORS["removed"], COLORS["error_bg"]),
        "modified": (COLORS["modified"], "#f3e5f5"),
    }
    fg, bg = colors.get(change_type, (COLORS["text_muted"], COLORS["surface_alt"]))
    badge = QLabel(change_type.upper())
    badge.setStyleSheet(f"""
        color: {fg};
        background-color: {bg};
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: bold;
    """)
    badge.setAlignment(Qt.AlignCenter)
    return badge


# ── File selection screen ────────────────────────────────────────────────────

class FileSelectionScreen(QWidget):
    file_selected = Signal(str, str)  # path, file_type

    def __init__(self, file_type: str, parent=None):
        super().__init__(parent)
        self.file_type = file_type
        self.file_path = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        title = QLabel(f"Seleccionar archivo {self.file_type}")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Formatos soportados: .xlsx, .xls")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Card with file info
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        self.path_label = QLabel("Ningún archivo seleccionado")
        self.path_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 8px;")
        self.path_label.setAlignment(Qt.AlignCenter)
        self.path_label.setWordWrap(True)
        card_layout.addWidget(self.path_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        browse_btn = QPushButton("Examinar...")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._browse)
        btn_layout.addWidget(browse_btn)

        self.confirm_btn = QPushButton("Confirmar")
        self.confirm_btn.setObjectName("success")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(self.confirm_btn)

        card_layout.addLayout(btn_layout)
        layout.addWidget(card)
        layout.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"Seleccionar archivo {self.file_type}",
            "",
            "Archivos Excel (*.xlsx *.xls);;Todos los archivos (*)",
        )
        if path:
            self.file_path = path
            self.path_label.setText(path)
            self.path_label.setStyleSheet(f"color: {COLORS['text']}; padding: 8px;")
            self.confirm_btn.setEnabled(True)

    def _confirm(self):
        if self.file_path:
            self.file_selected.emit(self.file_path, self.file_type)


# ── Stats screen ─────────────────────────────────────────────────────────────

class StatsScreen(QWidget):
    merge_requested = Signal()
    review_requested = Signal()
    save_requested = Signal()
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("Dashboard de Estadísticas")
        header.setObjectName("title")
        layout.addWidget(header)

        # Stats grid
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(12)
        layout.addLayout(self.stats_grid)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.auto_merge_btn = QPushButton("Aplicar Auto-Merge")
        self.auto_merge_btn.setObjectName("success")
        self.auto_merge_btn.clicked.connect(self.merge_requested)
        btn_layout.addWidget(self.auto_merge_btn)

        self.review_btn = QPushButton("Revisar Conflictos")
        self.review_btn.clicked.connect(self.review_requested)
        btn_layout.addWidget(self.review_btn)

        self.save_btn = QPushButton("Guardar Salida")
        self.save_btn.setObjectName("warning")
        self.save_btn.clicked.connect(self.save_requested)
        btn_layout.addWidget(self.save_btn)

        self.back_btn = QPushButton("Volver")
        self.back_btn.setObjectName("secondary")
        self.back_btn.clicked.connect(self.back_requested)
        btn_layout.addWidget(self.back_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def update_stats(self, stats: MergeStats, remaining: int = 0):
        # Clear old cards
        while self.stats_grid.count():
            item = self.stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = [
            (str(stats.total_base), "Trabajadores Base", ""),
            (str(stats.total_updated), "Trabajadores Actualizados", ""),
            (str(stats.auto_mergeable), "Auto-mergeables", "success"),
            (str(stats.conflicts), "Conflictos", "warning" if stats.conflicts > 0 else ""),
            (str(stats.checklist_added_total), "X's Agregados", "success"),
            (str(stats.checklist_removed_total), "X's Eliminados", "error" if stats.checklist_removed_total > 0 else ""),
            (str(stats.data_changed_total), "Campos Modificados", "warning" if stats.data_changed_total > 0 else ""),
            (str(stats.workers_added), "Trabajadores Nuevos", "success" if stats.workers_added > 0 else ""),
            (str(stats.workers_removed), "Trabajadores Eliminados", "error" if stats.workers_removed > 0 else ""),
        ]

        for i, (value, label, variant) in enumerate(cards):
            card = _make_stat_card(value, label, variant)
            self.stats_grid.addWidget(card, i // 3, i % 3)

        self.review_btn.setEnabled(stats.conflicts > 0)
        if remaining > 0:
            self.auto_merge_btn.setText(f"Auto-Merge Pendiente ({remaining})")


# ── Conflict review screen ──────────────────────────────────────────────────

class ConflictReviewScreen(QWidget):
    conflict_resolved = Signal(object, str)  # WorkerDiff, choice ("base"|"updated"|"manual")
    done_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conflicts = []
        self.current_index = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header
        self.header_label = QLabel()
        self.header_label.setObjectName("title")
        layout.addWidget(self.header_label)

        # Diff details (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.diff_container = QWidget()
        self.diff_layout = QVBoxLayout(self.diff_container)
        self.diff_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.diff_container)
        layout.addWidget(scroll, stretch=1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.prev_btn = QPushButton("Anterior")
        self.prev_btn.setObjectName("secondary")
        self.prev_btn.clicked.connect(self._prev)
        btn_layout.addWidget(self.prev_btn)

        self.keep_base_btn = QPushButton("Mantener Base")
        self.keep_base_btn.setObjectName("success")
        self.keep_base_btn.clicked.connect(lambda: self._resolve("base"))
        btn_layout.addWidget(self.keep_base_btn)

        self.use_updated_btn = QPushButton("Usar Actualizado")
        self.use_updated_btn.clicked.connect(lambda: self._resolve("updated"))
        btn_layout.addWidget(self.use_updated_btn)

        self.manual_btn = QPushButton("Edicion Manual")
        self.manual_btn.setObjectName("warning")
        self.manual_btn.clicked.connect(lambda: self._resolve("manual"))
        btn_layout.addWidget(self.manual_btn)

        self.next_btn = QPushButton("Siguiente")
        self.next_btn.setObjectName("secondary")
        self.next_btn.clicked.connect(self._next)
        btn_layout.addWidget(self.next_btn)

        self.done_btn = QPushButton("Listo")
        self.done_btn.setObjectName("error")
        self.done_btn.clicked.connect(self.done_signal)
        btn_layout.addWidget(self.done_btn)

        layout.addLayout(btn_layout)

    def set_conflicts(self, conflicts: list):
        self.conflicts = conflicts
        self.current_index = 0
        if conflicts:
            self._update_display()

    def _update_display(self):
        if not self.conflicts:
            return

        diff = self.conflicts[self.current_index]
        base = diff.base_worker
        updated = diff.updated_worker

        # Header
        if base:
            self.header_label.setText(
                f"Conflicto {self.current_index + 1}/{len(self.conflicts)}: "
                f"#{base.no} {base.nombre}"
            )
        elif updated:
            self.header_label.setText(
                f"Conflicto {self.current_index + 1}/{len(self.conflicts)}: "
                f"#{updated.no} {updated.nombre} (NUEVO)"
            )

        # Clear old diff rows
        while self.diff_layout.count():
            item = self.diff_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Build diff rows
        for fd in diff.field_diffs:
            row = QFrame()
            row.setObjectName("card")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 6, 10, 6)

            field_label = QLabel(fd.field_name)
            field_label.setFixedWidth(180)
            field_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_secondary']};")
            row_layout.addWidget(field_label)

            base_val = QLabel(fd.base_value or "—")
            base_val.setStyleSheet(f"""
                background-color: {COLORS['error_bg']};
                border: 1px solid #ef9a9a;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 150px;
            """)
            row_layout.addWidget(base_val)

            updated_val = QLabel(fd.updated_value or "—")
            updated_val.setStyleSheet(f"""
                background-color: {COLORS['success_bg']};
                border: 1px solid #a5d6a7;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 150px;
            """)
            row_layout.addWidget(updated_val)

            badge = _make_diff_badge(fd.change_type.value)
            row_layout.addWidget(badge)

            self.diff_layout.addWidget(row)

        # Navigation state
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.conflicts) - 1)

    def _resolve(self, choice: str):
        if not self.conflicts:
            return
        diff = self.conflicts[self.current_index]
        self.conflict_resolved.emit(diff, choice)
        if choice != "manual":
            self._next()

    def _next(self):
        if self.current_index < len(self.conflicts) - 1:
            self.current_index += 1
            self._update_display()

    def _prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._update_display()


# ── Manual edit dialog ──────────────────────────────────────────────────────

class ManualEditDialog(QMessageBox):
    """Simple manual edit using input dialog per field."""
    pass


# ── Main window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audit Merge Tool")
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)

        # State
        self.base_path = ""
        self.updated_path = ""
        self.base_wb = None
        self.updated_wb = None
        self.base_workers = []
        self.updated_workers = []
        self.base_col_map = {}
        self.updated_col_map = {}
        self.merged_col_map = {}
        self.diffs = []
        self.stats = None
        self.merged_workers = {}
        self.resolutions = {}
        self.worker = None

        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(_stylesheet())

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = QFrame()
        title_bar.setStyleSheet(f"""
            background-color: {COLORS['primary']};
            padding: 12px 20px;
        """)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(20, 10, 20, 10)

        app_title = QLabel("Audit Merge Tool")
        app_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        title_bar_layout.addWidget(app_title)
        title_bar_layout.addStretch()

        self.status_label = QLabel("Listo")
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px;")
        title_bar_layout.addWidget(self.status_label)

        main_layout.addWidget(title_bar)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(3)
        self.progress.setVisible(False)
        main_layout.addWidget(self.progress)

        # Stacked screens
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Screens
        self.file_base_screen = FileSelectionScreen("base")
        self.file_updated_screen = FileSelectionScreen("actualizado")
        self.stats_screen = StatsScreen()
        self.conflict_screen = ConflictReviewScreen()

        self.stack.addWidget(self.file_base_screen)
        self.stack.addWidget(self.file_updated_screen)
        self.stack.addWidget(self.stats_screen)
        self.stack.addWidget(self.conflict_screen)

        # Connections
        self.file_base_screen.file_selected.connect(self._on_base_selected)
        self.file_updated_screen.file_selected.connect(self._on_updated_selected)
        self.stats_screen.merge_requested.connect(self._on_auto_merge)
        self.stats_screen.review_requested.connect(self._on_review_conflicts)
        self.stats_screen.save_requested.connect(self._on_save)
        self.stats_screen.back_requested.connect(self._on_back)
        self.conflict_screen.conflict_resolved.connect(self._on_conflict_resolved)
        self.conflict_screen.done_signal.connect(self._on_conflict_done)

        self.stack.setCurrentIndex(0)

    def _show_progress(self, msg: str):
        self.status_label.setText(msg)
        self.progress.setVisible(True)

    def _hide_progress(self):
        self.progress.setVisible(False)

    @Slot(str, str)
    def _on_base_selected(self, path: str, file_type: str):
        self.base_path = path
        self.status_label.setText("Procesando archivo base...")
        self._show_progress("Cargando archivo base...")

        self.worker = MergeWorker(path, path)
        self.worker.finished.connect(self._on_base_loaded)
        self.worker.error.connect(self._on_load_error)
        self.worker.start()

    def _on_base_loaded(self, result):
        self.base_wb = result["base_wb"]
        self.base_workers = result["base_workers"]
        self.base_col_map = result["base_col_map"]
        self._hide_progress()
        self.status_label.setText(f"Base: {len(self.base_workers)} trabajadores")
        self.stack.setCurrentIndex(1)

    @Slot(str, str)
    def _on_updated_selected(self, path: str, file_type: str):
        self.updated_path = path
        self._show_progress("Cargando y procesando...")

        self.worker = MergeWorker(self.base_path, path)
        self.worker.finished.connect(self._on_process_complete)
        self.worker.error.connect(self._on_load_error)
        self.worker.start()

    def _on_process_complete(self, result):
        self.base_wb = result["base_wb"]
        self.base_workers = result["base_workers"]
        self.base_col_map = result["base_col_map"]
        self.updated_wb = result["updated_wb"]
        self.updated_workers = result["updated_workers"]
        self.updated_col_map = result["updated_col_map"]
        self.merged_col_map = result["merged_col_map"]
        self.diffs = result["diffs"]
        self.stats = result["stats"]

        self._hide_progress()
        self.stats_screen.update_stats(self.stats)
        self.stack.setCurrentIndex(2)
        self.status_label.setText(
            f"Procesado: {self.stats.auto_mergeable} auto, {self.stats.conflicts} conflictos"
        )

    def _on_load_error(self, msg):
        self._hide_progress()
        QMessageBox.critical(self, "Error", f"Error cargando archivo:\n{msg}")
        self.status_label.setText("Error")

    def _on_auto_merge(self):
        count = 0
        for diff in self.diffs:
            if diff.is_auto_mergeable and diff.base_worker and diff.updated_worker:
                merged = apply_auto_merge(diff.base_worker, diff.updated_worker)
                self.merged_workers[diff.worker_key] = merged
                count += 1

        remaining = len([d for d in self.diffs if d.worker_key not in self.merged_workers])
        remaining_conflicts = len([d for d in self.diffs if d.has_conflicts and d.worker_key not in self.merged_workers])

        recompute = [d for d in self.diffs if d.worker_key not in self.merged_workers]
        self.stats = compute_stats(recompute) if recompute else MergeStats()

        self.stats_screen.update_stats(self.stats, remaining)
        QMessageBox.information(
            self, "Auto-Merge",
            f"Auto-merge aplicado a {count} trabajadores.\n"
            f"Quedan {remaining_conflicts} conflictos por revisar."
        )
        self.status_label.setText(f"Auto-merge: {count} aplicados, {remaining_conflicts} conflictos pendientes")

    def _on_review_conflicts(self):
        conflicts = [
            d for d in self.diffs
            if d.has_conflicts and d.worker_key not in self.merged_workers
        ]
        if not conflicts:
            QMessageBox.information(self, "Sin conflictos", "No hay conflictos pendientes.")
            return
        self.conflict_screen.set_conflicts(conflicts)
        self.stack.setCurrentIndex(3)

    def _on_conflict_resolved(self, diff: WorkerDiff, choice: str):
        if choice == "manual":
            # Show input dialogs for each field
            from PySide6.QtWidgets import QInputDialog
            base = diff.base_worker
            updated = diff.updated_worker
            resolution = {}

            all_fields = [
                ("nombre", "Nombre"), ("curp", "CURP"), ("nss", "NSS"),
                ("depto", "Depto"), ("puesto", "Puesto"), ("salario", "Salario"),
                ("fecha_reingreso", "Fecha Reingreso"), ("fecha_baja", "Fecha Baja"),
                ("fecha_baja_2", "Fecha Baja 2"), ("fecha_baja_3", "Fecha Baja 3"),
            ]
            # Add checklist fields
            for f in DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS:
                all_fields.append((f, f.replace("_", " ").title()))

            for field_name, label in all_fields:
                base_val = ""
                updated_val = ""
                if base and hasattr(base, field_name):
                    base_val = getattr(base, field_name) or ""
                elif base and hasattr(base.checklist, field_name):
                    base_val = getattr(base.checklist, field_name) or ""
                if updated and hasattr(updated, field_name):
                    updated_val = getattr(updated, field_name) or ""
                elif updated and hasattr(updated.checklist, field_name):
                    updated_val = getattr(updated.checklist, field_name) or ""

                default = updated_val if updated_val else base_val
                val, ok = QInputDialog.getText(
                    self, f"Editar {label}",
                    f"{label}\nBase: {base_val}\nActualizado: {updated_val}",
                    text=default,
                )
                if ok:
                    resolution[field_name] = val
                else:
                    resolution[field_name] = default

            # Add extra fields
            base_extra = base.extra_fields if base else {}
            updated_extra = updated.extra_fields if updated else {}
            for key in set(base_extra.keys()) | set(updated_extra.keys()):
                if key not in resolution:
                    bv = base_extra.get(key, "")
                    uv = updated_extra.get(key, "")
                    val, ok = QInputDialog.getText(
                        self, f"Editar {key}",
                        f"{key}\nBase: {bv}\nActualizado: {uv}",
                        text=uv if uv else bv,
                    )
                    resolution[key] = val if ok else (uv if uv else bv)

        elif choice == "base":
            base = diff.base_worker
            resolution = {f: getattr(base.checklist, f) for f in
                         DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS}
            resolution.update({
                "nombre": base.nombre, "curp": base.curp, "nss": base.nss,
                "depto": base.depto, "puesto": base.puesto, "salario": base.salario,
                "fecha_reingreso": base.fecha_reingreso, "fecha_baja": base.fecha_baja,
                "fecha_baja_2": base.fecha_baja_2, "fecha_baja_3": base.fecha_baja_3,
            })
        elif choice == "updated":
            updated = diff.updated_worker
            resolution = {f: getattr(updated.checklist, f) for f in
                         DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS}
            resolution.update({
                "nombre": updated.nombre, "curp": updated.curp, "nss": updated.nss,
                "depto": updated.depto, "puesto": updated.puesto, "salario": updated.salario,
                "fecha_reingreso": updated.fecha_reingreso, "fecha_baja": updated.fecha_baja,
                "fecha_baja_2": updated.fecha_baja_2, "fecha_baja_3": updated.fecha_baja_3,
            })
            # Include extra fields from updated
            for key, val in (updated.extra_fields or {}).items():
                resolution[key] = val

        self.resolutions[diff.worker_key] = resolution
        if diff.base_worker and diff.updated_worker:
            merged = apply_conflict_resolution(diff.base_worker, diff.updated_worker, resolution)
            self.merged_workers[diff.worker_key] = merged
        elif diff.updated_worker:
            self.merged_workers[diff.worker_key] = diff.updated_worker

    def _on_conflict_done(self):
        remaining = len([d for d in self.diffs if d.has_conflicts and d.worker_key not in self.merged_workers])
        recompute = [d for d in self.diffs if d.worker_key not in self.merged_workers]
        self.stats = compute_stats(recompute) if recompute else MergeStats()
        self.stats_screen.update_stats(self.stats, remaining)
        self.stack.setCurrentIndex(2)
        self.status_label.setText(f"Conflictos: {remaining} pendientes")

    def _on_save(self):
        if not self.base_wb:
            QMessageBox.warning(self, "Sin datos", "Primero carga los archivos.")
            return

        default_name = f"{Path(self.base_path).stem}_Merged_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar archivo fusionado",
            str(Path(self.base_path).parent / default_name),
            "Archivos Excel (*.xlsx)",
        )
        if not path:
            return

        self._show_progress("Guardando...")

        try:
            wb = load_workbook_preserving(self.base_path)
            sheet_name = find_revision_sheet(wb)
            ws = wb[sheet_name]

            sorted_workers = build_merged_workers(
                self.base_workers,
                self.updated_workers,
                self.merged_workers,
                self.diffs,
                self.resolutions,
            )
            write_workers_to_sheet(ws, sorted_workers, column_map=self.merged_col_map)
            save_workbook(wb, path)

            self._hide_progress()
            QMessageBox.information(self, "Guardado", f"Archivo guardado en:\n{path}")
            self.status_label.setText(f"Guardado: {Path(path).name}")
        except Exception as e:
            self._hide_progress()
            QMessageBox.critical(self, "Error", f"Error guardando:\n{e}")

    def _on_back(self):
        self.stack.setCurrentIndex(0)


def main():
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
