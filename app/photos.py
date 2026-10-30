import io
import os
import re
import unicodedata

from flask import current_app
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
IMAGE_FORMATS = ["JPEG", "PNG", "HEIF"]
READ_ERRORS = (OSError, ValueError, Image.DecompressionBombError)
NOT_A_PHOTO = "That file could not be read as a photo."

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
    """Keep only plain letters, digits and hyphens, at most 20 of them."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9-]", "", text)[:20]

def photo_folder():
    """Return the private folder where photos are kept."""
    return os.path.join(current_app.instance_path, "photos")

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