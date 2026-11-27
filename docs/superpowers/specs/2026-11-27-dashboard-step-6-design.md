# Redesign step 6: month totals strip and phone layout

Short design, agreed 2026-11-27.

## Why

Step 6 of the Race Control redesign finishes the dashboard before the other pages adopt the new look. On a phone in the workshop the dashboard is used to check which cars are late and move them on. The month money matters at the desk, not in the workshop.

## What exists already

- The month strip is in `dashboard.html` with its data from `dashboard()`: picked up count, parts, labor, total. It is a plain 2 by 2 grid.
- Below 64rem the dashboard is one column: tower, car panel, strip.
- The top bar wraps to about two rows on a phone, about 120px before the first car.
- At 390px the make and model in a tower row get about 100px and are cut off.

## Goals

1. **Month strip, 2 by 2 at every width.** Figures in the Figure style from DESIGN.md (italic 900, about 26px on desk, smaller on a phone if needed), labels muted at about 13px, hairline lines between cells as now. Amounts keep the normal money format ("38400.00 MKD"). A number is never broken in the middle; the currency may drop to the next line under it. A big month (123456.00 MKD) must fit at 390px and desk width.
2. **Phone top bar.** Two tidy rows: brand on the left with the user name and Log out on the right, then Dashboard, Jobs and New job as three equal tabs underneath, each at least 44px tall. Shorter than today, so more of the tower shows on the first screen. The current page keeps its white underline. This is base.html, so it changes every page at phone width.
3. **Tower rows at 390px.** The make and model get more room, a normal plate ("SK 1234 AB") is never cut off, and the gap column with "d in status" does not wrap awkwardly. Rows stay whole at 62px and nothing scrolls sideways.

## Non-goals

- Move keeps returning to the car panel (`#car`), as now.
- The tower keeps its order, longest in the shop first. No late-first sorting.
- No Move button inside tower rows.
- No new number format for the dashboard.
- No changes to Python, routes or data. The other pages wait for step 7.

## Approaches

- **Building it:** CSS in `style.css`, plus a small template edit only if a rule needs a class to hook onto (picked). A separate phone template was ruled out because two copies drift apart. A folding menu button was ruled out because it needs JavaScript and adds a tap before every page change.
- **Month strip:** keep 2 by 2 (picked), one row like the sketch with a dashboard-only number format, or one row across the full width under both columns. Picked 2 by 2 because amounts stay the same on every page and the layout is the same on phone and desk.
- **After Move on a phone:** stay on the car panel (picked), back to the top of the tower, or a Move button in every row. Kiril picked staying on the car.

## Claude's calls (check these)

- The two-column breakpoint stays at 64rem, because the 520px tower and the car panel need about that much side by side. DESIGN.md says "roughly 60rem"; that line is corrected when DESIGN.md is rewritten in step 8.
- The user name stays in the phone top bar if it fits beside Log out.
- Exact sizes and column widths are left to the builder, measured in the browser against the goals above.

## Verification

- Dashboard at about 390px and at desk width with: no open cars, one car, nine or more cars, a late car, a car with no fault codes, a long make and model, a month with nothing picked up, and a big month total.
- The top bar at 390px on every page, and the login page (no user part).
- Nothing scrolls sideways on a phone. Reduced motion still removes the sector animation.
- The check script shows every page, POST and command behaving as before.
