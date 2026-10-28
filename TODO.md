# TODO

## In progress

- Nothing right now.

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
- Photos on jobs, for things like damage at check-in.
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
