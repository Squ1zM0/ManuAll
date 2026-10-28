#!/usr/bin/env python3
"""Assemble dist/index.json from data/brands/*.json.

Validation (fails the build, never ships a partial index silently):
  - brand file has brand, brandSlug, manuals (non-empty list)
  - every manual has a digits manualId matching the id in its url
  - every url matches the manual PAGE form only:
      https://www.manualslib.com/manual/<digits>/<slug>.html
    (/guide/ URLs, data2 PDF URLs, and proxy URLs are rejected)
  - every type is one of the five app labels
  - pages is null or a positive int
  - duplicate manualIds inside one brand file are dropped (warning)

Usage (from the repository root):
  python3 scripts/build_index.py [--data data/brands] [--out dist/index.json]
"""
import argparse, glob, json, os, re, sys, datetime

URL_RE = re.compile(r"^https://www\.manualslib\.com/manual/(\d+)/([^/?#]+)\.html$")
TYPES = {"Service", "Installation", "Parts & Wiring", "User / Owner", "Other"}

def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/brands")
    ap.add_argument("--out", default="dist/index.json")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.data, "*.json")))
    if not files:
        fail(f"no brand files found in {args.data}")
    brands = {}
    total_manuals = 0
    warnings = 0
    for path in files:
        with open(path) as f:
            data = json.load(f)
        slug = data.get("brandSlug")
        name = data.get("brand")
        manuals = data.get("manuals")
        if not slug or not name:
            fail(f"{path}: missing brand/brandSlug")
        if not isinstance(manuals, list) or not manuals:
            fail(f"{path}: manuals is empty or missing (a gap, not an index entry)")
        if slug in brands:
            fail(f"duplicate brandSlug {slug} ({path})")
        seen = set()
        kept = []
        for m in manuals:
            mid = str(m.get("manualId", ""))
            url = m.get("url", "")
            if not re.fullmatch(r"\d+", mid):
                fail(f"{path}: manualId not digits: {mid!r}")
            mu = URL_RE.match(url or "")
            if not mu:
                fail(f"{path}: url is not a manual page URL: {url!r}")
            if mu.group(1) != mid:
                fail(f"{path}: manualId {mid} != id in url {url!r}")
            if m.get("type") not in TYPES:
                fail(f"{path}: unknown type {m.get('type')!r} for manual {mid}")
            pages = m.get("pages")
            if pages is not None and (not isinstance(pages, int) or pages <= 0):
                fail(f"{path}: bad pages {pages!r} for manual {mid}")
            if not m.get("title") or not m.get("slug"):
                fail(f"{path}: manual {mid} missing title/slug")
            if mid in seen:
                print(f"WARN: {path}: duplicate manualId {mid}, dropping")
                warnings += 1
                continue
            seen.add(mid)
            kept.append({
                "manualId": mid,
                "slug": m["slug"],
                "title": m["title"],
                "type": m["type"],
                "pages": pages,
                "productModel": m.get("productModel"),
                "extraModels": m.get("extraModels") or [],
                "url": url,
            })
        brands[slug] = {
            "name": name,
            "aliases": data.get("aliases") or [],
            "capturedAt": data.get("capturedAt"),
            "manuals": kept,
        }
        total_manuals += len(kept)
        print(f"{slug}: {len(kept)} manuals ({len(manuals)} rows, "
              f"{len(manuals) - len(kept)} dupes dropped)")

    # Alias collisions: an alias must not shadow a real brandSlug.
    for slug, b in brands.items():
        for alias in b["aliases"]:
            if alias in brands and alias != slug:
                fail(f"alias {alias} of {slug} collides with brandSlug {alias}")

    index = {
        "version": 1,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "brandCount": len(brands),
        "manualCount": total_manuals,
        "brands": {k: brands[k] for k in sorted(brands)},
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(index, f, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")
    print(f"wrote {args.out}: {len(brands)} brands, {total_manuals} manuals, "
          f"{warnings} warnings, {os.path.getsize(args.out)} bytes")

if __name__ == "__main__":
    main()
