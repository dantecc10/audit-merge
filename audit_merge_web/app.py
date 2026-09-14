import os
import json
import uuid
import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Import the existing audit merge logic
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audit_merge.excel.io import load_workbook_preserving, read_workers_from_sheet, find_revision_sheet, write_workers_to_sheet, save_workbook
from src.audit_merge.diff.merge import match_workers, diff_workers, compute_stats, apply_auto_merge, apply_conflict_resolution
from src.audit_merge.models import Worker, WorkerDiff, DocumentChecklist

load_dotenv()

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"xlsx", "xls"}
MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "audit-merge-dev-secret-change-me")

# Brand configuration
BRAND = {
    "app_name": os.environ.get("APP_NAME", "Audit Merge Tool"),
    "tagline": os.environ.get("APP_TAGLINE", "Fusiona y revisa archivos de auditoría de nómina"),
    "description": os.environ.get("APP_DESCRIPTION", "Herramienta para fusionar avances de auditoría de expedientes"),
    "logo_text": os.environ.get("LOGO_TEXT", "Audit Merge"),
    "header_subtitle": os.environ.get("HEADER_SUBTITLE", "Compara, fusiona y exporta auditorías de nómina"),
    "primary_color": os.environ.get("PRIMARY_COLOR", "#1e3a5f"),
    "primary_dark": os.environ.get("PRIMARY_DARK", "#152d42"),
    "author_name": os.environ.get("AUTHOR_NAME", ""),
    "about_url": os.environ.get("ABOUT_URL", ""),
    "contact_email": os.environ.get("CONTACT_EMAIL", ""),
    "contact_github": os.environ.get("CONTACT_GITHUB", ""),
}

@app.context_processor
def inject_brand():
    return {"brand": BRAND}

# In-memory session store
DATASTORE = {}

UPLOAD_FOLDER_PATH = Path(UPLOAD_FOLDER)
UPLOAD_FOLDER_PATH.mkdir(exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def _get_state():
    state_id = session.get("state_id")
    if not state_id:
        return None
    return DATASTORE.get(state_id)

def _save_state(state):
    state_id = session.get("state_id")
    if not state_id:
        state_id = str(uuid.uuid4())
        session["state_id"] = state_id
    DATASTORE[state_id] = state

def _process_workbook(file_path):
    """Process an Excel workbook and return workers list and column map"""
    wb = load_workbook_preserving(file_path)
    sheet_name = find_revision_sheet(wb)
    workers, column_map = read_workers_from_sheet(wb[sheet_name])
    return wb, sheet_name, workers, column_map

def _serialize_worker(worker: Worker) -> dict:
    """Serialize a Worker object to dict for JSON storage"""
    return {
        "no": worker.no,
        "nombre": worker.nombre,
        "curp": worker.curp,
        "nss": worker.nss,
        "depto": worker.depto,
        "puesto": worker.puesto,
        "salario": worker.salario,
        "fecha_reingreso": worker.fecha_reingreso,
        "fecha_baja": worker.fecha_baja,
        "fecha_baja_2": worker.fecha_baja_2,
        "fecha_baja_3": worker.fecha_baja_3,
        "checklist": {
            "solicitud_empleo": worker.checklist.solicitud_empleo,
            "fecha_solicitud": worker.checklist.fecha_solicitud,
            "firma": worker.checklist.firma,
            "curriculum_vitae": worker.checklist.curriculum_vitae,
            "acta_nacimiento": worker.checklist.acta_nacimiento,
            "ine": worker.checklist.ine,
            "c_domicilio": worker.checklist.c_domicilio,
            "c_estudios": worker.checklist.c_estudios,
            "constancia_situacion_fiscal": worker.checklist.constancia_situacion_fiscal,
            "numero_imss": worker.checklist.numero_imss,
            "curp_checklist": worker.checklist.curp_checklist,
            "cta_banco": worker.checklist.cta_banco,
            "constancias_laborales": worker.checklist.constancias_laborales,
            "examen_medico": worker.checklist.examen_medico,
            "validacion_fechas": worker.checklist.validacion_fechas,
            "contrato": worker.checklist.contrato,
            "infonavit": worker.checklist.infonavit,
            "designacion_beneficiarios": worker.checklist.designacion_beneficiarios,
            "alta_imss": worker.checklist.alta_imss,
            "contrato_asignado": worker.checklist.contrato_asignado,
            "no_caja": worker.checklist.no_caja,
            "finiquito": worker.checklist.finiquito,
        },
        "row_index": worker.row_index,
    }

def _serialize_diff(diff: WorkerDiff) -> dict:
    """Serialize a WorkerDiff object to dict"""
    return {
        "worker_key": diff.worker_key,
        "base_worker": _serialize_worker(diff.base_worker) if diff.base_worker else None,
        "updated_worker": _serialize_worker(diff.updated_worker) if diff.updated_worker else None,
        "field_diffs": [
            {
                "field_name": fd.field_name,
                "base_value": fd.base_value,
                "updated_value": fd.updated_value,
                "change_type": fd.change_type.value,
            }
            for fd in diff.field_diffs
        ],
        "checklist_added": diff.checklist_added,
        "checklist_removed": diff.checklist_removed,
        "data_changed": diff.data_changed,
    }

def _deserialize_worker(data: dict) -> Worker:
    """Deserialize dict to Worker object"""
    checklist = DocumentChecklist(**data["checklist"])
    return Worker(
        no=data["no"],
        nombre=data["nombre"],
        curp=data["curp"],
        nss=data["nss"],
        depto=data["depto"],
        puesto=data["puesto"],
        salario=data["salario"],
        fecha_reingreso=data["fecha_reingreso"],
        fecha_baja=data["fecha_baja"],
        fecha_baja_2=data["fecha_baja_2"],
        fecha_baja_3=data["fecha_baja_3"],
        checklist=checklist,
        row_index=data["row_index"],
    )

def _deserialize_diff(data: dict) -> WorkerDiff:
    """Deserialize dict to WorkerDiff object"""
    from src.audit_merge.models import FieldDiff, ChangeType
    
    field_diffs = []
    for fd in data["field_diffs"]:
        field_diffs.append(FieldDiff(
            field_name=fd["field_name"],
            base_value=fd["base_value"],
            updated_value=fd["updated_value"],
            change_type=ChangeType(fd["change_type"]),
        ))
    
    return WorkerDiff(
        worker_key=data["worker_key"],
        base_worker=_deserialize_worker(data["base_worker"]) if data["base_worker"] else None,
        updated_worker=_deserialize_worker(data["updated_worker"]) if data["updated_worker"] else None,
        field_diffs=field_diffs,
        checklist_added=data["checklist_added"],
        checklist_removed=data["checklist_removed"],
        data_changed=data["data_changed"],
    )

def _serialize_workers_for_template(workers):
    """Convert workers to list of dicts for template rendering"""
    result = []
    for w in workers:
        x_count = w.checklist.count_x_marks()
        result.append({
            "no": w.no,
            "nombre": w.nombre,
            "curp": w.curp,
            "nss": w.nss,
            "depto": w.depto,
            "puesto": w.puesto,
            "salario": w.salario,
            "fecha_reingreso": w.fecha_reingreso,
            "fecha_baja": w.fecha_baja,
            "x_count": x_count,
            "checklist": {
                "solicitud_empleo": w.checklist.solicitud_empleo,
                "fecha_solicitud": w.checklist.fecha_solicitud,
                "firma": w.checklist.firma,
                "curriculum_vitae": w.checklist.curriculum_vitae,
                "acta_nacimiento": w.checklist.acta_nacimiento,
                "ine": w.checklist.ine,
                "c_domicilio": w.checklist.c_domicilio,
                "c_estudios": w.checklist.c_estudios,
                "constancia_situacion_fiscal": w.checklist.constancia_situacion_fiscal,
                "numero_imss": w.checklist.numero_imss,
                "curp_checklist": w.checklist.curp_checklist,
                "cta_banco": w.checklist.cta_banco,
                "constancias_laborales": w.checklist.constancias_laborales,
                "examen_medico": w.checklist.examen_medico,
                "validacion_fechas": w.checklist.validacion_fechas,
                "contrato": w.checklist.contrato,
                "infonavit": w.checklist.infonavit,
                "designacion_beneficiarios": w.checklist.designacion_beneficiarios,
                "alta_imss": w.checklist.alta_imss,
                "contrato_asignado": w.checklist.contrato_asignado,
                "no_caja": w.checklist.no_caja,
                "finiquito": w.checklist.finiquito,
            }
        })
    return result


@app.route("/")
def index():
    state = _get_state() or {}
    return render_template("index.html",
        base_file=state.get("base_file"),
        updated_file=state.get("updated_file"),
        stats=state.get("stats"),
        diffs=state.get("diffs"),
        current_step=state.get("current_step", 1),
    )


@app.route("/upload_base", methods=["POST"])
def upload_base():
    if "base_file" not in request.files:
        flash("No se recibió el archivo base.", "error")
        return redirect(url_for("index"))

    file = request.files["base_file"]
    if file.filename == "":
        flash("Debes seleccionar un archivo.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash("Formato inválido. Solo se permite .xlsx o .xls", "error")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    save_path = UPLOAD_FOLDER_PATH / f"{file_id}_{filename}"
    file.save(save_path)

    try:
        wb, sheet_name, workers, column_map = _process_workbook(str(save_path))
    except Exception as e:
        flash(f"Error procesando el archivo: {e}", "error")
        return redirect(url_for("index"))

    state = _get_state() or {}
    state["base_file"] = {
        "id": file_id,
        "filename": filename,
        "path": str(save_path),
        "sheet_name": sheet_name,
        "column_map": column_map,
    }
    state["base_workers"] = [_serialize_worker(w) for w in workers]
    state["current_step"] = 2
    _save_state(state)

    flash(f"Archivo base cargado: {len(workers)} trabajadores detectados", "success")
    return redirect(url_for("index"))


@app.route("/upload_updated", methods=["POST"])
def upload_updated():
    if "updated_file" not in request.files:
        flash("No se recibió el archivo actualizado.", "error")
        return redirect(url_for("index"))

    file = request.files["updated_file"]
    if file.filename == "":
        flash("Debes seleccionar un archivo.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash("Formato inválido. Solo se permite .xlsx o .xls", "error")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    save_path = UPLOAD_FOLDER_PATH / f"{file_id}_{filename}"
    file.save(save_path)

    try:
        wb, sheet_name, workers, column_map = _process_workbook(str(save_path))
    except Exception as e:
        flash(f"Error procesando el archivo: {e}", "error")
        return redirect(url_for("index"))

    state = _get_state() or {}
    state["updated_file"] = {
        "id": file_id,
        "filename": filename,
        "path": str(save_path),
        "sheet_name": sheet_name,
        "column_map": column_map,
    }
    state["updated_workers"] = [_serialize_worker(w) for w in workers]
    state["current_step"] = 3
    _save_state(state)

    flash(f"Archivo actualizado cargado: {len(workers)} trabajadores detectados", "success")
    return redirect(url_for("index"))


@app.route("/process", methods=["POST"])
def process_merge():
    state = _get_state()
    if not state or "base_workers" not in state or "updated_workers" not in state:
        flash("Primero carga ambos archivos.", "error")
        return redirect(url_for("index"))

    # Deserialize workers
    base_workers = [_deserialize_worker(w) for w in state["base_workers"]]
    updated_workers = [_deserialize_worker(w) for w in state["updated_workers"]]

    # Get column maps
    base_column_map = state.get("base_file", {}).get("column_map", {})
    updated_column_map = state.get("updated_file", {}).get("column_map", {})

    # Run diff
    matches = match_workers(base_workers, updated_workers)
    diffs = []
    for key, (base_w, updated_w) in matches.items():
        diffs.append(diff_workers(base_w, updated_w))

    stats = compute_stats(diffs)

    # Serialize diffs for storage
    state["diffs"] = [_serialize_diff(d) for d in diffs]
    state["stats"] = stats.to_dict()
    state["current_step"] = 4
    _save_state(state)

    flash(f"Procesado: {stats.auto_mergeable} auto-mergeables, {stats.conflicts} conflictos", "success")
    return redirect(url_for("index"))


@app.route("/auto_merge", methods=["POST"])
def auto_merge():
    state = _get_state()
    if not state or "diffs" not in state:
        flash("No hay diferencias para procesar.", "error")
        return redirect(url_for("index"))

    diffs = [_deserialize_diff(d) for d in state["diffs"]]
    base_workers = [_deserialize_worker(w) for w in state["base_workers"]]
    updated_workers = [_deserialize_worker(w) for w in state["updated_workers"]]

    auto_merged = 0
    merged_workers = {}
    for diff in diffs:
        if diff.is_auto_mergeable and diff.base_worker and diff.updated_worker:
            merged = apply_auto_merge(diff.base_worker, diff.updated_worker)
            merged_workers[diff.worker_key] = merged
            auto_merged += 1

    state["merged_workers"] = {k: _serialize_worker(v) for k, v in merged_workers.items()}
    state["auto_merged"] = auto_merged
    _save_state(state)

    flash(f"Auto-merge aplicado a {auto_merged} trabajadores", "success")
    return redirect(url_for("index"))


@app.route("/conflicts")
def conflicts_view():
    state = _get_state()
    if not state or "diffs" not in state:
        return redirect(url_for("index"))

    conflicts = [d for d in state["diffs"] if _deserialize_diff(d).has_conflicts]
    current_index = request.args.get("index", 0, type=int)
    if current_index < 0 or current_index >= len(conflicts):
        return redirect(url_for("index"))
    return render_template("conflicts.html",
        conflicts=conflicts,
        current_index=current_index,
        total=len(conflicts),
    )


@app.route("/resolve_conflict", methods=["POST"])
def resolve_conflict():
    state = _get_state()
    if not state or "diffs" not in state:
        return jsonify({"error": "No state"}), 400

    data = request.get_json()
    action = data.get("action")  # "keep_base", "use_updated", "manual"
    index = data.get("index", 0)
    manual_values = data.get("manual_values", {})

    diffs = [_deserialize_diff(d) for d in state["diffs"]]
    conflicts = [d for d in diffs if d.has_conflicts]

    if index >= len(conflicts):
        return jsonify({"error": "Invalid index"}), 400

    diff = conflicts[index]
    base = diff.base_worker
    updated = diff.updated_worker

    if action == "keep_base" and base:
        resolution = {f: getattr(base.checklist, f) for f in
                     DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS}
        resolution.update({
            "nombre": base.nombre, "curp": base.curp, "nss": base.nss,
            "depto": base.depto, "puesto": base.puesto, "salario": base.salario,
            "fecha_reingreso": base.fecha_reingreso, "fecha_baja": base.fecha_baja,
            "fecha_baja_2": base.fecha_baja_2, "fecha_baja_3": base.fecha_baja_3,
        })
    elif action == "use_updated" and updated:
        resolution = {f: getattr(updated.checklist, f) for f in
                     DocumentChecklist.CHECKLIST_FIELDS + DocumentChecklist.DATA_FIELDS}
        resolution.update({
            "nombre": updated.nombre, "curp": updated.curp, "nss": updated.nss,
            "depto": updated.depto, "puesto": updated.puesto, "salario": updated.salario,
            "fecha_reingreso": updated.fecha_reingreso, "fecha_baja": updated.fecha_baja,
            "fecha_baja_2": updated.fecha_baja_2, "fecha_baja_3": updated.fecha_baja_3,
        })
    elif action == "manual":
        resolution = manual_values
    else:
        return jsonify({"error": "Invalid action"}), 400

    if base and updated:
        merged = apply_conflict_resolution(base, updated, resolution)
    elif updated:
        merged = updated
    else:
        merged = base

    # Store resolution
    if "resolutions" not in state:
        state["resolutions"] = {}
    state["resolutions"][diff.worker_key] = resolution
    state["merged_workers"] = state.get("merged_workers", {})
    state["merged_workers"][diff.worker_key] = _serialize_worker(merged)
    _save_state(state)

    return jsonify({"success": True, "next_index": index + 1, "total": len([d for d in diffs if d.has_conflicts])})


@app.route("/export", methods=["POST"])
def export_merged():
    state = _get_state()
    if not state or "base_file" not in state:
        flash("No hay archivos para exportar.", "error")
        return redirect(url_for("index"))

    # Load base workbook
    base_path = state["base_file"]["path"]
    wb = load_workbook_preserving(base_path)
    sheet_name = state["base_file"]["sheet_name"]
    ws = wb[sheet_name]

    # Collect all workers
    base_workers = [_deserialize_worker(w) for w in state["base_workers"]]
    updated_workers = [_deserialize_worker(w) for w in state["updated_workers"]]

    all_workers = {}
    for w in base_workers:
        all_workers[w.key] = w
    for w in updated_workers:
        all_workers[w.key] = w

    # Apply auto-merged
    if "merged_workers" in state:
        for key, worker_data in state["merged_workers"].items():
            all_workers[key] = _deserialize_worker(worker_data)

    # Apply manual resolutions
    if "resolutions" in state:
        diffs = [_deserialize_diff(d) for d in state.get("diffs", [])]
        for key, resolution in state["resolutions"].items():
            diff = next((d for d in diffs if d.worker_key == key), None)
            if diff and diff.base_worker and diff.updated_worker:
                merged = apply_conflict_resolution(diff.base_worker, diff.updated_worker, resolution)
                all_workers[key] = merged
            elif diff and diff.updated_worker:
                all_workers[key] = diff.updated_worker

    # Write to sheet using base column map
    base_column_map = state.get("base_file", {}).get("column_map", {})
    sorted_workers = sorted(all_workers.values(), key=lambda w: (w.no or 0, w.nombre))
    write_workers_to_sheet(ws, sorted_workers, column_map=base_column_map)

    # Save output
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(state["base_file"]["filename"]).stem
    output_name = f"{base_name}_Merged_{timestamp}.xlsx"
    output_path = UPLOAD_FOLDER_PATH / output_name
    save_workbook(wb, str(output_path))

    return send_file(str(output_path), as_attachment=True, download_name=output_name)


@app.route("/api/diff_detail/<int:index>")
def api_diff_detail(index):
    state = _get_state()
    if not state or "diffs" not in state:
        return jsonify({"error": "No diffs"}), 404

    diffs = [_deserialize_diff(d) for d in state["diffs"]]
    if index >= len(diffs):
        return jsonify({"error": "Index out of range"}), 404

    diff = diffs[index]
    return jsonify({
        "worker_key": diff.worker_key,
        "base_worker": _serialize_worker(diff.base_worker) if diff.base_worker else None,
        "updated_worker": _serialize_worker(diff.updated_worker) if diff.updated_worker else None,
        "conflict_summary": diff.conflict_summary,
        "checklist_added": diff.checklist_added,
        "checklist_removed": diff.checklist_removed,
        "data_changed": diff.data_changed,
        "field_diffs": [
            {
                "field_name": fd.field_name,
                "base_value": fd.base_value,
                "updated_value": fd.updated_value,
                "change_type": fd.change_type.value,
            }
            for fd in diff.field_diffs
        ],
    })


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == "__main__":
    PORT = int(os.environ.get("FLASK_PORT", 5001))
    app.run(debug=True, port=PORT)