# Changes

## 2026-11-26 (rev20261126)
- Reels are now spread across the day: the workflow runs hourly from 08:00 to 15:00 Perth and each run posts ONE reel (`post_next_reel`), so a 5-part block goes out 08:00, 09:00, 10:00, 11:00, 12:00. Spreading the parts stops them competing with each other for the same followers.
- A new block only starts if no block has started that day, so it's still one block per day. If a part is left over (a dropped GitHub run), it goes first the next morning and that day's block follows an hour later.
- Never two reels less than 45 minutes apart (`MIN_GAP_MINUTES`), in case a late GitHub run lands next to the following one. The runs at 13:00-15:00 are spares for this.
- Carousel moved from 12:00 to 12:30 so it doesn't land on top of a reel.
- The old "post the whole block at once" behaviour is gone; manual `post` runs also post one reel.

## 2026-11-26 (rev20261126)
- `post` now skips if any reel was already posted today (Perth time). GitHub's 08:00 scheduled run was late on its first day, so the block was started by hand; this stops a late scheduled run from posting a second block the same day.

## 2026-11-25 (rev20261125_c)
- carousels.csv can now have a `post_date` column (YYYY-MM-DD). A dated carousel posts at the 12:00 run on or after that date, without waiting for its block to be posted from GitHub. Lets carousels go out from GitHub while the reels are still posted from the Mac.

## 2026-11-25 (rev20261125_b)
- `check` now looks up the Instagram account ID when the IG_USER_ID secret is missing (Adam couldn't open Business Settings: signed in via Instagram there, and his Facebook login shows no business assets). It lists every Instagram account the token can see, with IDs, then stops with a red run so nothing is posted.
- Also asks for Instagram accounts assigned directly to the system user (first run found no Page and no portfolio access).

## 2026-11-25 (rev20261125_a)
- Daily reels moved from 07:41 to 08:00 Perth (Adam: cleaner time). Cron '0 0 * * *'.
- New midday run (12:00 Perth, cron '0 4 * * *') that posts the carousel for the previous day's block, from `carousels.csv` + `carousels/<folder>/`. Manual mode `carousel` added.
- Added an empty `carousels.csv` (header only).

## 2026-11-25 (rev20261125)
- Added `blocks.csv` with just the header row, so the daily 07:41 run says "Nothing left to post" instead of failing while the Mac/Chrome task is still doing the posting. The real block rows get added at the switch-over.
