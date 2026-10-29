# Photos on jobs

## Why photos

Repair shops photograph cars all the time: damage at check-in, worn parts that were replaced, the dashboard warning that started it all. Right now those photos live in someone's phone gallery, mixed in with everything else, and they are hard to find when a customer asks "was that scratch there before?"

With this feature, photos belong to the job. Anyone who opens the job later sees them, with a name, a Before or After label, and the time they were added.

## How it works in the shop

**At check-in.** A customer brings in a car with a dented rear door. While creating the new job, the mechanic picks three photos from the phone. A name box appears under each one, so they type "Dent, rear left door", "Scratch on bumper" and "Odometer". When the job is saved, all three photos are stored as Before photos.

**During the repair.** On the job page, the mechanic uploads a photo of the worn brake pads they removed and names it "Old pads". The job is already in Repairing, so the form has After selected.

**At pickup.** The customer asks whether the scratch was there before. The mechanic opens the job, and the Before group shows "Scratch on bumper, added 2026-10-29 08:12 by admin".

**Months later.** The same car comes back. Repair history links to the earlier job, and its photos are still on that job's page.

## What you can do

- Add photos while creating a job, or later from the job page.
- Give each photo its own name, and change it later.
- Mark each photo Before or After. The job page shows the two groups separately.
- See when each photo was added and who added it.
- Click a photo to see it full size.
- Remove a photo that was added by mistake.
- Back up all photos into a single zip file with one command.

## Photos from any device

Photos can come from an iPhone, an Android phone or a computer. JPG, PNG and the HEIC format that iPhones use by default are all accepted, so nobody has to change camera settings or convert files first.

Every upload is checked to make sure it really is an image. A file that only pretends to be one, like a document renamed to .jpg, is turned away with a clear message.

## Keeping photos small

A photo straight from a phone is often 3 to 5 MB. Kept as is, a busy shop would fill its storage quickly. So every photo is tidied up on the way in:

1. It is turned upright, so phone photos never show up sideways.
2. It is scaled down so its longest side is at most 2000 pixels. Smaller photos are left at their size.
3. It is saved as a JPEG at quality 75.

The result is usually 300 to 500 KB, about a tenth of the original, and still sharp enough to read a part number or see a small scratch. The original file is not kept.

Both numbers are settings. A shop with plenty of storage can raise them to keep larger, sharper photos without any code changes.

## Privacy

Photos are only visible to logged-in staff. They are kept in a private folder on the server, not in the public part of the site, so a photo cannot be opened by guessing its address.

Phone photos carry hidden details, such as when the photo was taken and sometimes where. WrenchTrack never shows these on any page. They stay inside the saved file, so they can still be checked later by downloading the photo, for example to confirm when damage was first recorded. If photos are ever shown on a public page, these details will be removed first.

## Readable file names

Saved photos get names that make sense outside the app too, built from the job number, the plate, the car make and a photo number:

`job42_SK1234AB_skoda_3.jpg`

So a folder of photos, or a backup zip, can be browsed by hand and every file can be traced back to its job. Special characters are cleaned out (Škoda becomes skoda), and no photo ever overwrites another. Jobs without a plate simply skip that part.

## Before and After

Every photo is either Before or After. The form picks a sensible default from where the job is: Before while the car is being received and diagnosed, After once the repair has started. Photos added while creating a new job are always Before. The default can always be changed by hand.

## Backups

The photos have their own backup command, separate from the database backup. It packs every photo into one zip file with the date in its name. Keeping it separate means the regular database backup stays small and quick, and the photo backup can be run whenever it suits.

## Good to know

- If the new job form has to be shown again, for example because a required field was left empty, the browser forgets the chosen photos. The form says so and asks for them to be chosen again. Nothing is saved until the job itself is saved.
- If one of several photos on the new job form is not a valid image, nothing is saved, and the form says which file was the problem.
- Photos do not appear on the printed job ticket or in the CSV export.
- Removing a job's photo also removes the file, so storage is not wasted on photos nobody can see.

## Build order

1. Add the image libraries and the photo settings.
2. Add a place in the database to record each photo.
3. Teach the app to check, resize and save a photo.
4. Show a photo to logged-in staff.
5. Upload photos from the job page.
6. Show photos on the job page in Before and After groups.
7. Rename and remove photos.
8. Add photos to the new job form, with a name box for each one.
9. Add the photo backup command.
10. Update the README and TODO.

The first six steps give a working version: photos can be uploaded and viewed on any job.

## How it will be tested

- Photos from an iPhone, an Android phone and a computer all upload and appear upright.
- A fake image, an unsupported file type and an empty upload are all turned away with a clear message.
- Photos cannot be opened without logging in.
- A downloaded photo still carries its original date taken.
- Job pages look right with no photos, with only Before photos, and with both groups.
- A photo name containing code is shown as plain text, never run.
- The new job form behaves correctly when it has to be shown again.
- Removing a photo and adding another never overwrites an existing file.
- The backup zip opens and contains every photo.

## Not included for now

- Reordering photos or choosing a cover photo for the job list.
- A log of who renamed or removed which photo. This will come with the planned activity log.
- Video uploads, which need different tools and much more storage.
