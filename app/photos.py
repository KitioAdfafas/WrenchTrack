import io
import os
import re
import sqlite3
import unicodedata
import zipfile

import click
from flask import current_app, flash, g, request
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from .db import backup_target
from .status import STATUSES

register_heif_opener()

ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".heic", ".heif")
PHOTO_ACCEPT = ",".join(ALLOWED_EXTENSIONS) + ",image/*"
IMAGE_FORMATS = ["JPEG", "PNG", "HEIF"]
READ_ERRORS = (OSError, ValueError, Image.DecompressionBombError)
NOT_A_PHOTO = "That file could not be read as a photo."

PHOTO_STAGES = ["before", "after"]

def read_photo(file):
    """Open an uploaded file as an image. Returns (image, error)."""
    if file is None or file.filename == "":
        return None, "Choose a photo to upload."

    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return None, "Photos must be JPG, PNG, HEIC or HEIF."

    try:
        image = Image.open(file.stream, formats=IMAGE_FORMATS)
        image.load()
    except READ_ERRORS:
        return None, NOT_A_PHOTO

    return image, None

def shrink_photo(image):
    """Turn a photo upright, scale it down and return it as JPEG bytes."""
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    max_side = current_app.config["PHOTO_MAX_SIDE"]
    image.thumbnail((max_side, max_side))

    buffer = io.BytesIO()
    image.save(
        buffer,
        "JPEG",
        quality=current_app.config["PHOTO_QUALITY"],
        exif=image.getexif(),
    )
    return buffer.getvalue()

def prepare_photo(file):
    """Check an upload and turn it into JPEG bytes. Returns (data, error)."""
    image, error = read_photo(file)
    if error:
        return None, error
    try:
        return shrink_photo(image), None
    except READ_ERRORS:
        return None, NOT_A_PHOTO

def clean_name_part(text):
    """Strip text down to plain letters, digits and hyphens, 20 characters max."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9-]", "", text)[:20]

def photo_folder():
    """Return the private folder where photos are kept."""
    return os.path.join(current_app.instance_path, "photos")

def remove_photo_file(filename):
    """Delete a saved photo. A file that is already gone is fine."""
    try:
        os.remove(os.path.join(photo_folder(), filename))
    except FileNotFoundError:
        pass

def save_photo(data, job):
    """Write JPEG bytes to the photo folder and return the new file name."""
    folder = photo_folder()
    os.makedirs(folder, exist_ok=True)

    plate = clean_name_part(job["plate"])
    make = clean_name_part(job["make"]).lower()
    parts = [f"job{job['id']}", plate, make]
    base = "_".join(part for part in parts if part)

    number = 1
    while True:
        filename = f"{base}_{number}.jpg"
        try:
            with open(os.path.join(folder, filename), "xb") as f:
                f.write(data)
            return filename
        except FileExistsError:
            number += 1

def default_photo_stage(status):
    """Before until the repair starts, After from then on."""
    if STATUSES.index(status) < STATUSES.index("Repairing"):
        return "before"
    return "after"

def ask_for_photos_again():
    """Remind the user when the form comes back after photos were chosen."""
    if any(file.filename for file in request.files.getlist("photos")):
        flash("Please choose the photos again.")

def read_photos():
    """Check every chosen photo. Return (photos, error)."""
    files = [file for file in request.files.getlist("photos") if file.filename]
    names = request.form.getlist("photo_names")

    photos = []
    for position, file in enumerate(files):
        name = names[position].strip() if position < len(names) else ""
        if len(name) > 100:
            return [], f"{file.filename}: A photo name can be at most 100 characters."

        data, error = prepare_photo(file)
        if error:
            return [], f"{file.filename}: {error}"
        photos.append((data, name))

    return photos, None

def save_job_photos(db, job, photos, stage):
    """Save the photos without committing. Written files are removed on failure."""
    written = []
    try:
        for data, name in photos:
            filename = save_photo(data, job)
            written.append(filename)
            db.execute(
                "INSERT INTO photos (job_id, filename, name, stage, created_by) "
                "VALUES (?, ?, ?, ?, ?)",
                (job["id"], filename, name or None, stage, g.user["id"]),
            )
    except (OSError, sqlite3.Error):
        for filename in written:
            remove_photo_file(filename)
        raise

@click.command("backup-photos")
def backup_photos_command():
    """Save every photo into one zip file in instance/backups."""
    folder = photo_folder()
    photos = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
    if not photos:
        click.echo("There are no photos to back up.")
        return

    target = backup_target("photos", "zip")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_STORED) as archive:
        for name in photos:
            archive.write(os.path.join(folder, name), arcname=name)

    click.echo(f"Backup saved: {target}")

def init_app(app):
    """Add the photo backup command and the accepted upload types for templates."""
    app.cli.add_command(backup_photos_command)
    app.jinja_env.globals["photo_accept"] = PHOTO_ACCEPT
