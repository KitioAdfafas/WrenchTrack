import csv
import io

from .db import get_db
from .shop import PARTS_TOTAL_SQL, job_total, localtime

DELIMITERS = {"semicolon": ";", "comma": ","}

def csv_safe(value):
    """Stop Excel from running customer-typed text as a formula."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text

def csv_money(value, delimiter):
    """Two decimals, with a decimal comma when the columns are split by semicolons."""
    text = f"{value:.2f}"
    return text.replace(".", ",") if delimiter == ";" else text

def find_export_jobs(start, end):
    """Jobs received between start and end (either may be None), with their parts total."""
    conditions = []
    params = []
    if start:
        conditions.append("j.date_received >= ?")
        params.append(start.isoformat())
    if end:
        conditions.append("j.date_received <= ?")
        params.append(end.isoformat())

    sql = (
        "SELECT j.*, " + PARTS_TOTAL_SQL + " "
        "FROM jobs j LEFT JOIN parts p ON p.job_id = j.id"
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " GROUP BY j.id ORDER BY j.date_received, j.id"
    return get_db().execute(sql, params).fetchall()

def field(key):
    """A column that writes one stored field as it is."""
    return lambda job, delimiter: job[key]

def money_field(key):
    """A column that writes an amount in the format the delimiter needs."""
    return lambda job, delimiter: csv_money(job[key], delimiter)

def status_change_time(job, delimiter):
    """The last status change in shop time."""
    return localtime(job["status_changed_at"])

EXPORT_COLUMNS = [
    ("id", field("id")),
    ("date_received", field("date_received")),
    ("plate", field("plate")),
    ("customer", field("customer_name")),
    ("phone", field("phone")),
    ("make", field("make")),
    ("model", field("model")),
    ("year", field("year")),
    ("vin", field("vin")),
    ("mileage", field("mileage")),
    ("engine", field("engine")),
    ("fuel_type", field("fuel_type")),
    ("problem", field("problem")),
    ("status", field("status")),
    ("last_status_change", status_change_time),
    ("parts_total", money_field("parts_total")),
    ("labor_cost", money_field("labor_cost")),
    ("total", money_field("total")),
]

def export_job(row):
    """One job as a dict, with the parts total and the total worked out once."""
    job = dict(row)
    job["parts_total"] = round(row["parts_total"], 2)
    job["total"] = job_total(job["parts_total"], row["labor_cost"])
    return job

def write_safe_row(writer, cells):
    """Write one CSV line with every cell made safe for Excel."""
    writer.writerow([csv_safe(cell) for cell in cells])

def export_csv_bytes(rows, delimiter):
    """The whole CSV file for these job rows, as UTF-8 with a BOM for Excel."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)
    write_safe_row(writer, [header for header, _ in EXPORT_COLUMNS])
    for row in rows:
        job = export_job(row)
        write_safe_row(writer, [value(job, delimiter) for _, value in EXPORT_COLUMNS])
    return output.getvalue().encode("utf-8-sig")
