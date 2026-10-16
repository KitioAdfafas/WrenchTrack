import difflib
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

ALIAS_GROUPS = [
    {"vw", "volkswagen"},
    {"merc", "mercedes", "mercedes-benz", "benz"},
    {"skoda", "skodaa"}
]

TERM_TO_GROUP = {}
for group in ALIAS_GROUPS:
    for term in group:
        TERM_TO_GROUP[term] = group


def can_fuzzy(word):
    """Typo tolerance only for words of 4+ characters without digits."""
    return len(word) >= 4 and not any(ch.isdigit() for ch in word)

def word_variants(word):
    """Return the spellings to look for: the word itself plus its aliases."""
    if word in TERM_TO_GROUP:
        return set(TERM_TO_GROUP[word])
    if can_fuzzy(word):
        close = difflib.get_close_matches(word, TERM_TO_GROUP.keys(), n=1, cutoff=0.8)
        if close:
            return set(TERM_TO_GROUP[close[0]])
    return {word}

def job_matches(job, words):
    """True if every search word is found in the job (alias, substring or typo)."""    
    haystack = " ".join(
        [job["plate"], job["customer_name"], job["make"], job["model"]]
    ).casefold()
    tokens = haystack.replace("-", " ").split()

    for word in words:
        if any(variant in haystack for variant in word_variants(word)):
            continue
        if can_fuzzy(word) and difflib.get_close_matches(word, tokens, n=1, cutoff=0.8):
            continue
        return False
    return True

@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    sql = (
        "SELECT id, plate, make, model, customer_name, status, date_received "
        "FROM jobs"
    )
    conditions = []
    params = []

    if status in STATUSES:
        conditions.append("status = ?")
        params.append(status)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id DESC"

    jobs = get_db().execute(sql, params).fetchall()

    words = q.casefold().split()
    if words:
        jobs = [job for job in jobs if job_matches(job, words)]

    return render_template(
        "jobs/index.html",
        jobs=jobs,
        next_status=next_status,
        q=q,
        status=status,
        statuses=STATUSES,
    )            

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

    fault_codes = get_db().execute(
        "SELECT id, code, description, created_at FROM fault_codes "
        "WHERE job_id = ? ORDER BY id",
        (job_id,),
    ).fetchall()

    return render_template(
        "jobs/detail.html",
        job=job,
        notes=notes,
        fault_codes=fault_codes,
        next_label=next_status(job["status"]),
    )

@bp.route("/<int:job_id>/edit", methods=("GET", "POST"))
def edit(job_id):
    job = get_job_or_404(job_id)
    if request.method == "POST":
        values, error = read_job_form(request.form)

        if error is None:
            db = get_db()
            db.execute(
                "UPDATE jobs SET customer_name = ?, phone = ?, make = ?, model = ?,"
                "year = ?, plate = ?, vin = ?, mileage = ?, engine = ?, "
                "fuel_type = ?, problem = ?, date_received = ? "
                "WHERE id = ?",
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
                    job_id,
                ),
            )
            db.commit()
            flash("Job updated.", "ok")
            return redirect(url_for("jobs.detail", job_id=job_id))

        flash(error)
        form = values
    else:
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

@bp.route("/<int:job_id>/fault-codes", methods=("POST",))
def add_fault_code(job_id):
    get_job_or_404(job_id)
    code = request.form.get("code", "").strip().upper()
    description = request.form.get("description", "").strip()

    if not code:
        flash("A fault code cannot be empty.")
    elif len(code) > 20:
        flash("A fault code can be at most 20 characters.")
    elif len(description) > 200:
        flash("The description can be at most 200 chatacters.")
    else:
        db = get_db()
        exists = db.execute(
            "SELECT 1 FROM fault_codes WHERE job_id = ? AND code = ?",
            (job_id, code),
        ).fetchone()
        if exists:
            flash("That code is alredy on this job.")
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