# Clone-and-scale affiliate shortlist template

This repo builds a GitHub Pages product shortlist from **one file**: `site_config.json`.

## Edit only this file
Open `site_config.json` and update:
- `title`
- `description`
- `intro_paragraphs`
- `meta_note`
- `products` (list)

Then run the GitHub Action (or wait for the daily schedule).

## Setup
1) Repo Settings → Secrets and variables → Actions → add `AMZ_PARTNER_TAG` (example: `yourtag-20`)
2) Actions → Daily rebuild → Run workflow

## Images
The workflow caches images during the build (`CACHE_IMAGES=1`) to reduce broken images from hotlink blocking.
If you prefer not to cache third‑party images, change `CACHE_IMAGES` to `"0"` in `.github/workflows/daily.yml`.
