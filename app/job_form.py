import json
from datetime import date
from pathlib import Path

from .shop import shop_today

FUEL_TYPES = ["petrol", "diesel", "hybrid", "electric"]

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

JOB_FIELDS = [
    "customer_name",
    "phone",
    "make",
    "model",
    "year",
    "plate",
    "vin",
    "mileage",
    "engine",
    "fuel_type",
    "problem",
    "date_received",
]

OPTIONAL_FIELDS = ["vin", "engine"]

NUMBER_FIELDS = ["year", "mileage"]

UPPERCASE_FIELDS = ["plate", "vin"]

LAST_VISIT_FIELDS = [field for field in JOB_FIELDS if field not in ("plate", "mileage", "problem")]

def read_job_form(form):
    """Clean the submitted form. Returns (values, error). error is None if valid."""
    values = {}
    for field in JOB_FIELDS:
        text = form.get(field, "").strip()
        if field in UPPERCASE_FIELDS:
            text = text.upper()
        values[field] = text

    for field in JOB_FIELDS:
        if field not in OPTIONAL_FIELDS and not values[field]:
            return values, "Please fill in every required field."

    if values["fuel_type"] not in FUEL_TYPES:
        return values, "Pick a valid fuel type."

    try:
        year = int(values["year"])
        mileage = int(values["mileage"])
    except ValueError:
        return values, "Year and mileage must be whole numbers."

    if not 1950 <= year <= shop_today().year + 1:
        return values, "That year does not look right."
    if mileage < 0:
        return values, "Mileage cannot be negative."

    try:
        date.fromisoformat(values["date_received"])
    except ValueError:
        return values, "Date must look like 2026-10-10."

    return values, None

def job_params(values):
    """Turn checked form values into database values: whole numbers, and NULL for empty optional fields."""
    params = {}
    for field in JOB_FIELDS:
        value = values[field]
        if field in NUMBER_FIELDS:
            value = int(value)
        elif field in OPTIONAL_FIELDS and not value:
            value = None
        params[field] = value
    return params
