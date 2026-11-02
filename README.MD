# WrenchTrack

WrenchTrack is a web app for car repair shops. It tracks each repair job from check-in to pickup, and it's built with Python, Flask and SQLite.

## Features

- Staff login; accounts are created from the command line
- Create and edit repair jobs with customer and vehicle details
- Plate autofill: a known plate fills in the customer and car details from the last visit
- Track job status from Received to Picked up
- Search by customer, plate, make, model, phone number, VIN, or fault code, and filter by status
- Dashboard for active jobs and jobs that may be waiting too long
- Add notes, OBD fault codes, parts, and labor costs
- Add photos to a job (JPG, PNG or HEIC) with a name and a Before or After label
- Repair history: see earlier jobs linked by license plate or VIN
- Print job tickets and export jobs to CSV
- Prepare a "car is ready" message with the total, ready to copy to the customer
- Back up the database and photos, and update the database without losing data

## Getting started (Windows PowerShell)

```powershell
git clone https://github.com/KitioAdfafas/WrenchTrack.git
cd WrenchTrack
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and replace `SECRET_KEY` with a long random value.

Initialize the database, create a user, and start the development server:

```powershell
flask --app app init-db
flask --app app create-user admin
flask --app app run --debug
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) and log in.

**Warning:** `init-db` deletes existing data. For an existing database, use `flask --app app migrate-db` instead. To make a backup, run `flask --app app backup-db`. To back up photos, run `flask --app app backup-photos`.

## Settings

Set `SHOP_TIMEZONE` in `.env` to choose the shop's time zone (defaults to `Europe/Skopje`), and `CURRENCY` to choose the currency shown after amounts (defaults to `MKD`).

Set `PHOTO_QUALITY` to choose the JPEG quality of the saved photos (defaults to `75`), and `PHOTO_MAX_SIDE` to choose the longest side in pixels (defaults to `2000`).

## Planned work

See [TODO.md](TODO.md).

## Data attribution

The car make and model list comes from
[car-list](https://github.com/matthlavacka/car-list)
by [matthlavacka](https://github.com/matthlavacka).
