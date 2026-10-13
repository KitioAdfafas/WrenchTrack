from datetime import date

from flask import (
    Blueprint, 
    abort,
    flash, 
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from .db import get_db

bp = Blueprint("jobs", __name__, url_prefix="/jobs")

FUEL_TYPES = ["petrol", "diesel", "hybrid", "electric"]

STATUSES = [
    "Received",
    "Diagnosing",
    "Waiting for parts",
    "Repairing",
    "Ready",
    "Picked up"
]

REQUIRED_FIELDS = [
    "customer_name",
    "phone",
    "make",
    "model",
    "year",
    "plate",
    "mileage",
    "fuel_type",
    "problem",
    "date_received",
]

def next_status(status):
    """Return the status that follows this one, or None if it is the last."""
    position = STATUSES.index(status)
    if position == len(STATUSES) - 1:
        return None
    return STATUSES[position + 1]

def get_job_or_404(job_id):
    job = get_db().execute("SELECT * FROM jobs WHERE id = ?",
    (job_id,)).fetchone()
    if job is None:
        abort(404)
    return job
    
def read_job_form(form):
    """Clean the submitted form. Returns (values, error). error is None if valid."""
    values = {
        "customer_name": form.get("customer_name", "").strip(),
        "phone": form.get("phone", "").strip(),
        "make": form.get("make", "").strip(),
        "model": form.get("model", "").strip(),
        "year": form.get("year", "").strip(),
        "plate": form.get("plate", "").strip().upper(),
        "vin": form.get("vin", "").strip().upper(),
        "mileage": form.get("mileage", "").strip(),
        "engine": form.get("engine", "").strip(),
        "fuel_type": form.get("fuel_type", "").strip(),
        "problem": form.get("problem", "").strip(),
        "date_received": form.get("date_received", "").strip(),
    }

    for field in REQUIRED_FIELDS:
        if not values[field]:
            return values, "Please fill in every required field."

    if values["fuel_type"] not in FUEL_TYPES:
        return values, "Pick a valid fuel type."

    try:
        year = int(values["year"])
        mileage = int(values["mileage"])
    except ValueError:
        return values, "Year and mileage must be whole numbers."

    if not 1950 <= year <= date.today().year + 1:
        return values, "That year does not look right."
    if mileage < 0:
        return values, "Mileage cannot be negative."

    try:
        date.fromisoformat(values["date_received"])
    except ValueError:
        return values, "Date must look like 2026-10-10."

    return values, None


@bp.route("/")
def index():
    jobs = get_db().execute(
        "SELECT id, plate, make, model, customer_name, status, date_received "
        "FROM jobs ORDER BY id DESC"
    ).fetchall()
    return render_template("jobs/index.html", jobs=jobs,
    next_status=next_status)


@bp.route("/new", methods=("GET", "POST"))
def new():
    if request.method == "POST":
        values, error = read_job_form(request.form)

        if error is None:
            db = get_db()
            db.execute(
                "INSERT INTO jobs (customer_name, phone, make, model, year, plate, "
                "vin, mileage, engine, fuel_type, problem, date_received, created_by) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    values["customer_name"],
                    values["phone"],
                    values["make"],
                    values["model"],
                    int(values["year"]),
                    values["plate"],
                    values["vin"] or None,
                    int(values["mileage"]),
                    values["engine"] or None,
                    values["fuel_type"],
                    values["problem"],
                    values["date_received"],
                    g.user["id"],
                ),
            )
            db.commit()
            flash("Job saved.", "ok")
            return redirect(url_for("jobs.index"))

        flash(error)
        form = values
    else:
        form = {
            "fuel_type": "petrol",
            "date_received": date.today().isoformat(),
        }

    return render_template("jobs/new.html", form=form, fuel_types=FUEL_TYPES)

@bp.route("/<int:job_id>")
def detail(job_id):
    job = get_job_or_404(job_id)
    notes = get_db().execute(
        "SELECT body, created_at FROM notes WHERE job_id = ? ORDER BY id DESC",
        (job_id,),
    ).fetchall()
    return render_template(
        "jobs/detail.html",
        job=job,
        notes=notes,
        next_label=next_status(job["status"]),
    )

@bp.route("/<int:job_id>/edit")
def edit(job_id):
    job = get_job_or_404(job_id)
    form = {key: ("" if value is None else value) for key, value in dict(job).items()}
    return render_template(
        "jobs/new.html",
        form=form,
        fuel_types=FUEL_TYPES,
        heading="Edit job",
        button="Save changes",
    )

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
        db.commit()

    if request.form.get("back") == "detail":
        return redirect(url_for("jobs.detail", job_id=job_id))
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
        