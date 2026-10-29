# Photos on jobs: plan

## Why

Staff need to photograph cars at check-in (for example existing damage) and during or after the repair, and see those photos later on the job page. The app runs on PythonAnywhere where disk space is tight, so photos are shrunk on upload. Later the app may move to a self-hosted server with more space, so the shrinking settings must be easy to change.

## What it does

- Photos can be added on the new job form and on the job page after the job exists.
- Each photo has its own name, for example "Scratch on rear bumper". The name is optional and can be changed later.
- Each photo is marked Before or After. The job page shows two groups, Before and After.
- Each photo shows when it was added and by whom, for example "Added 2026-10-29 15:30 by kiril", in shop time.
- Clicking a preview opens the photo full size.
- Photos can be renamed and removed.
- Old jobs opened from Repair history show their photos on their own job page. The Repair history list itself shows no previews or counts.

## Rules

- Accepted files: .jpg, .jpeg, .png, .heic, .heif, from iPhone, Android and PC.
- The server opens every file with Pillow to check it is a real image. Checking the file name alone is not enough.
- Every photo is saved as a JPEG. Quality comes from PHOTO_QUALITY (default 75). The longest side is at most PHOTO_MAX_SIDE pixels (default 2000). Both live in .env, like CURRENCY.
- The original upload is not kept.
- Photos are turned the right way up before saving. PNG transparency is flattened to RGB.
- The date taken and the location stay inside the saved JPEG. The app never reads or shows them. Staff can download a photo and see them in Windows under Properties, Details. If a public page (like the planned QR status page) ever shows photos, they must be cleaned of this data first.
- Files are stored in instance/photos, never in static/.
- Photos are served through a route that checks the photo belongs to that job. Login is required automatically by require_login in auth.py.
- MAX_CONTENT_LENGTH caps one upload request at about 50 MB.
- New dependencies: Pillow (shrink and convert) and pillow-heif (read iPhone HEIC and HEIF files).

## File names

- Format: job id, plate, make, model if needed, photo number. Examples:
  - car job: job42_SK1234AB_skoda_3.jpg
  - future radio job with no plate: job57_vw_rns510_1.jpg
- Empty parts are skipped, so the same code works for jobs without a plate.
- Plate and make are typed by people, so they are cleaned down to plain ASCII letters, digits and hyphens before going into a file name. Accented letters are turned into plain ones (Škoda becomes skoda), not dropped.
- The photo number is the next free number for that job. Count the job's photos plus one, then keep counting up while a file with that name already exists. This avoids overwriting after a photo is removed.
- If the plate is edited later, old photos keep the old plate in their file name. That is fine, the database row is what links a photo to its job.

## Database

New table, added to both schema.sql (with a DROP TABLE line) and migrations.sql (CREATE TABLE IF NOT EXISTS, plus an index on job_id):

- id
- job_id, references jobs, ON DELETE CASCADE
- filename (the stored file name)
- name (optional, the photo name shown on the page)
- stage, 'before' or 'after', with a CHECK constraint
- created_at, UTC, default now
- created_by, references users

No columns for date taken or location. No video column for now; adding one later is a simple, safe migration.

## Decisions made by Claude (change any of them)

- Photos added on the new job form are always Before.
- On the job page, Before or After defaults from the status: Before until Repairing, After from Repairing on.
- Previews are the same file shown smaller with CSS. No separate thumbnail files.
- Photos do not appear on the print ticket or the CSV export.
- Image processing helpers go in a new module app/photos.py. Routes stay in jobs.py.

## Steps

| # | Step | Files | Time |
|---|------|-------|------|
| 1 | Install Pillow and pillow-heif, add them to requirements.txt. Add PHOTO_QUALITY and PHOTO_MAX_SIDE to .env.example and the config, and set MAX_CONTENT_LENGTH. Run a flask command to confirm the app still imports. | requirements.txt, .env.example, app/__init__.py | 15 to 20 min |
| 2 | Photos table in schema.sql and migrations.sql. Run backup-db and migrate-db, then check init-db on a fresh database. | schema.sql, migrations.sql | 20 min |
| 3 | Photo helper part 1: check the extension, open with Pillow, return a plain error message if it is not a real image. | app/photos.py | 20 to 25 min |
| 4 | Photo helper part 2: turn upright, convert to RGB, shrink, save as JPEG with the date and location kept. Build the file name from the job and skip empty parts. | app/photos.py | 35 to 45 min |
| 5 | Route that sends a photo file, only if the photo belongs to that job. | jobs.py | 15 min |
| 6 | Upload on the job page: form with file, name and Before or After, plus an add_photo route modeled on add_part. | jobs.py, detail.html | 25 to 30 min |
| 7 | Show photos on the job page: Before and After groups, previews with names, "Added ... by ..." in shop time, click for full size, a little CSS. | jobs.py detail, detail.html, style.css | 30 min |
| 8 | Rename and remove: two POST routes modeled on delete_part. Remove also deletes the file from disk. | jobs.py, detail.html | 25 min |
| 9 | New job form, server side: accept several photos and their names, check them all before saving anything, save them after the job is saved. If the form comes back (error or the same car dialog), show "Please choose the photos again". | jobs.py new, new.html | 30 to 40 min |
| 10 | New job form, browser side: JavaScript adds a name box for each chosen photo. Photo fields show only on New, not on Edit. | new.html | 20 to 30 min |
| 11 | backup-photos command: zip instance/photos into instance/backups with a date in the name. Store without compressing (JPEGs do not shrink further). | db.py | 20 min |
| 12 | Finish: README (dependencies, HEIC, backup-photos), TODO.md, deploy to PythonAnywhere (pip install, backup-db, migrate-db, reload), try it on Termux. | README.MD, TODO.md | 20 to 30 min |

Total: about 5 to 6 hours, 3 to 4 sessions. Steps 1 to 6 give a first working version.

## Checks

- Upload a real iPhone HEIC, an Android JPG and a PC PNG. All show the right way up.
- Upload a text file renamed to .jpg. It is rejected with a plain message.
- Open a photo URL while logged out. It redirects to login.
- Open a photo URL with the wrong job id. It returns 404.
- Download a photo and check Windows shows the date taken.
- Open the job page with no photos, and for a Picked up job.
- Submit the new job form with photos and a missing field. The form asks to choose the photos again and nothing is saved.
- Remove a photo, then upload another. No file is overwritten.
- Run backup-photos and open the zip.

## Later, not part of this plan

- Full activity log, which will also cover photo uploads, renames and removals.
- Radio repair as a second job type. Photos should work for it without changes thanks to the file name rule above.
- Video uploads would need ffmpeg and much more disk space.
