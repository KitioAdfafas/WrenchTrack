# TODO

## In progress

- Photos on jobs: upload on the new job form and on the job page, a name for each photo, before and after groups, shrinking with Pillow, HEIC support and a backup-photos command. Full plan in docs/photos-plan.md.

## Next, roughly in order

- Plate autofill: when a known plate is typed on a new job, fill in the customer and car details from the last visit.
- Paid or unpaid flag on jobs, since a car can be picked up before the bill is paid.
- Pagination for the job list.
- A "car is ready" button that prepares a message to send to the customer.
- A "Waiting for approval" status for when the customer has to OK the repair first. This touches the status list, stuck thresholds, CSS, the CHECK constraint and a migration, so it needs care.
- Assign a mechanic to each job.
- Service reminders based on mileage and the date of the last visit.
- Cost price and sell price on parts.
- Fault code lookup.
- Full activity log: a record of what every user does (logins and logouts, new jobs, edits, status changes, photos, parts, notes), with when it happened and who did it. Needs a log table and a small helper that every route calls.
- Radio repair: a second job type for car radios (for example Audi MMI 3G, VW RNS 510). Same make and model, no plate or VIN, new fields such as hardware or software problem and the software version before and after. Photos must work for it too. Changes the "Cars only" rule, so it needs its own planning first. Leaning toward a job type column plus a radio details table, which means a careful migration to relax the NOT NULL rules on the jobs table.
- A QR code status page where customers can check their job. This would be the first public page, so privacy needs thinking through.
- pytest tests and GitHub Actions.
- Scheduled backups.

## Done

- Wider search: the job list search also finds jobs by phone number, VIN and fault code.
- Currency setting: CURRENCY in .env (MKD by default) is shown after every amount on the detail, print and dashboard pages.
- Typo and small error fixes across the README, templates and code. This fixed the broken print page, renamed "previous repairs" to "Repair history" in the README and the URL, and removed trailing spaces.

## Housekeeping

- Remove the unused home.html or find a use for it.
- Take new README screenshots.
