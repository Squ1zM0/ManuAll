# ManuAll — live manual lookup spec

ManuAll holds the **lookup spec only**. No PDFs are stored here, no manual
index is stored here, and no brand list is stored here. At query time the
app (Price-Cal, `/manuals`) navigates manualslib.com directly using the
rules below, and the technician types the brand and model as free text.

## URL patterns (verified by automated fetch, 2026-10-26)

| Page | Pattern | Notes |
|---|---|---|
| Brand page | `/brand/<slug>/` | e.g. `/brand/carrier/`, `/brand/amana/` |
| Product-type page | `/brand/<slug>/<type>.html` | **The `.html` matters** — the trailing-slash form 404s. E.g. `/brand/amana/air-conditioner.html` |
| Manual page | `/manual/<id>/<Brand>-<model>.html` | e.g. `/manual/734125/Carrier-58mvb.html` |
| Letter page | `/brand/<letter>.html` | A–Z, digits 0–9, plus `/brand/lit.html` for the `#` bucket. Paginated via `?page=` (A = 13 pages, Z = 2) |

## Brand slug rule

Lowercase, `&` becomes `and`, spaces become hyphens, other punctuation is
dropped, hyphen runs collapse, leading/trailing hyphens trim. Verified
against 1,000 real brand pages:

- `Carrier` → `carrier`
- `General Electric` → `general-electric` (serves GE's page)
- `A & A Scales` → `a-and-a-scales`
- `A to Z Rubber Stamps` → `a-to-z-rubber-stamps`

## Lookup flow

1. Slugify the typed brand, fetch its brand page.
2. Match the model against that page's manual list (see Matching below).
   Most queries end here — the brand page lists hundreds of manuals
   (Carrier: 518, GE: 2,125).
3. On a miss, fan out to the brand's product-type pages in parallel
   (capped at 50) and match there. Brand pages list only a *partial*
   manual list; type pages hold the full per-brand list (Amana air
   conditioners: 180 manuals, 170 not on the brand page).
4. If the brand page 404s, fall back to the letter page: fetch
   `/brand/<first-letter>.html` (paginating `?page=` as needed, capped)
   and find the `<a href="/brand/<slug>/">` whose text matches the typed
   brand case-insensitively, then retry with that slug.
5. If still not found, report brand-not-found / model-not-found cleanly.
   Brand pages are NOT `?page=`-paginated (page 2 returns the same list);
   type pages are not paginated either.

## What a list page yields

Each manual row pairs a product link (`/products/<Brand>-<model>-<id>.html`)
with a manual link. The manual anchor text is the manual **type**
(`Installation Instructions Manual`, `Use & Care Manual`, `Service Manual`,
`Owner's Manual`, …). The title attribute (or a leading `N pages` in the
anchor text on popular-manual cards) gives the **page count**.

List pages also carry `#product-<model>` fragment links: a manual's
"also applies to" bullets name the other models it covers (e.g. the
AVXC20 Series service manual covers AVXC200241, AVXC200361, AVXC200481).
These are match signals, not separate manuals — dedupe by manual ID.

## Matching

Normalize by uppercasing and stripping non-alphanumerics. Minimum input
length 3 characters.

- **Exact:** the normalized input equals a candidate — the manual slug
  with its brand prefix stripped (`Amana-Avxc20-Series` → `AVXC20SERIES`,
  `Carrier-58mvb` → `58MVB`), the row's product model, a series base
  (slug with a trailing `SERIES` removed), or a covered fragment model.
- **Series-prefix:** the normalized input starts with a candidate or its
  series base (full model `58MVB060F10114` matches the `58MVB` series
  manual; `AVXC201234` matches `AVXC20-Series`).
- Exact ranks above prefix.

## Ranking

Service/maintenance first, then installation/start-up, then parts/wiring,
then user/owner guides, then other. Type is classified from the anchor
text by keyword. All manuals for the matched model/series are returned,
ranked — never a single best match.

## v1 scope (and what comes later)

v1 returns the **manual page URL**. The technician opens it on ManualsLib
and downloads from there in one tap. The direct PDF link
(`data2.manualslib.com/cpdf/…pdf`) appears in NO fetched HTML (letter,
brand, type, manual, or download pages) and is not derivable from the
manual ID (opaque hash) — it is resolved by ManualsLib's JavaScript at
runtime. Direct-PDF resolution is a later upgrade, not part of v1.

## Politeness

Browser User-Agent, 15-second per-request timeout, no-store fetches,
bounded fan-out, no retries around a block. If ManualsLib blocks or
rate-limits, stop and report — never work around it.
