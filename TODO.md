# TODO

## Next, roughly in order

- Paid or unpaid flag on jobs, since a car can be picked up before the bill is paid.
- Pagination for the job list.
- A "Waiting for approval" status for when the customer has to OK the repair first. This touches the status list, stuck thresholds, CSS, the CHECK constraint and a migration, so it needs care.
- Assign a mechanic to each job.
- Service reminders based on mileage and the date of the last visit.
- Cost price and sell price on parts.
- Fault code lookup.
- Full activity log: a record of what every user does (logins and logouts, new jobs, edits, status changes, photos, parts, notes), with when it happened and who did it.
- Radio repair: a second job type for car radios and head units (for example Audi MMI 3G, VW RNS 510). Make and model but no plate or VIN, plus fields such as hardware or software fault and the software version before and after. Photos work the same as on car jobs.
- A QR code status page where customers can check their job. This would be the first public page, so privacy needs thinking through.
- pytest tests and GitHub Actions.
- Scheduled backups.

## Done

- "Car is ready" message: jobs in Ready show a prepared message with the total, ready to edit and copy to the customer.
- Plate autofill: typing a known plate on a new job fills in the customer and car details from the last visit, without replacing anything already typed.
- Photos on jobs: add photos on the new job form or the job page, with a name and a Before or After label. The job page shows them in two groups, and they can be renamed or removed. Uploads are checked and resized automatically, HEIC is supported, and backup-photos saves them all to one zip.
- Same-car warning: it now opens without reloading the page, so the form and any chosen photos stay as they were.
- Wider search: the job list search also finds jobs by phone number, VIN and fault code.
- Currency setting: CURRENCY in .env (MKD by default) is shown after every amount on the detail, print and dashboard pages.
- Typo and small error fixes across the README, templates and code. This fixed the broken print page, renamed "previous repairs" to "Repair history" in the README and the URL, and removed trailing spaces.

## Housekeeping

- Remove the unused home.html or find a use for it.
- Take new README screenshots.
