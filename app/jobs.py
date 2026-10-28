import csv
import difflib
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import (
    Blueprint, 
    Response,
    abort,
    current_app,
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

STUCK_AFTER_DAYS = {
    "Received": 1,
    "Diagnosing": 3,
    "Waiting for parts": 5,
    "Repairing": 4,
    "Ready": 2,
}

def load_car_models():
    """Read app/data/car-list.json into {make: [models]}. Empty if the file is missing."""
    path = Path(__file__).parent / "data" / "car-list.json"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {
        entry["brand"]: sorted(set(entry["models"]), key=str.casefold)
        for entry in data
    }        

CAR_MODELS = load_car_models()

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

@bp.app_template_filter("localtime")
def localtime(value):
    """Turn a UTC timestamp from SQLite into shop time, like 2026-10-24 15:00."""
    if not value:
        return ""
    try:
        utc = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return value
    zone = ZoneInfo(current_app.config["SHOP_TIMEZONE"])
    return utc.astimezone(zone).strftime("%Y-%m-%d %H:%M")    

@bp.app_template_global()
def days_in_status(changed_at):
    """Whole days since the last status change (stored in UTC)."""
    try:
        changed = datetime.strptime(changed_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return 0
    return max(0, (datetime.now(timezone.utc) - changed).days)

@bp.app_template_global()
def is_stuck(job):
    """True if the job has sat in its current status for too long."""
    limit = STUCK_AFTER_DAYS.get(job["status"])
    return limit is not None and days_in_status(job["status_changed_at"]) >= limit    

def get_job_or_404(job_id):
    job = get_db().execute("SELECT * FROM jobs WHERE id = ?",
    (job_id,)).fetchone()
    if job is None:
        abort(404)
    return job

def calculate_totals(job, parts):
    """Return (parts_total, total), calculated from the stored rows."""
    parts_total = round(sum(p["quantity"] * p["price"] for p in parts), 2)
    total = round(parts_total + job["labor_cost"], 2)
    return parts_total, total
    
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
    {"skoda", "škoda"}
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

def squash(text):
    """Lowercase and keep only letters and digits, so SR-1234-AG becomes sr1234ag"""
    return "".join(ch for ch in text.casefold() if ch.isalnum())

def job_matches(job, words):
    """True if every search word is found in the job (alias, substring or typo)."""    
    haystack = " ".join(
        [job["plate"], job["customer_name"], job["make"], job["model"],
         job["phone"], job["vin"] or "", job["codes"] or ""]
    ).casefold()
    tokens = haystack.replace("-", " ").split()
    squashed_fields = [
        squash(job["plate"]),
        squash(job["phone"]),
        squash(job["vin"] or ""),
    ]

    for word in words:
        if any(variant in haystack for variant in word_variants(word)):
            continue
        squashed = squash(word)
        if squashed and any(squashed in field for field in squashed_fields):
            continue
        if can_fuzzy(word) and difflib.get_close_matches(word, tokens, n=1, cutoff=0.8):
            continue
        return False
    return True

def find_related_jobs(plate, vin, exclude_id=None):
    """Other jobs of the same car: same plate, or same VIN (only if both are filled in)."""
    plate_key = squash(plate)
    vin_key = squash(vin or "")
    rows = get_db().execute(
        "SELECT id, plate, vin, customer_name, make, model, status, date_received, problem "
        "FROM jobs WHERE id != ? ORDER BY date_received DESC, id DESC",
        (exclude_id or 0,),
    ).fetchall()

    found = []
    for row in rows:
        row_vin = squash(row["vin"] or "")
        same_plate = bool(plate_key) and squash(row["plate"]) == plate_key
        same_vin = bool(vin_key) and row_vin == vin_key
        if not (same_plate or same_vin):
            continue

        if same_plate and same_vin:
            reason = "Same plate and VIN"
        elif same_plate and vin_key and row_vin:
            reason = "Same plate, different VIN"
        elif same_plate:
            reason = "Same plate"
        else:
            reason = "Same VIN, different plate"

        job = dict(row)
        job["reason"] = reason
        found.append(job)
    return found                    

@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    sql = (
        "SELECT id, plate, make, model, customer_name, status, date_received, "
        "status_changed_at, phone, vin, "
        "(SELECT GROUP_CONCAT(code, ' ') FROM fault_codes "
        "WHERE fault_codes.job_id = jobs.id) AS codes, "
        "MAX(0, CAST(julianday(date('now')) - julianday(date_received) AS INTEGER)) "
        "AS days_in_shop "
        "FROM jobs"
    )
    conditions = []
    params = []

    if status in STATUSES:
        conditions.append("status = ?")
        params.append(status)
    elif status == "" and not q:
        conditions.append("status != ?")
        params.append(STATUSES[-1])    

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY (status = ?), date_received, id"
    params.append(STATUSES[-1])

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

        if error is None and not request.form.get("confirm_duplicate"):
            related = find_related_jobs(values["plate"], values["vin"])
            if related:
                return render_template(
                    "jobs/new.html",
                    form=values,
                    fuel_types=FUEL_TYPES,
                    car_models=CAR_MODELS,
                    related=related,
                )

        if error is None:
            db = get_db()
            cursor = db.execute(
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
            db.execute(
                "INSERT INTO status_history (job_id, from_status, to_status, changed_by) "
                "VALUES (?, NULL, ?, ?)",
                (cursor.lastrowid, STATUSES[0], g.user["id"]),
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

    return render_template("jobs/new.html", form=form, fuel_types=FUEL_TYPES, car_models=CAR_MODELS)

@bp.route("/<int:job_id>")
def detail(job_id):
    job = get_job_or_404(job_id)
    notes = get_db().execute(
        "SELECT body, created_at FROM notes WHERE job_id = ? ORDER BY id DESC",
        (job_id,),
    ).fetchall()

    parts = get_db().execute(
        "SELECT id, name, quantity, price FROM parts WHERE job_id = ? ORDER BY id",
        (job_id,),
    ).fetchall()

    fault_codes = get_db().execute(
        "SELECT id, code, description, created_at FROM fault_codes "
        "WHERE job_id = ? ORDER BY id",
        (job_id,),
    ).fetchall()

    parts_total, total = calculate_totals(job, parts)

    history = get_db().execute(
        "SELECT h.from_status, h.to_status, h.changed_at, u.username "
        "FROM status_history h LEFT JOIN users u ON u.id = h.changed_by "
        "WHERE h.job_id = ? ORDER BY h.id DESC",
        (job_id,),
    ).fetchall()

    related_count = len(find_related_jobs(job["plate"], job["vin"], exclude_id=job_id))

    return render_template(
        "jobs/detail.html",
        job=job,
        notes=notes,
        fault_codes=fault_codes,
        parts=parts,
        history=history,
        parts_total=parts_total,
        total=total,
        next_label=next_status(job["status"]),
        related_count=related_count
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
        car_models=CAR_MODELS,
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
        db.execute(
            "INSERT INTO status_history (job_id, from_status, to_status, changed_by) "
            "VALUES (?, ?, ?, ?)",
            (job_id, job["status"], following, g.user["id"]),
        )   
        db.commit()

    if request.form.get("back") == "detail":
        return redirect(url_for("jobs.detail", job_id=job_id))
    return redirect(
        url_for(
            "jobs.index",
            q=request.form.get("q") or None,
            status=request.form.get("status") or None,
        )
    )   

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
        flash("The description can be at most 200 characters.")
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
    price_text = request.form.get("price", "").strip()

    error = None
    if not name:
        error = "A part needs a name."
    elif len(name) > 100:
        error = "The part name can be at most 100 characters."
    else:
        try:
            quantity = int(quantity_text)
            price = float(price_text.replace(",", "."))
        except ValueError:
            error = "Quantity must be a whole number and price must be a number."
        else:
            if not 1 <= quantity <= 1000:
                error = "Quantity must be between 1 and 1000."
            elif not 0 <= price <= 100000:
                error = "Price must be between 0 and 100000."

    if error:
        flash(error)
    else:
        db = get_db()
        db.execute(
            "INSERT INTO parts (job_id, name, quantity, price) VALUES (?, ?, ?, ?)",
            (job_id, name, quantity, price)
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

@bp.route("/<int:job_id>/labor", methods=("POST",))
def set_labor(job_id):
    get_job_or_404(job_id)
    labor_text = request.form.get("labor_cost", "").strip()

    try:
        labor_cost = float(labor_text.replace(",","."))
    except ValueError:
        labor_cost = None

    if labor_cost is None or not 0 <= labor_cost <= 100000:
        flash("Labor cost must be a number between 0 and 100000.")      
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
    db = get_db()
    fault_codes = db.execute(
        "SELECT code, description FROM fault_codes WHERE job_id = ? ORDER BY id",
        (job_id,),
    ).fetchall()
    parts = db.execute(
        "SELECT name, quantity, price FROM parts WHERE job_id = ? ORDER BY id",
        (job_id,),
    ).fetchall()
    parts_total, total = calculate_totals(job, parts)

    return render_template(
        "jobs/print.html",
        job=job,
        fault_codes=fault_codes,
        parts=parts,
        parts_total=parts_total,
        total=total,
    )

@bp.route("/<int:job_id>/previous-repairs")
def previous_repairs(job_id):
    job = get_job_or_404(job_id)
    related = find_related_jobs(job["plate"], job["vin"], exclude_id=job_id)
    return render_template("jobs/previous.html", job=job, related=related)

DELIMITERS = {"semicolon": ";", "comma": ","}

def csv_safe(value):
    """Stop Excel from running customer-typed text as a formula"""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text

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

    conditions = []
    params = []
    if start:
        conditions.append("j.date_received >= ?")
        params.append(start.isoformat())
    if end:
        conditions.append("j.date_received <= ?")
        params.append(end.isoformat())

    sql = (
        "SELECT j.*, COALESCE(SUM(p.quantity * p.price), 0) AS parts_total "
        "FROM jobs j LEFT JOIN parts p ON p.job_id = j.id"
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " GROUP BY j.id ORDER BY j.date_received, j.id"
    rows = get_db().execute(sql, params).fetchall()

    def money(value):
        text = f"{value:.2f}"
        return text.replace(".", ",") if delimiter == ";" else text

    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)
    writer.writerow([
        "id", "date_received", "plate", "customer", "phone", "make", "model",
        "year", "vin", "mileage", "engine", "fuel_type", "problem", "status",
        "last_status_change", "parts_total", "labor_cost", "total",
    ])  
    for row in rows:
        parts_total = round(row["parts_total"], 2)
        total = round(parts_total + row["labor_cost"], 2)
        writer.writerow([
            row["id"],
            row["date_received"],
            csv_safe(row["plate"]),
            csv_safe(row["customer_name"]),
            csv_safe(row["phone"]),
            csv_safe(row["make"]),
            csv_safe(row["model"]),
            row["year"],
            csv_safe(row["vin"]),
            row["mileage"],
            csv_safe(row["engine"]),
            row["fuel_type"],
            csv_safe(row["problem"]),
            row["status"],
            localtime(row["status_changed_at"]),
            money(parts_total),
            money(row["labor_cost"]),
            money(total),
        ])  

    filename = f"wrenchtrack_jobs_{date.today().isoformat()}.csv"
    return Response(
        output.getvalue().encode("utf-8-sig"),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@bp.route("/dashboard")
def dashboard():
    db = get_db()

    counts = {s: 0 for s in STATUSES[:-1]}
    for row in db.execute(
        "SELECT status, COUNT(*) AS n FROM jobs WHERE status != ? GROUP BY status",
        (STATUSES[-1],),
    ):
        counts[row["status"]] = row["n"]

    open_jobs = db.execute(
        "SELECT id, plate, make, model, customer_name, status, date_received, "
        "status_changed_at, "
        "MAX(0, CAST(julianday(date('now')) - julianday(date_received) AS INTEGER)) "
        "AS days_in_shop "
        "FROM jobs WHERE status != ? ORDER BY date_received, id",
        (STATUSES[-1],),
    ).fetchall()   
    oldest = open_jobs[:5]
    stuck = [j for j in open_jobs if is_stuck(j)]
    stuck.sort(key=lambda j: days_in_status(j["status_changed_at"]), reverse=True)

    zone = ZoneInfo(current_app.config["SHOP_TIMEZONE"])
    month_start = datetime.now(zone).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start_utc = month_start.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    picked = db.execute(
        "SELECT j.id, j.labor_cost, COALESCE(SUM(p.quantity * p.price), 0) AS parts_total "
        "FROM jobs j "
        "JOIN status_history h ON h.job_id = j.id AND h.to_status = ? AND h.changed_at >= ? "
        "LEFT JOIN parts p ON p.job_id = j.id "
        "GROUP BY j.id",
        (STATUSES[-1], month_start_utc)
    ).fetchall()
    parts_total = round(sum(r["parts_total"] for r in picked), 2)
    labor_total = round(sum(r["labor_cost"] for r in picked), 2)

    return render_template(
        "jobs/dashboard.html",
        statuses=STATUSES[:-1],
        counts=counts,
        stuck=stuck,
        oldest=oldest,
        picked_count=len(picked),
        parts_total=parts_total,
        labor_total=labor_total,
        revenue=round(parts_total + labor_total, 2),
    )             