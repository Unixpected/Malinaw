# Infrastructure Watch PH

A read-only monitor of DPWH infrastructure projects. No sample or invented data: everything on
the site comes from the real project records, and anything the data cannot show is listed on the
"Data gaps and sources" tab.

## Data
`base-data/base-data-json.tar.xz` from github.com/csiiiv/dpwh-transparency-data-api-scraper,
which holds the DPWH Transparency Portal project list (about 247,000 projects) as JSON pages.
The archive does not say when it was collected, so it can be out of date. The live source is
transparency.dpwh.gov.ph (API: api.transparency.dpwh.gov.ph/projects). That API sits behind
bot protection, which is why the scraper repo rotates browser fingerprints; refresh the archive
with that scraper if you need newer data.

## Run it
    pip install -r requirements.txt
    python pipeline/fetch.py      # downloads the archive (about 12 MB)
    python pipeline/build.py      # writes site/data.json
    cd docs && python -m http.server 8000

## Rules
`rules.json` holds each rule's formula, weight and "how to check" text. Fields: `budget_m`,
`progress`, `status`, `report_count`, `dup_desc_count`, `contractor_share`, `office_year_n`,
`office_year_total_m`, `has_coords`. Thresholds and weights are judgement calls, shown on the
site's "How it works" tab. `config.json` sets the ranking cut-offs.

## What the data cannot show
Amount paid is zero for every project, completion dates are missing for many, and there are no
bidder counts or company records. So payment-vs-progress, overdue and single-bidder checks are
not possible. PhilGEPS awards, COA audit reports, FDPP budgets and BLGF data are not loaded
because no verified data file was available.

## Put it online (GitHub Pages)
1. Upload everything in this folder to a new public GitHub repository.
2. Go to Settings > Pages. Under "Build and deployment", set Source to "Deploy from a branch",
   Branch to `main`, and Folder to `/docs`. Save.
3. After a minute the site is live at https://YOUR-HANDLE.github.io/REPO-NAME/.
The site already includes its data (`docs/data.json`). The optional workflow in `.github`
re-downloads the archive and refreshes that file every Sunday.

## Publishing guidance
A flag is a prompt to look closer, not evidence of wrongdoing. Cite the contract ID next to every
claim, use neutral wording, and do not publish contractor names without checking the source.
