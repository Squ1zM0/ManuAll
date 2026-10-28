# ManuAll index format

## Brand files — `data/brands/<brand-slug>.json`

One file per brand. The filename slug is the slug a user would type
through the app's slug rule (lowercase, `&` → `and`, spaces →
hyphens, hyphens kept), e.g. `bradford-white.json`. Fields:

| Field | Meaning |
|---|---|
| `brand` | Display name from the ManualsLib brand page title (e.g. `Amana`). |
| `brandSlug` | The typed slug this file answers for. |
| `aliases` | Other ManualsLib slugs serving the same brand (e.g. `generac-power-systems` for `generac`). The app resolves all of these to this file. |
| `sourceBrandPages` | Brand-page paths tried during capture. |
| `slugUsed` | The slug whose brand page actually supplied the type list. |
| `capturedAt` | ISO-8601 UTC timestamp of the capture. |
| `typePages` | Per type page: `{path, manuals, status}` — `manuals` is the raw anchor count on that page (before dedupe), `status` the fetch HTTP status. |
| `manuals` | Array of manual entries (below), sorted by title, then manualId. |
| `convertedGuides` | `/guide/` featured links converted to `/manual/` form after verification (manualId, slug, title). |
| `gaps` | `{failedTypePages, failedGuideConversions}` — pages/links that could not be captured, with reason. Gaps are never papered over. |

Manual entry:

| Field | Meaning |
|---|---|
| `manualId` | Digits from the ManualsLib URL. Dedupe key within a brand. |
| `slug` | URL slug from the ManualsLib URL (e.g. `Amana-Asx-14-Seer`). |
| `title` | Display title: product model + manual label for listing rows, or the full title for featured/popular items. |
| `type` | One of `Service`, `Installation`, `Parts & Wiring`, `User / Owner`, `Other`, classified from the listing label/title with the same keyword buckets as the app ranking (Service first, then Installation, then Parts & Wiring, then User / Owner). |
| `pages` | Page count where the listing shows it, else `null`. Never guessed. |
| `productModel` | Product model from the listing row (`/products/` link text), else `null`. |
| `extraModels` | Model fragments from `#product-` URL fragments on that manual's links. |
| `url` | **Manual page URL only**: `https://www.manualslib.com/manual/<manualId>/<slug>.html`. Never a `/guide/` URL, never a data2 PDF URL, never a Worker/proxy URL. |

Rules enforced by the builder:

- `url` must match `^https://www\.manualslib\.com/manual/\d+/[^/?#]+\.html$`.
- `manualId` must be digits and must match the id in `url`.
- `type` must be one of the five labels above.
- Duplicate `manualId` values inside one brand file are dropped (first wins, warning printed).
- A brand file with zero manuals fails the build (it is a gap, not an index entry).

`/guide/` links: ManualsLib's brand pages list some newer manuals only
as featured `/guide/<id>/<slug>.html` links. Those are stored only
after fetching the `/manual/<id>/<slug>.html` form and confirming
HTTP 200 with a title sharing the guide slug's key tokens. The
stored `url` is always the `/manual/` form. Unverified conversions
land in `gaps.failedGuideConversions`.

## Built index — `dist/index.json` (do not hand-edit)

Built by `scripts/build_index.py` from `data/brands/*.json`:

```json
{
  "version": 1,
  "generatedAt": "<ISO-8601 UTC>",
  "brandCount": 10,
  "manualCount": 12345,
  "brands": {
    "<brandSlug>": {
      "name": "Amana",
      "aliases": [],
      "capturedAt": "<ISO-8601 UTC>",
      "manuals": [ { "manualId": "...", "slug": "...", "title": "...",
                     "type": "Service", "pages": 43, "productModel": "...",
                     "extraModels": ["..."], "url": "https://www.manualslib.com/manual/.../....html" } ]
    }
  }
}
```

`brands` keys are sorted by slug. Manuals keep their brand-file
order (title, then manualId). The builder prints brand/manual
counts and every warning; it exits nonzero on any validation
failure so a bad file can never ship a partial index silently.

## Price-Cal fetch pattern

Raw GitHub first, jsDelivr fallback, plain GET, no custom headers:

```
https://raw.githubusercontent.com/Squ1zM0/ManuAll/main/dist/index.json
https://cdn.jsdelivr.net/gh/Squ1zM0/ManuAll@main/dist/index.json
```

The app fetches once per page session and caches the index in
memory. Lookup semantics (same as the old live lookup): slugify the
typed brand, resolve slug or alias, require at least 3 model
characters, match exact model then series-prefix against slug
candidates, product model, extra-model fragments, and title;
show all matches within the series, ranked Service, Installation,
Parts & Wiring, User / Owner, Other, exact before prefix, then
title A–Z. Errors: `model_too_short`, `brand_not_found`
(includes "in the stored index" wording when the brand is not
captured yet), `model_not_found`, `index_fetch_failed`.

## Rebuilding

```sh
python3 scripts/build_index.py
```

Run from the repository root. It reads `data/brands/*.json` and
writes `dist/index.json`. Commit both the brand files and the
rebuilt `dist/index.json` together so the pushed index always
matches its sources.
