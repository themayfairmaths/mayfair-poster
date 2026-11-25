# Mayfair Math auto-poster

Posts one block of reels to @themayfairmaths every day at 08:00 Perth, plus a carousel at midday the day after, from GitHub's servers. No laptop needed.

## One-off setup
1. **GitHub account + repo.** Sign up at github.com (free). Click **New repository** and name it `mayfair-poster`.
   - **Public** = custom covers work (Instagram has to fetch the cover from a public link). Upcoming videos are visible to anyone who finds the repo. The token is still safe, because secrets are never public.
   - **Private** = everything is hidden, but reels go out without custom covers.
2. **Upload these files** with **Add file → Upload files**: `post.py`, `README.md`, `posted.csv`, `blocks.csv`, and the `.github/workflows/post.yml` file (or use GitHub Desktop, which keeps the folders).
3. **Add the secrets:** **Settings → Secrets and variables → Actions → New repository secret**
   - `IG_TOKEN` = the system-user token.
   - `IG_USER_ID` = the Instagram account ID (business.facebook.com → Settings → Instagram profiles → click @themayfairmaths → the ID shown).
4. **Covers (public repo only):** on the same page, **Variables** tab → **New variable** `COVER_BASE_URL` = `https://raw.githubusercontent.com/<your-username>/mayfair-poster/main/covers/`
5. **Test:** **Actions → Post to Instagram → Run workflow → mode: check.** Green tick = token and account work. Nothing is posted.
6. **First real post:** Run workflow → mode: test → paste one queue file name.

## Adding videos
Put the `NNN Title.mp4` and `NNN Title.txt` files in `queue/` and the covers in `covers/`, and keep `blocks.csv` up to date. Upload a few weeks at a time. Each file is under 6 MB.

## How it works
Each day it takes the first block in `blocks.csv` that still has unposted parts and posts them in `post_order` (last part first, so the grid reads 1 to N). Results go into `posted.csv`. If a post fails, the run goes red and GitHub emails you. The next run carries on from where it stopped. Missed days slip the plan; nothing is skipped.

## Carousels (midday)
At 12:00 Perth the workflow posts the carousel for the previous day's block, if one is ready.
- `carousels.csv`: one row per carousel: `after_block,folder,carousel_name` (block number from blocks.csv).
- `carousels/<folder>/`: `slide01.jpg` ... `slide10.jpg` (JPEG only, 2-10 slides, 1080x1350) and `caption.txt`.
- It waits until every reel in that block was posted on an earlier day, so it always lands at midday the day after. One carousel per run; if a day is missed it carries on next time.
- Needs the public repo and `COVER_BASE_URL` (the carousel link is worked out from it).
- Manual: Run workflow -> mode **carousel** (optionally type a folder name to post that one now).

Note: GitHub can start scheduled runs a few minutes late at busy times (on the hour is busiest).
