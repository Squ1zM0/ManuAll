# ManuAll

ManuAll holds the stored manual-URL index that Price-Cal's Manuals page
reads at query time. It does **not** store PDFs and does **not** store
manual content — it stores verified URLs that lead to manuals on
ManualsLib, organized by brand, so the app never has to fetch
ManualsLib live at use time.

## Architecture change — Oct 27, 2026 (supersedes the live-lookup path)

Before this date, ManuAll held only the live lookup specification (see
NAVIGATION.md): Price-Cal navigated manualslib.com at query time,
through a Cloudflare Workers proxy. That path was retired by Fred on
Oct 27, 2026, because ManualsLib intermittently refuses the Workers'
shared egress IPs, which made lookups unreliable on phones.

The previous README statement — "No PDFs, manuals, or indexes are
stored in this repository" — is superseded by this change. What is
stored now is a **URL index only**: brand → model/series → verified
manual URLs (with title, type, and page count where the listing shows
it). No PDF files, no manual page content, and no search API are
stored here.

Current runtime path (Price-Cal):

1. The Manuals page fetches the index in four quarters from this
   repository — `dist/index-1.json` through `dist/index-4.json` —
   raw GitHub first, jsDelivr fallback per file, no proxy, no
   custom headers. The app merges the four parts and serves the
   combined index. If any quarter fails to load, the lookup fails
   honestly instead of silently serving a partial index, and the
   old single-file index is never used as a silent fallback.
2. It matches the typed brand and model against the stored index
   (same slug rule, same exact/series-prefix matching, same
   show-all-within-the-series and ranking as the old live lookup).
3. Tapping a result opens the stored URL on ManualsLib directly,
   from the phone's own connection.

Capture (how the index is built, not how it is used): Cobalt-side
code calls only — brand page, then every type page, then manual-page
verification where a link needs it. NAVIGATION.md remains the
reference for the brand-slug rule, the brand/type/manual page
patterns, and the matching and ranking rules. Capture retries in
flagged windows and logs gaps; it never invents a URL.

## Stored URL form — confirmed Oct 27, 2026

Fred clarified on Oct 27, 2026 (23:17 MDT) that ManuAll stores "the
URL that leads directly to the PDF that [is] stored on ManualsLib",
and no PDFs — then confirmed the form at 23:18 MDT: the manual
**page** URL (`https://www.manualslib.com/manual/<id>/<slug>.html`,
which opens the ManualsLib viewer with Download one click away).
Direct data2.manualslib.com PDF URLs are explicitly **not** stored
(they are JS-resolved and behind a Download flow, not capturable by
code calls alone). The builder enforces the page-URL form; see
`docs/INDEX_FORMAT.md`.

## Layout

```
data/brands/<brand-slug>.json   one file per brand (see docs/INDEX_FORMAT.md)
scripts/build_index.py          assembles the combined index from data/brands/
dist/index-1.json .. index-4.json
                                built index quarters Price-Cal fetches (do not
                                hand-edit); brand-intact, size-balanced parts
                                of the combined index (see "Quarters" below)
dist/index.json                 Phase 1 legacy single-file index (10 brands);
                                left in place, NOT read by the current app
docs/INDEX_FORMAT.md            schema, builder usage, and fetch pattern
NAVIGATION.md                   historical live-lookup spec (reference only)
```

## Quarters — Oct 28, 2026

The combined index (327 brands, 212,329 manuals) is 58.7 MB, which
GitHub's API refuses as a single file. It is therefore published in
four quarters, split by brand — no brand's manual list is split
across parts — balanced by serialized size so each part is about
14.7 MB:

| Part | Brands | Manuals |
|---|---|---|
| dist/index-1.json | 80 | 52,153 |
| dist/index-2.json | 82 | 51,617 |
| dist/index-3.json | 82 | 54,665 |
| dist/index-4.json | 83 | 53,894 |

The 327 brands are 10 Phase 1 trade brands (33,588 manuals) plus
317 HVAC-category brands captured from TechDirect's HVAC list
(178,741 manuals). A brand slug appearing in two quarters is a
build error, never silently overwritten. The quarters are the
index; `dist/index.json` remains only as the Phase 1 legacy file.

## Fetch pattern for Price-Cal

Raw GitHub first, per quarter (N = 1..4):

```
https://raw.githubusercontent.com/Squ1zM0/ManuAll/main/dist/index-N.json
```

jsDelivr fallback, per quarter:

```
https://cdn.jsdelivr.net/gh/Squ1zM0/ManuAll@main/dist/index-N.json
```

All are plain GETs with no custom headers. The app fetches all
four quarters once per page session, merges them, and caches the
merged index in memory. If any quarter fails on both hosts, the
lookup fails instead of serving a partial index.
