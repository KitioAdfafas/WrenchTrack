# Redesign Step 6: Month Strip and Phone Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the dashboard month strip (2 by 2 at every width) and make the dashboard and the top bar work well on a phone at 360 to 390px.

**Architecture:** CSS changes in `app/static/style.css`, plus two small wrapper elements in `app/templates/base.html` so the phone top bar can be laid out. No Python, route or data changes. A scratchpad screenshot script measures the pages in headless Chrome and turns the spec's goals into pass or fail checks.

**Tech Stack:** Flask 3, Jinja, plain CSS, headless Chrome (`C:\Program Files\Google\Chrome\Application\chrome.exe`) for checks only.

**Spec:** `docs/superpowers/specs/2026-11-27-dashboard-step-6-design.md`

Scratchpad folder, written `S` below: `C:\Users\Kiril\AppData\Local\Temp\claude\17f934235a426e47\611ff934-0259-4453-b00c-49b55b21276a\scratchpad`. The behavior check script is `S\check\smoke.py` and its baseline from main at `b506c6b` is `S\check\base` (230 snapshots). Nothing in `S` is committed.

## Global Constraints

- Plain HTML and CSS. No JavaScript in the app, no new dependency, no CSS framework.
- All colors, shadows and corner sizes come from the CSS variables in `:root`. Do not add raw color values.
- Red (`--late`) means late or stuck and nothing else.
- Only position tags, the late tag, status stripes and sector segments are slanted.
- Every tappable thing is at least 44px tall on touch screens.
- Nothing may scroll sideways on a phone.
- Amounts keep the normal money format, for example "38400.00 MKD". No new number format.
- Move keeps returning to the car panel (`#car`). The tower order stays: longest in the shop first.
- Desk width (64rem and up) looks the same as before, apart from the month strip.
- Never use em dashes or emojis in code comments, interface text or commit messages.
- One feature per commit, short plain commit message, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Commands are for Windows PowerShell, run from `C:\Users\Kiril\WrenchTrack`.

## Review Focus

1. **360px phones** (the Samsung S10 the app has run on is 360 CSS px wide): every dashboard scenario and every page passes the sideways-scroll check at 360, not only at 390. Pinned in Task 1 (widths list) and checked in Tasks 2 to 5.
2. **A seven-digit month total** (1234567.89 MKD): the number stays on one line inside its cell at 360px and at 1024px. Pinned by the `full` scenario in Task 1, checked in Task 2.
3. **Two-digit positions** (10, 11, 12) in the tower: the number fits inside the slanted tag after the tag is narrowed. Pinned by the `full` scenario (12 open cars) and the `posCut` metric, checked in Task 4.
4. **A long user name** ("aleksandar.stojanovski") in the phone top bar: it is cut with an ellipsis and Log out stays fully visible and at least 44px tall. Pinned by the `full` scenario, checked in Task 3.
5. **A 1024px laptop**, just above the 64rem switch to two columns: the strip's currency drops under the number cleanly and the tower rows keep their desk layout. Pinned by the 1024 width, checked in Tasks 2 and 4.

---

### Task 1: Screenshot and measurement script (scratchpad, not committed)

**Files:**
- Create: `S\check\shots.py`

**Interfaces:**
- Produces: `python S\check\shots.py OUT_DIR [--compare BASE_DIR]`. It writes `OUT_DIR\<scenario>_<page>_<width>.png`, `OUT_DIR\metrics.json` (a list of `{scenario, page, width, ...metrics}`), prints one line per page and width, prints a `FAIL ...` line for every failed check, and exits 1 if any check failed.

- [ ] **Step 1: Build the scenarios.** Each scenario is its own temporary instance folder made with `make_app` and `init_db` from `smoke.py` (import them, do not copy), so the real `instance` folder is never touched. Log in through the session (`user_id`) the way `smoke.py` does.
  - `empty`: one user `tester`, no jobs.
  - `one`: user `tester`, a single open car that is not late, nothing picked up this month.
  - `fixture`: a copy of `S\check\fixture\wrenchtrack.sqlite` (5 open cars, 2 picked up, fault codes, a late car).
  - `full`: user `aleksandar.stojanovski`; 12 open cars across all five open statuses, at least 4 of them late; plates in the form `SK-1234-AB` (10 characters, the longest normal plate) plus one `BT 123 AB`; one car `Mercedes-Benz` `GLE 350 d 4MATIC Coupe`; picked up this month with parts and labor adding up to exactly 1234567.89; the selected car (`?job=<id>`) has no fault codes. Write `date_received`, `status_changed_at` and a `status_history` row for Picked up with `changed_at` inside the current shop month.

- [ ] **Step 2: Render and capture.** Pages: `/jobs/dashboard` for every scenario; for `fixture` also `/jobs/`, `/jobs/1`, `/jobs/1/edit`, `/jobs/new`, `/jobs/1/repair-history`, `/jobs/1/print`, and `/login` while logged out. Widths: 360, 390, 1024, 1440. Get each page with the test client, rewrite `"/static/` to `"file:///C:/Users/Kiril/WrenchTrack/app/static/`, add the metrics script before `</body>`, and save it as `OUT_DIR\html\<name>.html`. Then run Chrome twice per file and width: `--headless=new --hide-scrollbars --allow-file-access-from-files --virtual-time-budget=3000 --window-size=W,3000 --screenshot=PNG` and the same flags with `--dump-dom` to read the metrics back.

- [ ] **Step 3: The metrics script.** It writes one JSON object into `<pre id="metrics">`:
  - `sw`, `vw`: `document.documentElement.scrollWidth`, `innerWidth`
  - `topbar`: `.topbar` offsetHeight
  - `tabMin`: smallest offsetHeight of `.topbar a` other than `.brand` (null if none)
  - `logout`: offsetHeight of `.who button` (null if none)
  - `nameCut`: true if `.who-name` exists and its scrollWidth is above its clientWidth
  - `plateCut`: plate texts in `.tower-row .plate span` whose scrollWidth is above their clientWidth
  - `posCut`: count of `.pos span` wider than their `.pos`
  - `carMin`: smallest clientWidth of `.tower-row .car` (null if none)
  - `gapSmallLines`: largest `round(height / lineHeight)` over `.gap small`
  - `monthOverflow`: count of `.month dd` whose scrollWidth is above their clientWidth
  - `monthBroken`: count of `.month dd` whose number (the text before the first space) spans more than one line, checked with `Range.getClientRects()` on that part of the text node

- [ ] **Step 4: The checks.**
  - Always:
    - `sw <= vw`
    - `logout >= 44` and `tabMin >= 44` when not null
    - `monthOverflow == 0` and `monthBroken == 0`
    - `posCut == 0`
    - `plateCut` holds no plate of 10 characters or fewer
  - With `--compare BASE_DIR`:
    - on the `fixture` dashboard at 390, `topbar` is lower than in the base
    - on every dashboard at 360 and 390, `carMin` is higher than in the base
    - at 1440, `topbar` and `carMin` equal the base

- [ ] **Step 5: Take the visual baseline from main.**

Run: `& .venv\Scripts\python.exe S\check\shots.py S\shots\base`
Expected: it runs to the end and writes PNGs for 4 scenarios. Some `FAIL` lines are expected on main: they are the goals of Tasks 2 to 4. Report them to Claude, together with the base `topbar` and `carMin` values at 360, 390 and 1440. Claude looks at the base PNGs before Task 2 starts.

---

### Task 2: Month strip, 2 by 2 at every width

**Files:**
- Modify: `app/static/style.css` (the `.month` rules near line 726 and the `@media (min-width: 64rem)` block)

**Interfaces:**
- Consumes: `shots.py` from Task 1. No markup change: `.month`, `.month div`, `.month dt` and `.month dd` already exist in `dashboard.html`.

- [ ] **Step 1: Confirm the failing checks.** Run `shots.py S\shots\t2 --compare S\shots\base` and note any `monthBroken` or `monthOverflow` failures.
- [ ] **Step 2: Change the strip CSS.**
  - `.month dd`: replace `overflow-wrap: anywhere` with `overflow-wrap: normal`, so a number never breaks and only the currency drops to the next line. Set `line-height: 1.15`. Keep `font-size: 1.375rem` below 64rem.
  - At 64rem and up: `.month dd` gets `font-size: 1.625rem` (the about 26px Figure style) and `.month div` gets `padding: 1.125rem 1.5rem`.
  - The grid stays `repeat(2, minmax(0, 1fr))` at every width.
  - If 1234567.89 still overflows at 360, lower the phone size to `1.25rem`, and go no lower.
- [ ] **Step 3: Run the checks.** Run `shots.py S\shots\t2 --compare S\shots\base`. Expected: no `month*` failures in any scenario or width. Then look at `full_dashboard_360.png`, `full_dashboard_1024.png` and `fixture_dashboard_1440.png`: four cells, currency under the number only where it does not fit.
- [ ] **Step 4: Run the behavior check.** Run `& .venv\Scripts\python.exe S\check\smoke.py S\check\t2`, then `git diff --no-index --stat S\check\base S\check\t2`. Expected: no differences (CSS only).
- [ ] **Step 5: Hand to Claude for review.** Hand over the diff, the shots output and the PNG paths, then wait for the go-ahead.
- [ ] **Step 6: Commit and push.** Commit message: `Lay out the month totals strip 2 by 2 at every width`. Then run `git push origin main` as a single command. If the push is rejected, stop and report to Claude.

---

### Task 3: Phone top bar

**Files:**
- Modify: `app/templates/base.html` (the `nav.topbar` block)
- Modify: `app/static/style.css` (the `.topbar` and `.who` rules near line 129, plus the `@media (max-width: 40rem)` block)

**Interfaces:**
- Consumes: `shots.py` (`topbar`, `tabMin`, `logout`, `nameCut`).
- Produces: two new classes that later steps may style: `.nav` wraps the Dashboard, Jobs and New job links, and `.who-name` wraps the user name inside `.who`.

- [ ] **Step 1: Change the markup.** In `base.html`, inside `{% if g.user %}`, put the three links inside `<span class="nav">` and the user name inside `<span class="who-name">`. Keep the `aria-current` logic and the Log out form, with its CSRF field, exactly as they are.
- [ ] **Step 2: Change the desk CSS.** `.nav { display: flex; }`. At 1440 the bar must render the same as the base: compare `fixture_dashboard_1440.png`, and `topbar` must be equal.
- [ ] **Step 3: Change the phone CSS** (below 40rem).
  - `.topbar` becomes a grid with columns `minmax(0, 1fr) auto`: brand in row 1, column 1; `.who` in row 1, column 2; `.nav` across both columns in row 2.
  - `.topbar .brand`: `min-height: 48px` and `font-size: 1.125rem`.
  - `.who-name`: `min-width: 0`, a `max-width` around `9rem`, `overflow: hidden`, `white-space: nowrap`, `text-overflow: ellipsis`.
  - `.nav`: `display: grid`, `grid-template-columns: repeat(3, 1fr)`. `.nav a`: `min-height: 44px`, `justify-content: center`, `padding: 0`. The current page keeps its white 3px underline.
  - Target: `topbar` at most 100px at 390 and 360, against about 120px on main.
- [ ] **Step 4: Run the checks.** Run `shots.py S\shots\t3 --compare S\shots\base`. Expected:
  - no `sw`, `tabMin` or `logout` failures
  - the `topbar` compare passes
  - in `full` at 390, `nameCut` is true and Log out is fully visible
  - `fixture_login_390.png` shows the brand only, with no empty second row
- [ ] **Step 5: Run the behavior check.** Run `smoke.py S\check\t3` and diff it against `S\check\base`. Expected: every HTML page differs only by the two new spans in the top bar. Redirects, flashes, CSV, commands and database dumps are unchanged.
- [ ] **Step 6: Hand to Claude for review.** Hand over the diff, the shots output and the PNG paths, then wait for the go-ahead.
- [ ] **Step 7: Commit and push.** Commit message: `Fit the top bar into two rows on phones`. Then run `git push origin main`, stopping on rejection.

---

### Task 4: Tower rows on phones

**Files:**
- Modify: `app/static/style.css` (the `.tower-row`, `.pos` and `.gap small` rules near lines 472 to 600). The desk values in `@media (min-width: 64rem)` stay unchanged.

**Interfaces:**
- Consumes: `shots.py` (`carMin`, `plateCut`, `posCut`, `gapSmallLines`, `sw`).

- [ ] **Step 1: Confirm the failing checks.** Run `shots.py S\shots\t4 --compare S\shots\base` and note the `carMin` values, `plateCut` entries and `gapSmallLines` at 360 and 390.
- [ ] **Step 2: Change the base `.tower-row` rule** (it applies below 64rem).
  - Columns: `1.75rem 0.3125rem <plate> minmax(0, 1fr) max-content`.
  - `padding: 0 0.625rem`. `gap` stays at `0.375rem`.
  - `<plate>` is a fixed width, the same in every row so car names line up. Use the smallest 0.25rem step at which `SK-1234-AB` shows uncut at 360 (no `plateCut` for plates of 10 characters or fewer). Longer plates may still end in an ellipsis.
  - `.gap small` gets `white-space: nowrap`.
  - Row `min-height` stays 62px.
- [ ] **Step 3: Run the checks.** Run `shots.py S\shots\t4 --compare S\shots\base`. Expected:
  - no failures, with the `carMin` compare passing at 360 and 390
  - `gapSmallLines` is 1
  - `posCut` is 0 with positions 10 to 12 in `full`
  - the 1024 and 1440 tower looks the same as the base PNGs
- [ ] **Step 4: Run the behavior check.** Run `smoke.py S\check\t4` and diff it against the Task 3 snapshot `S\check\t3`. Expected: no differences.
- [ ] **Step 5: Hand to Claude for review.** Hand over the diff, the shots output, the new `carMin` values and the PNG paths, then wait for the go-ahead.
- [ ] **Step 6: Commit and push.** Commit message: `Give car names more room in the tower on phones`. Then run `git push origin main`, stopping on rejection.

---

### Task 5: Final check and progress note

**Files:**
- Modify: `CLAUDE.md` (the line in "Refactor plan" that says the redesign continues at step 6)

- [ ] **Step 1: Run the full check.** Run `shots.py S\shots\final --compare S\shots\base` and `smoke.py S\check\final`, then diff `S\check\final` against `S\check\base`. Expected:
  - no shots failures
  - the smoke diff shows only the two top bar spans
- [ ] **Step 2: Claude's own checks.** Claude looks at every final PNG at 360, 390, 1024 and 1440, and at the dashboard with reduced motion. Per CLAUDE.md, Claude also runs `& .venv\Scripts\flask.exe --app app --help` to confirm the app imports.
- [ ] **Step 3: Update CLAUDE.md.** Change "Step 5 looks done in commit cd989eb, so the redesign continues at step 6 (confirm)." to "Steps 1 to 6 are done (step 6 on 2026-11-27), so the redesign continues at step 7. Part of step 7 is already in 540b115 and 16d334f."
- [ ] **Step 4: Commit and push.** Commit message: `Note that redesign step 6 is done`. Then run `git push origin main`, stopping on rejection.
- [ ] **Step 5: Tell Kiril what is left to deploy.** On PythonAnywhere: pull and reload the web app. No database step is needed, because there is no schema change.
