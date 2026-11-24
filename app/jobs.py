from datetime import date

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from .db import get_db
from .export import DELIMITERS, export_csv_bytes, find_export_jobs
from .job_form import (
    CAR_MODELS,
    FUEL_TYPES,
    LAST_VISIT_FIELDS,
    job_params,
    read_job_form,
)
from .limits import (
    MAX_AMOUNT,
    MAX_CODE,
    MAX_DESCRIPTION,
    MAX_PART_NAME,
    MAX_QUANTITY,
)
from .photos import (
    PHOTO_STAGES,
    ask_for_photos_again,
    default_photo_stage,
    job_photos,
    photo_folder,
    photo_name_error,
    read_photos,
    remove_photo_file,
    save_job_photos,
)
from .search import find_related_jobs, job_matches
from .shop import (
    PARTS_TOTAL_SQL,
    job_total,
    money,
    shop_now,
    shop_today,
    utc_text,
)
from .status import LAST_STATUS, STATUSES, is_stuck, next_status

bp = Blueprint("jobs", __name__, url_prefix="/jobs")

def get_job_or_404(job_id):
    job = get_db().execute(
        "SELECT * FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()
    if job is None:
        abort(404)
    return job

def job_parts(job_id):
    """All parts on a job, oldest first."""
    return get_db().execute(
        "SELECT id, name, quantity, price FROM parts WHERE job_id = ? ORDER BY id",
        (job_id,),
    ).fetchall()

def job_fault_codes(job_id):
    """All fault codes on a job, oldest first."""
    return get_db().execute(
        "SELECT id, code, description, created_at FROM fault_codes "
        "WHERE job_id = ? ORDER BY id",
        (job_id,),
    ).fetchall()

def calculate_totals(job, parts):
    """Return (parts_total, total), calculated from the stored rows."""
    parts_total = round(sum(p["quantity"] * p["price"] for p in parts), 2)
    return parts_total, job_total(parts_total, job["labor_cost"])

def record_status(db, job_id, from_status, to_status):
    """Write one line of status history, signed by the user."""
    db.execute(
        "INSERT INTO status_history (job_id, from_status, to_status, changed_by) "
        "VALUES (?, ?, ?, ?)",
        (job_id, from_status, to_status, g.user["id"]),
    )

def read_amount(text):
    """Read a money amount, allowing a comma as the decimal mark. None if it is not a number."""
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None

def is_local_path(target):
    """True only for an address on this site."""
    return (
        target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
    )

def ready_message(job, total):
    """Build the pickup message for the customer."""
    return (
        f"Hello {job['customer_name']}, your {job['make']} {job['model']} "
        f"({job['plate']}) is ready for pickup. Total: {money(total)}."
    )

@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    sql = (
        "SELECT id, plate, make, model, customer_name, status, date_received, "
        "status_changed_at, phone, vin, "
        "(SELECT GROUP_CONCAT(code, ' ') FROM fault_codes "
        "WHERE fault_codes.job_id = jobs.id) AS codes "
        "FROM jobs"
    )
    conditions = []
    params = []

    if status in STATUSES:
        conditions.append("status = ?")
        params.append(status)
    elif status == "" and not q:
        conditions.append("status != ?")
        params.append(LAST_STATUS)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY (status = ?), date_received, id"
    params.append(LAST_STATUS)

    jobs = get_db().execute(sql, params).fetchall()

    words = q.casefold().split()
    if words:
        jobs = [job for job in jobs if job_matches(job, words)]

    return render_template(
        "jobs/index.html",
        jobs=jobs,
        q=q,
        status=status,
        statuses=STATUSES,
    )

def render_job_form(form, editing=False, related=None):
    """Show the job form, for a new job or for editing one."""
    return render_template(
        "jobs/new.html",
        form=form,
        fuel_types=FUEL_TYPES,
        car_models=CAR_MODELS,
        editing=editing,
        related=related,
    )

@bp.route("/new", methods=("GET", "POST"))
def new():
    if request.method == "POST":
        values, error = read_job_form(request.form)

        if error is None and not request.form.get("confirm_duplicate"):
            related = find_related_jobs(values["plate"], values["vin"])
            if related:
                ask_for_photos_again()
                return render_job_form(values, related=related)

        if error is None:
            photos, error = read_photos()

        if error is None:
            db = get_db()
            params = job_params(values)
            params["status"] = STATUSES[0]
            params["created_by"] = g.user["id"]
            cursor = db.execute(
                "INSERT INTO jobs (customer_name, phone, make, model, year, plate, "
                "vin, mileage, engine, fuel_type, problem, date_received, status, "
                "status_changed_at, created_by) "
                "VALUES (:customer_name, :phone, :make, :model, :year, :plate, "
                ":vin, :mileage, :engine, :fuel_type, :problem, :date_received, "
                ":status, datetime('now'), :created_by)",
                params,
            )
            job_id = cursor.lastrowid
            record_status(db, job_id, None, STATUSES[0])
            save_job_photos(db, get_job_or_404(job_id), photos, PHOTO_STAGES[0])
            db.commit()
            flash("Job saved.", "ok")
            return redirect(url_for("jobs.detail", job_id=job_id))

        flash(error)
        ask_for_photos_again()
        form = values
    else:
        form = {
            "fuel_type": FUEL_TYPES[0],
            "date_received": shop_today().isoformat(),
        }

    return render_job_form(form)

@bp.route("/same-car")
def same_car():
    plate = request.args.get("plate", "").strip()
    vin = request.args.get("vin", "").strip()
    related = find_related_jobs(plate, vin)
    if not related:
        return ""
    return render_template("jobs/_same_car.html", related=related)

@bp.route("/last-visit")
def last_visit():
    plate = request.args.get("plate", "").strip()
    related = find_related_jobs(plate, "")
    if not related:
        return {}
    return {field: related[0][field] or "" for field in LAST_VISIT_FIELDS}

@bp.route("/<int:job_id>")
def detail(job_id):
    job = get_job_or_404(job_id)
    notes = get_db().execute(
        "SELECT body, created_at FROM notes WHERE job_id = ? ORDER BY id DESC",
        (job_id,),
    ).fetchall()

    parts = job_parts(job_id)
    fault_codes = job_fault_codes(job_id)
    parts_total, total = calculate_totals(job, parts)

    history = get_db().execute(
        "SELECT h.from_status, h.to_status, h.changed_at, u.username "
        "FROM status_history h LEFT JOIN users u ON u.id = h.changed_by "
        "WHERE h.job_id = ? ORDER BY h.id DESC",
        (job_id,),
    ).fetchall()

    before_photos, after_photos = job_photos(job_id)

    related_count = len(find_related_jobs(job["plate"], job["vin"], exclude_id=job_id))
    ready_text = ready_message(job, total) if job["status"] == "Ready" else None

    return render_template(
        "jobs/detail.html",
        job=job,
        notes=notes,
        fault_codes=fault_codes,
        parts=parts,
        history=history,
        parts_total=parts_total,
        total=total,
        related_count=related_count,
        ready_text=ready_text,
        photo_stage=default_photo_stage(job["status"]),
        before_photos=before_photos,
        after_photos=after_photos,
    )

@bp.route("/<int:job_id>/edit", methods=("GET", "POST"))
def edit(job_id):
    job = get_job_or_404(job_id)
    if request.method == "POST":
        values, error = read_job_form(request.form)

        if error is None:
            db = get_db()
            params = job_params(values)
            params["id"] = job_id
            db.execute(
                "UPDATE jobs SET customer_name = :customer_name, phone = :phone, "
                "make = :make, model = :model, year = :year, plate = :plate, "
                "vin = :vin, mileage = :mileage, engine = :engine, "
                "fuel_type = :fuel_type, problem = :problem, "
                "date_received = :date_received "
                "WHERE id = :id",
                params,
            )
            db.commit()
            flash("Job updated.", "ok")
            return redirect(url_for("jobs.detail", job_id=job_id))

        flash(error)
        form = values
    else:
        form = {key: ("" if value is None else value) for key, value in dict(job).items()}

    return render_job_form(form, editing=True)

@bp.route("/<int:job_id>/advance", methods=("POST",))
def advance(job_id):
    job = get_job_or_404(job_id)
    following = next_status(job["status"])

    if following is None:
        flash("This job is already picked up.")
    else:
        db = get_db()
        db.execute(
            "UPDATE jobs SET status = ?, status_changed_at = datetime('now') "
            "WHERE id = ?",
            (following, job_id),
        )
        record_status(db, job_id, job["status"], following)
        db.commit()

    target = request.form.get("next", "")
    if is_local_path(target):
        return redirect(target)
    return redirect(url_for("jobs.index"))

@bp.route("/<int:job_id>/notes", methods=("POST",))
def add_note(job_id):
    get_job_or_404(job_id)
    body = request.form.get("body", "").strip()

    if not body:
        flash("A note cannot be empty.")
    else:
        db = get_db()
        db.execute("INSERT INTO notes (job_id, body) VALUES (?, ?)", (job_id, body))
        db.commit()
        flash("Note added.", "ok")

    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.route("/<int:job_id>/fault-codes", methods=("POST",))
def add_fault_code(job_id):
    get_job_or_404(job_id)
    code = request.form.get("code", "").strip().upper()
    description = request.form.get("description", "").strip()

    if not code:
        flash("A fault code cannot be empty.")
    elif len(code) > MAX_CODE:
        flash(f"A fault code can be at most {MAX_CODE} characters.")
    elif len(description) > MAX_DESCRIPTION:
        flash(f"The description can be at most {MAX_DESCRIPTION} characters.")
    else:
        db = get_db()
        exists = db.execute(
            "SELECT 1 FROM fault_codes WHERE job_id = ? AND code = ?",
            (job_id, code),
        ).fetchone()
        if exists:
            flash("That code is already on this job.")
        else:
            db.execute(
                "INSERT INTO fault_codes (job_id, code, description) VALUES (?, ?, ?)",
                (job_id, code, description or None),
            )
            db.commit()
            flash("Fault code added.", "ok")

    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.route("/<int:job_id>/fault-codes/<int:code_id>/delete", methods=("POST",))
def delete_fault_code(job_id, code_id):
    get_job_or_404(job_id)
    db = get_db()
    cursor = db.execute(
        "DELETE FROM fault_codes WHERE id = ? AND job_id = ?",
        (code_id, job_id),
    )
    db.commit()

    if cursor.rowcount:
        flash("Fault code removed.", "ok")
    else:
        flash("That fault code was not found.")

    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.route("/<int:job_id>/parts", methods=("POST",))
def add_part(job_id):
    get_job_or_404(job_id)
    name = request.form.get("name", "").strip()
    quantity_text = request.form.get("quantity", "").strip()
    price_text = request.form.get("price", "")

    error = None
    if not name:
        error = "A part needs a name."
    elif len(name) > MAX_PART_NAME:
        error = f"The part name can be at most {MAX_PART_NAME} characters."
    else:
        try:
            quantity = int(quantity_text)
        except ValueError:
            quantity = None
        price = read_amount(price_text)
        if quantity is None or price is None:
            error = "Quantity must be a whole number and price must be a number."
        elif not 1 <= quantity <= MAX_QUANTITY:
            error = f"Quantity must be between 1 and {MAX_QUANTITY}."
        elif not 0 <= price <= MAX_AMOUNT:
            error = f"Price must be between 0 and {MAX_AMOUNT}."

    if error:
        flash(error)
    else:
        db = get_db()
        db.execute(
            "INSERT INTO parts (job_id, name, quantity, price) VALUES (?, ?, ?, ?)",
            (job_id, name, quantity, price),
        )
        db.commit()
        flash("Part added.", "ok")

    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.route("/<int:job_id>/parts/<int:part_id>/delete", methods=("POST",))
def delete_part(job_id, part_id):
    get_job_or_404(job_id)
    db = get_db()
    cursor = db.execute(
        "DELETE FROM parts WHERE id = ? AND job_id = ?",
        (part_id, job_id),
    )
    db.commit()

    if cursor.rowcount:
        flash("Part removed.", "ok")
    else:
        flash("That part was not found.")

    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.route("/<int:job_id>/photos", methods=("POST",))
def add_photo(job_id):
    job = get_job_or_404(job_id)
    stage = request.form.get("stage", "")

    error = None
    if stage not in PHOTO_STAGES:
        error = "Pick Before or After."
    else:
        photos, error = read_photos()
        if not photos and not error:
            error = "Choose a photo to upload."

    if error:
        flash(error)
        ask_for_photos_again()
    else:
        db = get_db()
        save_job_photos(db, job, photos, stage)
        db.commit()
        if len(photos) == 1:
            flash("Photo added.", "ok")
        else:
            flash(f"{len(photos)} photos added.", "ok")

    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.app_errorhandler(413)
def upload_too_large(error):
    flash("That upload is too large.")
    job_id = (request.view_args or {}).get("job_id")
    if job_id is None:
        return redirect(url_for("jobs.index"))
    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.route("/<int:job_id>/photos/<int:photo_id>")
def photo_file(job_id, photo_id):
    photo = get_db().execute(
        "SELECT filename FROM photos WHERE id = ? AND job_id = ?",
        (photo_id, job_id),
    ).fetchone()
    if photo is None:
        abort(404)
    return send_from_directory(photo_folder(), photo["filename"])

@bp.route("/<int:job_id>/photos/<int:photo_id>/rename", methods=("POST",))
def rename_photo(job_id, photo_id):
    get_job_or_404(job_id)
    name = request.form.get("name", "").strip()

    error = photo_name_error(name)
    if error:
        flash(error)
    else:
        db = get_db()
        cursor = db.execute(
            "UPDATE photos SET name = ? WHERE id = ? AND job_id = ?",
            (name or None, photo_id, job_id),
        )
        db.commit()

        if cursor.rowcount:
            flash("Photo renamed.", "ok")
        else:
            flash("That photo was not found.")

    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.route("/<int:job_id>/photos/<int:photo_id>/delete", methods=("POST",))
def delete_photo(job_id, photo_id):
    get_job_or_404(job_id)
    db = get_db()
    photo = db.execute(
        "SELECT filename FROM photos WHERE id = ? AND job_id = ?",
        (photo_id, job_id),
    ).fetchone()

    if photo is None:
        flash("That photo was not found.")
    else:
        db.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        db.commit()
        remove_photo_file(photo["filename"])
        flash("Photo removed.", "ok")

    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.route("/<int:job_id>/labor", methods=("POST",))
def set_labor(job_id):
    get_job_or_404(job_id)
    labor_cost = read_amount(request.form.get("labor_cost", ""))

    if labor_cost is None or not 0 <= labor_cost <= MAX_AMOUNT:
        flash(f"Labor cost must be a number between 0 and {MAX_AMOUNT}.")
    else:
        db = get_db()
        db.execute(
            "UPDATE jobs SET labor_cost = ? WHERE id = ?",
            (round(labor_cost, 2), job_id),
        )
        db.commit()
        flash("Labor cost saved.", "ok")

    return redirect(url_for("jobs.detail", job_id=job_id))

@bp.route("/<int:job_id>/print")
def print_ticket(job_id):
    job = get_job_or_404(job_id)
    fault_codes = job_fault_codes(job_id)
    parts = job_parts(job_id)
    parts_total, total = calculate_totals(job, parts)

    return render_template(
        "jobs/print.html",
        job=job,
        fault_codes=fault_codes,
        parts=parts,
        parts_total=parts_total,
        total=total,
    )

@bp.route("/<int:job_id>/repair-history")
def previous_repairs(job_id):
    job = get_job_or_404(job_id)
    related = find_related_jobs(job["plate"], job["vin"], exclude_id=job_id)
    return render_template("jobs/previous.html", job=job, related=related)

@bp.route("/export")
def export():
    return render_template("jobs/export.html")

@bp.route("/export.csv")
def export_csv():
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    delimiter = DELIMITERS.get(request.args.get("delimiter", ""), ";")

    try:
        start = date.fromisoformat(date_from) if date_from else None
        end = date.fromisoformat(date_to) if date_to else None
    except ValueError:
        flash("Dates must look like 2026-10-10.")
        return redirect(url_for("jobs.export"))
    if start and end and start > end:
        flash("The start date must not be after the end date.")
        return redirect(url_for("jobs.export"))

    rows = find_export_jobs(start, end)
    filename = f"wrenchtrack_jobs_{shop_today().isoformat()}.csv"
    return Response(
        export_csv_bytes(rows, delimiter),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

def pick_selected(open_jobs, job_id):
    """Return the open job with this id, or the top of the tower if it is not there."""
    for job in open_jobs:
        if job["id"] == job_id:
            return job
    if open_jobs:
        return open_jobs[0]
    return None

@bp.route("/dashboard")
def dashboard():
    db = get_db()

    open_jobs = db.execute(
        "SELECT id, plate, make, model, year, engine, mileage, customer_name, phone, "
        "status, date_received, status_changed_at, labor_cost "
        "FROM jobs WHERE status != ? ORDER BY date_received, id",
        (LAST_STATUS,),
    ).fetchall()
    late_count = len([j for j in open_jobs if is_stuck(j)])

    selected = pick_selected(open_jobs, request.args.get("job", type=int))
    selected_codes = []
    selected_total = 0
    if selected is not None:
        selected_codes = job_fault_codes(selected["id"])
        _, selected_total = calculate_totals(selected, job_parts(selected["id"]))

    month_start = shop_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start_utc = utc_text(month_start)

    picked = db.execute(
        "SELECT j.id, j.labor_cost, " + PARTS_TOTAL_SQL + " "
        "FROM jobs j "
        "JOIN status_history h ON h.job_id = j.id AND h.to_status = ? AND h.changed_at >= ? "
        "LEFT JOIN parts p ON p.job_id = j.id "
        "GROUP BY j.id",
        (LAST_STATUS, month_start_utc),
    ).fetchall()
    parts_total = round(sum(r["parts_total"] for r in picked), 2)
    labor_total = round(sum(r["labor_cost"] for r in picked), 2)

    return render_template(
        "jobs/dashboard.html",
        statuses=STATUSES,
        late_count=late_count,
        month_name=month_start.strftime("%B"),
        picked_count=len(picked),
        parts_total=parts_total,
        labor_total=labor_total,
        revenue=job_total(parts_total, labor_total),
        tower=open_jobs,
        selected=selected,
        selected_codes=selected_codes,
        selected_total=selected_total,
    )