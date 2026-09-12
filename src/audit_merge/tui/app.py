from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Button, Static, DataTable, 
    Input, Label, Select, RadioSet, RadioButton, 
    RichLog, ProgressBar, Tabs, TabPane
)
from textual.screen import Screen
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Group
import datetime
import os
from pathlib import Path

from src.audit_merge.models import Worker, WorkerDiff, MergeStats, FieldDiff, ChangeType, DocumentChecklist
from src.audit_merge.excel.io import load_workbook_preserving, save_workbook, read_workers_from_sheet, write_workers_to_sheet, find_revision_sheet
from src.audit_merge.diff.merge import match_workers, diff_workers, compute_stats, apply_auto_merge, apply_conflict_resolution


class FileSelected(Message):
    def __init__(self, path: str, file_type: str):
        self.path = path
        self.file_type = file_type
        super().__init__()


class FilePickerScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    
    def __init__(self, file_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_type = file_type
        self.selected_path = ""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(f"Select {self.file_type} File", classes="title"),
            Input(placeholder="Enter file path or browse...", id="file_input"),
            Button("Browse", id="browse_btn", variant="primary"),
            Button("Confirm", id="confirm_btn", variant="success", disabled=True),
            Button("Cancel", id="cancel_btn", variant="error"),
            id="file_picker_container"
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "browse_btn":
            self.action_browse()
        elif event.button.id == "confirm_btn":
            self.post_message(FileSelected(self.selected_path, self.file_type))
            self.app.pop_screen()
        elif event.button.id == "cancel_btn":
            self.app.pop_screen()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        path = event.value.strip()
        self.selected_path = path
        confirm_btn = self.query_one("#confirm_btn", Button)
        confirm_btn.disabled = not (path and os.path.exists(path))
    
    def action_browse(self) -> None:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            path = filedialog.askopenfilename(
                title=f"Select {self.file_type} Excel File",
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
            )
            root.destroy()
            if path:
                self.selected_path = path
                input_widget = self.query_one("#file_input", Input)
                input_widget.value = path
                confirm_btn = self.query_one("#confirm_btn", Button)
                confirm_btn.disabled = False
        except ModuleNotFoundError:
            self.notify("tkinter not available - please type path manually", severity="warning")
    
    def action_cancel(self) -> None:
        self.app.pop_screen()


class StatsScreen(Screen):
    BINDINGS = [
        Binding("a", "apply_auto", "Apply Auto-Merge"),
        Binding("r", "review", "Review Conflicts"),
        Binding("s", "save", "Save Output"),
        Binding("escape", "back", "Back"),
    ]
    
    def __init__(self, stats: MergeStats, diffs: list[WorkerDiff], base_workers: list[Worker], 
                 updated_workers: list[Worker], base_wb, updated_wb, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = stats
        self.diffs = diffs
        self.base_workers = base_workers
        self.updated_workers = updated_workers
        self.base_wb = base_wb
        self.updated_wb = updated_wb
        self.merged_workers = {}
        self.resolutions = {}
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(self._build_stats_text(), id="stats_display", classes="stats"),
            Horizontal(
                Button("Apply Auto-Merge (A)", id="apply_auto", variant="success"),
                Button("Review Conflicts (R)", id="review_conflicts", variant="primary"),
                Button("Save Output (S)", id="save_output", variant="warning"),
                Button("Back (Esc)", id="back", variant="error"),
                id="action_buttons"
            ),
            id="stats_container"
        )
        yield Footer()
    
    def _build_stats_text(self) -> str:
        lines = [
            f"Base file workers:     {self.stats.total_base}",
            f"Updated file workers:  {self.stats.total_updated}",
            "",
            f"✓ Auto-mergeable:      {self.stats.auto_mergeable}",
            f"⚠ Conflicts to review: {self.stats.conflicts}",
            "",
            f"  X's added:           {self.stats.checklist_added_total}",
            f"  X's removed:         {self.stats.checklist_removed_total}",
            f"  Data fields changed: {self.stats.data_changed_total}",
            f"  Workers added:       {self.stats.workers_added}",
            f"  Workers removed:     {self.stats.workers_removed}",
        ]
        return "\n".join(lines)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply_auto":
            self.action_apply_auto()
        elif event.button.id == "review_conflicts":
            self.action_review()
        elif event.button.id == "save_output":
            self.action_save()
        elif event.button.id == "back":
            self.action_back()
    
    def action_apply_auto(self) -> None:
        auto_count = 0
        for diff in self.diffs:
            if diff.is_auto_mergeable and diff.base_worker and diff.updated_worker:
                merged = apply_auto_merge(diff.base_worker, diff.updated_worker)
                self.merged_workers[diff.worker_key] = merged
                auto_count += 1
        
        self.notify(f"Applied auto-merge to {auto_count} workers")
        self._refresh_stats()
    
    def action_review(self) -> None:
        conflict_diffs = [d for d in self.diffs if d.has_conflicts]
        if not conflict_diffs:
            self.notify("No conflicts to review")
            return
        self.app.push_screen(ConflictReviewScreen(conflict_diffs, self))
    
    def action_save(self) -> None:
        self._build_final_workbook()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(self.app.base_path).stem
        output_name = f"{base_name}_Merged_{timestamp}.xlsx"
        output_path = Path(self.app.base_path).parent / output_name
        save_workbook(self.base_wb, str(output_path))
        self.notify(f"Saved to {output_path}")
    
    def action_back(self) -> None:
        self.app.pop_screen()
    
    def _refresh_stats(self) -> None:
        remaining_diffs = [d for d in self.diffs if d.worker_key not in self.merged_workers]
        self.stats = compute_stats(remaining_diffs)
        self.query_one("#stats_display", Static).update(self._build_stats_text())
    
    def _build_final_workbook(self) -> None:
        revision_sheet_name = find_revision_sheet(self.base_wb)
        ws = self.base_wb[revision_sheet_name]
        
        all_workers = {}
        for w in self.base_workers:
            all_workers[w.key] = w
        for w in self.updated_workers:
            all_workers[w.key] = w
        
        for diff in self.diffs:
            if diff.worker_key in self.merged_workers:
                all_workers[diff.worker_key] = self.merged_workers[diff.worker_key]
            elif diff.worker_key in self.resolutions:
                base_w = diff.base_worker
                updated_w = diff.updated_worker
                if base_w and updated_w:
                    merged = apply_conflict_resolution(base_w, updated_w, self.resolutions[diff.worker_key])
                    all_workers[diff.worker_key] = merged
                elif updated_w:
                    all_workers[diff.worker_key] = updated_w
        
        sorted_workers = sorted(all_workers.values(), key=lambda w: (w.no or 0, w.nombre))
        write_workers_to_sheet(ws, sorted_workers)


class ConflictReviewScreen(Screen):
    BINDINGS = [
        Binding("n", "next", "Next"),
        Binding("p", "previous", "Previous"),
        Binding("k", "keep_base", "Keep Base"),
        Binding("u", "use_updated", "Use Updated"),
        Binding("m", "manual", "Manual Edit"),
        Binding("escape", "done", "Done"),
    ]
    
    def __init__(self, conflict_diffs: list[WorkerDiff], parent_screen: StatsScreen, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conflict_diffs = conflict_diffs
        self.parent_screen = parent_screen
        self.current_index = 0
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("", id="conflict_header", classes="conflict-header"),
            ScrollableContainer(
                Static("", id="conflict_details", classes="conflict-details"),
                id="conflict_scroll"
            ),
            Horizontal(
                Button("Keep Base (K)", id="keep_base", variant="success"),
                Button("Use Updated (U)", id="use_updated", variant="primary"),
                Button("Manual (M)", id="manual", variant="warning"),
                Button("Previous (P)", id="prev", variant="default"),
                Button("Next (N)", id="next", variant="default"),
                Button("Done (Esc)", id="done", variant="error"),
                id="conflict_actions"
            ),
            id="conflict_container"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        self._update_display()
    
    def _update_display(self) -> None:
        diff = self.conflict_diffs[self.current_index]
        base = diff.base_worker
        updated = diff.updated_worker
        
        header_text = f"Conflict {self.current_index + 1}/{len(self.conflict_diffs)}: "
        if base:
            header_text += f"#{base.no} {base.nombre}"
        elif updated:
            header_text += f"#{updated.no} {updated.nombre} (NEW)"
        
        self.query_one("#conflict_header", Static).update(header_text)
        
        details = []
        if base is None:
            details.append("NEW WORKER in updated file")
            details.append(f"Name: {updated.nombre}")
            details.append(f"CURP: {updated.curp}")
            details.append(f"NSS: {updated.nss}")
        elif updated is None:
            details.append("WORKER REMOVED from updated file")
            details.append(f"Name: {base.nombre}")
            details.append(f"CURP: {base.curp}")
            details.append(f"NSS: {base.nss}")
        else:
            for field_diff in diff.field_diffs:
                if field_diff.change_type == ChangeType.ADDED:
                    details.append(f"[green]+ {field_diff.field_name}: '{field_diff.updated_value}'[/green]")
                elif field_diff.change_type == ChangeType.REMOVED:
                    details.append(f"[red]- {field_diff.field_name}: '{field_diff.base_value}'[/red]")
                elif field_diff.change_type == ChangeType.MODIFIED:
                    details.append(f"[yellow]~ {field_diff.field_name}: '{field_diff.base_value}' → '{field_diff.updated_value}'[/yellow]")
        
        self.query_one("#conflict_details", Static).update("\n".join(details))
        
        prev_btn = self.query_one("#prev", Button)
        next_btn = self.query_one("#next", Button)
        prev_btn.disabled = self.current_index == 0
        next_btn.disabled = self.current_index == len(self.conflict_diffs) - 1
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        diff = self.conflict_diffs[self.current_index]
        
        if event.button.id == "keep_base":
            self._resolve_conflict(diff, "base")
        elif event.button.id == "use_updated":
            self._resolve_conflict(diff, "updated")
        elif event.button.id == "manual":
            self._resolve_conflict(diff, "manual")
        elif event.button.id == "prev":
            self.action_previous()
        elif event.button.id == "next":
            self.action_next()
        elif event.button.id == "done":
            self.action_done()
    
    def _resolve_conflict(self, diff: WorkerDiff, choice: str) -> None:
        base = diff.base_worker
        updated = diff.updated_worker
        resolution = {}
        
        if base is None:
            resolution = {f: getattr(updated.checklist, f) for f in 
                         DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS}
            resolution.update({
                "nombre": updated.nombre, "curp": updated.curp, "nss": updated.nss,
                "depto": updated.depto, "puesto": updated.puesto, "salario": updated.salario,
                "fecha_reingreso": updated.fecha_reingreso, "fecha_baja": updated.fecha_baja,
                "fecha_baja_2": updated.fecha_baja_2, "fecha_baja_3": updated.fecha_baja_3,
            })
        elif updated is None:
            resolution = {f: getattr(base.checklist, f) for f in 
                         DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS}
            resolution.update({
                "nombre": base.nombre, "curp": base.curp, "nss": base.nss,
                "depto": base.depto, "puesto": base.puesto, "salario": base.salario,
                "fecha_reingreso": base.fecha_reingreso, "fecha_baja": base.fecha_baja,
                "fecha_baja_2": base.fecha_baja_2, "fecha_baja_3": base.fecha_baja_3,
            })
        else:
            if choice == "base":
                resolution = {f: getattr(base.checklist, f) for f in 
                             DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS}
                resolution.update({
                    "nombre": base.nombre, "curp": base.curp, "nss": base.nss,
                    "depto": base.depto, "puesto": base.puesto, "salario": base.salario,
                    "fecha_reingreso": base.fecha_reingreso, "fecha_baja": base.fecha_baja,
                    "fecha_baja_2": base.fecha_baja_2, "fecha_baja_3": base.fecha_baja_3,
                })
            elif choice == "updated":
                resolution = {f: getattr(updated.checklist, f) for f in 
                             DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS}
                resolution.update({
                    "nombre": updated.nombre, "curp": updated.curp, "nss": updated.nss,
                    "depto": updated.depto, "puesto": updated.puesto, "salario": updated.salario,
                    "fecha_reingreso": updated.fecha_reingreso, "fecha_baja": updated.fecha_baja,
                    "fecha_baja_2": updated.fecha_baja_2, "fecha_baja_3": updated.fecha_baja_3,
                })
            elif choice == "manual":
                self.app.push_screen(ManualEditScreen(diff, self))
                return
        
        self.parent_screen.resolutions[diff.worker_key] = resolution
        self.parent_screen.merged_workers[diff.worker_key] = apply_conflict_resolution(base, updated, resolution)
        self.action_next()
    
    def action_next(self) -> None:
        if self.current_index < len(self.conflict_diffs) - 1:
            self.current_index += 1
            self._update_display()
    
    def action_previous(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self._update_display()
    
    def action_done(self) -> None:
        self.app.pop_screen()


class ManualEditScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]
    
    def __init__(self, diff: WorkerDiff, parent_screen: ConflictReviewScreen, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diff = diff
        self.parent_screen = parent_screen
        self.inputs = {}
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(f"Manual Edit: {self.diff.base_worker.nombre if self.diff.base_worker else 'NEW'}", classes="title"),
            ScrollableContainer(
                *self._build_input_fields(),
                id="manual_inputs"
            ),
            Horizontal(
                Button("Save", id="save", variant="success"),
                Button("Cancel", id="cancel", variant="error"),
                id="manual_actions"
            ),
            id="manual_container"
        )
        yield Footer()
    
    def _build_input_fields(self):
        fields = []
        base = self.diff.base_worker
        updated = self.diff.updated_worker
        
        all_fields = [
            ("nombre", "Nombre"), ("curp", "CURP"), ("nss", "NSS"),
            ("depto", "Departamento"), ("puesto", "Puesto"), ("salario", "Salario"),
            ("fecha_reingreso", "Fecha Reingreso"), ("fecha_baja", "Fecha Baja"),
            ("fecha_baja_2", "Fecha Baja 2"), ("fecha_baja_3", "Fecha Baja 3"),
        ] + [(f, f.replace("_", " ").title()) for f in 
             DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS]
        
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
            
            default_val = updated_val if updated_val else base_val
            inp = Input(value=default_val, placeholder=f"Base: {base_val} | Updated: {updated_val}", id=f"input_{field_name}")
            self.inputs[field_name] = inp
            fields.append(Label(label))
            fields.append(inp)
        
        return fields
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            resolution = {k: v.value for k, v in self.inputs.items()}
            self.parent_screen.parent_screen.resolutions[self.diff.worker_key] = resolution
            base = self.diff.base_worker
            updated = self.diff.updated_worker
            if base and updated:
                merged = apply_conflict_resolution(base, updated, resolution)
                self.parent_screen.parent_screen.merged_workers[self.diff.worker_key] = merged
            self.app.pop_screen()
        elif event.button.id == "cancel":
            self.app.pop_screen()
    
    def action_cancel(self) -> None:
        self.app.pop_screen()


class AuditMergeApp(App):
    CSS = """
    /* ============================================================
       SIMPLE DESIGN SYSTEM - Textual compatible only
       ============================================================ */
    
    Screen {
        background: #ffffff;
        color: #1a1a2e;
    }
    
    Header {
        background: #1e3a5f;
        color: #ffffff;
        height: 3;
        padding: 0 3;
    }
    
    Header:focus {
        background: #2d6a9e;
    }
    
    Footer {
        background: #f8f9fa;
        color: #4a4a6a;
        border-top: solid #dee2e6;
        height: 2;
    }
    
    /* Containers */
    .screen-container {
        width: 100%;
        height: 100%;
        padding: 4;
        layout: vertical;
    }
    
    .content-area {
        width: 100%;
        height: 1fr;
        overflow: auto;
    }
    
    .centered {
        align: center middle;
        width: 100%;
    }
    
    .stats-grid {
        layout: grid;
        grid-size: 4 1;
        grid-gutter: 3;
        width: 100%;
        height: auto;
        margin-bottom: 4;
    }
    
    .split-view {
        layout: horizontal;
        width: 100%;
        height: 1fr;
    }
    
    .split-pane {
        width: 1fr;
        height: 1fr;
        overflow: auto;
    }
    
    .split-divider {
        width: 1;
        background: #dee2e6;
        margin: 0 2;
    }
    
    /* Cards & Panels */
    .card {
        background: #ffffff;
        border: solid #dee2e6;
        padding: 3;
        margin: 2 0;
    }
    
    .card:hover {
        border: solid #2d6a9e;
    }
    
    .card-elevated {
        background: #f8f9fa;
        border: solid #dee2e6;
        padding: 4;
        margin: 3 0;
    }
    
    .card-section {
        background: #f8f9fa;
        border: solid #dee2e6;
        padding: 3;
        margin: 2 0;
    }
    
    .panel {
        background: #ffffff;
        border: solid #dee2e6;
        padding: 4;
    }
    
    .panel-header {
        text-style: bold;
        color: #1e3a5f;
        margin-bottom: 3;
        padding-bottom: 2;
        border-bottom: solid #dee2e6;
    }
    
    .panel-section {
        background: #f8f9fa;
        border: solid #dee2e6;
        padding: 3;
        margin: 2 0;
    }
    
    /* Stat Cards */
    .stat-card {
        background: #ffffff;
        border: solid #dee2e6;
        padding: 4;
        min-width: 22;
        min-height: 10;
        layout: vertical;
        align: center middle;
    }
    
    .stat-card-primary {
        border: solid #1e3a5f;
        border-left: thick #1e3a5f;
    }
    
    .stat-card-success {
        border: solid #2e7d32;
        border-left: thick #2e7d32;
    }
    
    .stat-card-warning {
        border: solid #f57c00;
        border-left: thick #f57c00;
    }
    
    .stat-card-error {
        border: solid #c62828;
        border-left: thick #c62828;
    }
    
    .stat-icon {
        margin-bottom: 1;
        height: auto;
    }
    
    .stat-value {
        text-style: bold;
        color: #1a1a2e;
        margin-bottom: 1;
        height: auto;
    }
    
    .stat-label {
        color: #4a4a6a;
        text-align: center;
        width: 100%;
        height: auto;
    }
    
    /* Buttons */
    Button {
        margin: 0 1;
        min-width: 16;
        height: 3;
        text-style: bold;
    }
    
    Button.primary {
        background: #1e3a5f;
        color: #ffffff;
        border: solid #1e3a5f;
    }
    
    Button.primary:hover {
        background: #2d6a9e;
        border: solid #2d6a9e;
    }
    
    Button.primary:focus {
        background: #1e3a5f;
        border: thick #00b4d8;
    }
    
    Button.secondary {
        background: #ffffff;
        color: #1e3a5f;
        border: solid #1e3a5f;
    }
    
    Button.secondary:hover {
        background: #eef1f5;
    }
    
    Button.success {
        background: #2e7d32;
        color: #ffffff;
        border: solid #2e7d32;
    }
    
    Button.success:hover {
        background: #1b5e20;
    }
    
    Button.warning {
        background: #f57c00;
        color: #ffffff;
        border: solid #f57c00;
    }
    
    Button.warning:hover {
        background: #e65100;
    }
    
    Button.error {
        background: #c62828;
        color: #ffffff;
        border: solid #c62828;
    }
    
    Button.error:hover {
        background: #b71c1c;
    }
    
    Button.ghost {
        background: transparent;
        color: #4a4a6a;
        border: solid transparent;
    }
    
    Button.ghost:hover {
        background: #eef1f5;
        color: #1a1a2e;
    }
    
    Button:disabled {
        opacity: 0.5;
        background: #f8f9fa !important;
        color: #888899 !important;
        border: solid #dee2e6 !important;
    }
    
    .button-group {
        layout: horizontal;
        width: 100%;
        height: auto;
        padding: 3 0;
    }
    
    .button-group > Button {
        margin: 0 1;
    }
    
    .button-group-primary > Button.primary {
        margin-right: 2;
    }
    
    /* Inputs */
    Input {
        background: #ffffff;
        border: solid #dee2e6;
        color: #1a1a2e;
        padding: 1 2;
        margin: 1 0;
        min-height: 3;
    }
    
    Input:focus {
        border: thick #2d6a9e;
    }
    
    Input.-invalid {
        border: solid #c62828;
    }
    
    Input.-valid {
        border: solid #2e7d32;
    }
    
    /* Badges */
    .badge {
        padding: 0 2;
        text-style: bold;
        height: 2;
        content-align: center middle;
        min-width: 8;
    }
    
    .badge-success {
        background: #e8f5e9;
        color: #2e7d32;
        border: solid #a5d6a7;
    }
    
    .badge-warning {
        background: #fff3e0;
        color: #f57c00;
        border: solid #ffcc80;
    }
    
    .badge-error {
        background: #fce4ec;
        color: #c62828;
        border: solid #ef9a9a;
    }
    
    .badge-info {
        background: #e3f2fd;
        color: #0288d1;
        border: solid #90caf9;
    }
    
    .badge-neutral {
        background: #f8f9fa;
        color: #888899;
        border: solid #dee2e6;
    }
    
    .badge-auto {
        background: #e8f5e9;
        color: #2e7d32;
        border: solid #a5d6a7;
    }
    
    .badge-conflict {
        background: #fff3e0;
        color: #f57c00;
        border: solid #ffcc80;
    }
    
    .badge-removed {
        background: #fce4ec;
        color: #c62828;
        border: solid #ef9a9a;
    }
    
    .badge-added {
        background: #e3f2fd;
        color: #0288d1;
        border: solid #90caf9;
    }
    
    .badge-modified {
        background: #f3e5f5;
        color: #6a1b9a;
        border: solid #ce93d8;
    }
    
    /* Typography */
    .title {
        text-style: bold;
        color: #1e3a5f;
        margin-bottom: 3;
        padding-bottom: 2;
        border-bottom: solid #dee2e6;
    }
    
    .subtitle {
        text-style: bold;
        color: #4a4a6a;
        margin: 3 0 2 0;
    }
    
    .section-title {
        text-style: bold;
        color: #1a1a2e;
        margin: 4 0 2 0;
        padding-bottom: 1;
        border-bottom: solid #dee2e6;
    }
    
    .muted {
        color: #888899;
    }
    
    .text-primary {
        color: #1a1a2e;
    }
    
    .text-secondary {
        color: #4a4a6a;
    }
    
    .text-muted {
        color: #888899;
    }
    
    .text-success {
        color: #2e7d32;
    }
    
    .text-warning {
        color: #f57c00;
    }
    
    .text-error {
        color: #c62828;
    }
    
    .text-info {
        color: #0288d1;
    }
    
    /* Data Table */
    DataTable {
        background: #ffffff;
        border: solid #dee2e6;
    }
    
    DataTable > .datatable--header {
        background: #f8f9fa;
        color: #4a4a6a;
        text-style: bold;
        border-bottom: solid #dee2e6;
    }
    
    DataTable > .datatable--cursor {
        background: #eef1f5 !important;
    }
    
    DataTable > .datatable--row-highlighted {
        background: #eef1f5;
    }
    
    DataTable > .datatable--cell {
        padding: 1 2;
    }
    
    /* Directory Tree */
    DirectoryTree {
        background: #ffffff;
        border: solid #dee2e6;
        padding: 2;
    }
    
    DirectoryTree > .tree--node {
        padding: 1 2;
    }
    
    DirectoryTree > .tree--node--highlighted {
        background: #eef1f5;
    }
    
    DirectoryTree > .tree--node--selected {
        background: #90e0ef;
        color: #001f3f;
    }
    
    /* Checkbox */
    Checkbox {
        margin: 1 0;
        padding: 1;
    }
    
    Checkbox > .checkbox--label {
        color: #1a1a2e;
    }
    
    Checkbox.-checked > .checkbox--label {
        color: #1e3a5f;
        text-style: bold;
    }
    
    /* Collapsible */
    Collapsible {
        border: solid #dee2e6;
        background: #ffffff;
        overflow: hidden;
    }
    
    Collapsible > .collapsible--title {
        background: #f8f9fa;
        padding: 2 3;
        text-style: bold;
        color: #1a1a2e;
        border-bottom: solid #dee2e6;
    }
    
    Collapsible > .collapsible--content {
        padding: 3;
    }
    
    /* Progress Bar */
    ProgressBar {
        background: #f8f9fa;
        border: solid #dee2e6;
        height: 1;
        margin: 2 0;
    }
    
    ProgressBar > .progress-bar--bar {
        background: #1e3a5f;
    }
    
    /* Tabs */
    Tabs {
        background: #f8f9fa;
        border-bottom: solid #dee2e6;
        padding: 0 3;
    }
    
    Tabs > .tabs--tab {
        color: #4a4a6a;
        padding: 2 3;
        margin-right: 1;
    }
    
    Tabs > .tabs--tab.-active {
        background: #ffffff;
        color: #1e3a5f;
        text-style: bold;
        border-bottom: thick #1e3a5f;
        margin-bottom: -1;
    }
    
    Tabs > .tabs--tab:hover {
        color: #1a1a2e;
    }
    
    /* Toast / Notifications */
    .toast {
        background: #ffffff;
        border: solid #dee2e6;
        padding: 3 4;
        margin: 2;
    }
    
    .toast-success {
        border: solid #2e7d32;
        border-left: thick #2e7d32;
    }
    
    .toast-warning {
        border: solid #f57c00;
        border-left: thick #f57c00;
    }
    
    .toast-error {
        border: solid #c62828;
        border-left: thick #c62828;
    }
    
    .toast-info {
        border: solid #0288d1;
        border-left: thick #0288d1;
    }
    
    /* Diff View */
    .diff-row {
        layout: horizontal;
        width: 100%;
        height: auto;
        min-height: 3;
        padding: 1 2;
        border-bottom: solid #dee2e6;
    }
    
    .diff-row:last-child {
        border-bottom: none;
    }
    
    .diff-row.-added {
        background: #e8f5e9;
    }
    
    .diff-row.-removed {
        background: #fce4ec;
    }
    
    .diff-row.-modified {
        background: #fff3e0;
    }
    
    .diff-gutter {
        width: 2;
        background: #f8f9fa;
    }
    
    .diff-field {
        width: 20;
        min-width: 18;
        padding: 1 2;
        text-style: bold;
        color: #4a4a6a;
        content-align-horizontal: right;
    }
    
    .diff-base, .diff-updated {
        width: 1fr;
        min-width: 25;
        padding: 1 2;
    }
    
    .diff-base {
        background: #fce4ec;
        border: solid #ef9a9a;
        border-right: thick #ef9a9a;
    }
    
    .diff-updated {
        background: #e8f5e9;
        border: solid #a5d6a7;
        border-left: thick #a5d6a7;
    }
    
    .diff-unchanged .diff-base,
    .diff-unchanged .diff-updated {
        background: #f5f5f5;
        border: solid #dee2e6;
    }
    
    .diff-badge {
        margin-left: 2;
        
    }
    
    /* Breadcrumb */
    .breadcrumb {
        layout: horizontal;
        height: 3;
        padding: 1 2;
        background: #f8f9fa;
        border-bottom: solid #dee2e6;
        overflow-x: auto;
    }
    
    .breadcrumb-item {
        color: #888899;
        padding: 0 1;
    }
    
    .breadcrumb-item:hover {
        color: #1e3a5f;
        text-style: underline;
    }
    
    .breadcrumb-item.-active {
        color: #1a1a2e;
        text-style: bold;
    }
    
    .breadcrumb-separator {
        color: #888899;
        padding: 0 1;
    }
    
    /* Legacy container IDs */
    #file_picker_container, #stats_container, #conflict_container, #manual_container {
        width: 90%;
        max-width: 140;
        height: auto;
        margin: 4 2 4 2;
        padding: 4;
        background: #ffffff;
        border: solid #dee2e6;
    }
    
    #action_buttons, #conflict_actions, #manual_actions {
        width: 100%;
        height: auto;
        layout: horizontal;
        padding: 3 0;
    }
    
    #action_buttons > Button, #conflict_actions > Button, #manual_actions > Button {
        margin: 0 1;
    }
    
    /* Utility Classes */
    .hidden {
        display: none;
    }
    
    .sr-only {
        width: 0;
        height: 0;
        overflow: hidden;
    }
    
    .flex {
        layout: horizontal;
    }
    
    .flex-vertical {
        layout: vertical;
    }
    
    .flex-1 {
        width: 1fr;
        height: 1fr;
    }
    
    .align-center {
        align: center middle;
    }
    
    .gap-sm {
        margin: 2 0;
    }
    
    .gap-md {
        margin: 3 0;
    }
    
    .gap-lg {
        margin: 4 0;
    }
    
    .p-sm {
        padding: 2;
    }
    
    .p-md {
        padding: 3;
    }
    
    .p-lg {
        padding: 4;
    }
    
    .w-full {
        width: 100%;
    }
    
    .h-full {
        height: 1fr;
    }
    
    .overflow-auto {
        overflow: auto;
    }
    
    .overflow-hidden {
        overflow: hidden;
    }
"""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
    ]
    
    def __init__(self):
        super().__init__()
        self.base_path = ""
        self.updated_path = ""
        self.base_wb = None
        self.updated_wb = None
        self.base_workers = []
        self.updated_workers = []
        self.diffs = []
        self.stats = None
    
    def on_mount(self) -> None:
        self.push_screen(FilePickerScreen("base"))
    
    def on_file_selected(self, event: FileSelected) -> None:
        if event.file_type == "base":
            self.base_path = event.path
            self.base_wb = load_workbook_preserving(event.path)
            sheet_name = find_revision_sheet(self.base_wb)
            self.base_workers = read_workers_from_sheet(self.base_wb[sheet_name])
            self.push_screen(FilePickerScreen("updated"))
        elif event.file_type == "updated":
            self.updated_path = event.path
            self.updated_wb = load_workbook_preserving(event.path)
            sheet_name = find_revision_sheet(self.updated_wb)
            self.updated_workers = read_workers_from_sheet(self.updated_wb[sheet_name])
            self._process_merge()
    
    def _process_merge(self) -> None:
        matches = match_workers(self.base_workers, self.updated_workers)
        self.diffs = []
        for key, (base_w, updated_w) in matches.items():
            diff = diff_workers(base_w, updated_w)
            self.diffs.append(diff)
        
        self.stats = compute_stats(self.diffs)
        self.push_screen(StatsScreen(self.stats, self.diffs, self.base_workers, 
                                     self.updated_workers, self.base_wb, self.updated_wb))


def main():
    app = AuditMergeApp()
    app.run()


if __name__ == "__main__":
    main()