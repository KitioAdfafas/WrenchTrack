# WrenchTrack

WrenchTrack is a web app for auto repair shops to manage repair jobs from vehicle check-in to pickup. Built with **Python, Flask, and SQLite**.

## Features

- Staff login; accounts are created from the command line
- Create and edit repair jobs with customer and vehicle details
- Track job status from **Received** to **Picked up**
- Search bu customer, plate, make, or model, and filter by status
- Dashboard for active jobs and jobs that may be waiting too long
- Add notes, OBD fault codes, parts, and labor costs
- View previos repairs linked by license plate or VIN
- Print job tickets and export jobs to CSV
- Back up the database and apply non-destructive database migrations

## Getting started (Windows PowerShell)

```powershell
git clone https://github.com/KitioAdfafas/Wrenchtrack.git
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

**Warning:** `init-db` deletes existing data. For an existing database, use `flask --app app migrate-db` instead. To make a backup, run `flask --app app backup-db`.

## Notes

Set `SHOP_TIMEZONE` in `.env` to choose the shop's time zone (defaults to `Europe/Skopje`). For public deployment, use a production WSGI server and HTTPS; do not expose Flask's development server directly to the internet.

## Data attribution

The car make and model list is soured from

[car-list](https://github.com/matthlavacka/car-list)
by [matthlavacka](https://github.com/matthlavacka)