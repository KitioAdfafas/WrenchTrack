import difflib

from .db import get_db

ALIAS_GROUPS = [
    {"vw", "volkswagen"},
    {"merc", "mercedes", "mercedes-benz", "benz"},
    {"skoda", "škoda"},
]

TERM_TO_GROUP = {term: group for group in ALIAS_GROUPS for term in group}

def can_fuzzy(word):
    """True if the word is long enough for typo matching (4+ characters, no digits)."""
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
    """Lowercase and keep only letters and digits, so SR-1234-AG becomes sr1234ag."""
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

def find_related_jobs(plate, vin, exclude_id=0):
    """Other jobs of the same car: same plate, or same VIN (only if both are filled in)."""
    plate_key = squash(plate)
    vin_key = squash(vin or "")
    rows = get_db().execute(
        "SELECT * FROM jobs WHERE id != ? ORDER BY date_received DESC, id DESC",
        (exclude_id,),
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
