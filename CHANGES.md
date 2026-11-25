# Changes

## 2026-11-25 (rev20261125_b)
- `check` now looks up the Instagram account ID when the IG_USER_ID secret is missing (Adam couldn't open Business Settings: signed in via Instagram there, and his Facebook login shows no business assets). It lists every Instagram account the token can see, with IDs, then stops with a red run so nothing is posted.
- Also asks for Instagram accounts assigned directly to the system user (first run found no Page and no portfolio access).

## 2026-11-25 (rev20261125_a)
- Daily reels moved from 07:41 to 08:00 Perth (Adam: cleaner time). Cron '0 0 * * *'.
- New midday run (12:00 Perth, cron '0 4 * * *') that posts the carousel for the previous day's block, from `carousels.csv` + `carousels/<folder>/`. Manual mode `carousel` added.
- Added an empty `carousels.csv` (header only).

## 2026-11-25 (rev20261125)
- Added `blocks.csv` with just the header row, so the daily 07:41 run says "Nothing left to post" instead of failing while the Mac/Chrome task is still doing the posting. The real block rows get added at the switch-over.
