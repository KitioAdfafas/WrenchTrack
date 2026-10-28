# TODO

## In progress

- Wider search: let the job list search also find jobs by phone number, VIN and fault code. I'm planning this first, then building it.

## Next, roughly in order

- Currency setting. Amounts are shown as plain numbers with two decimals right now.
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

## Housekeeping

- Fix README typos ("bu", "previos", "soured") and rename "previous repairs" to "Repair history".
- Remove the unused home.html or find a use for it.
- Take new README screenshots.
