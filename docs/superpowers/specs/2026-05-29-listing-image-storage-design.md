# Listing image storage in Postgres

## Goal

Stop relying on `img.nepremicnine.net` URLs in the frontend. Save up to
three images per listing as bytes in our own database so:

- listings keep their images after they're removed from nepremicnine.net,
- the frontend serves images from our backend, not from a third party.

## Scope

In scope:

- Up to three images per listing (positions 0, 1, 2).
- New listings store image bytes lazily — the bytes are downloaded on the
  first frontend request for that image, not at scrape time.
- Existing listings get backfilled the same way: lazy, on first view.

Out of scope:

- Eager background backfill of historical listings.
- Multiple resolutions (thumbnail vs full). One stored size, used everywhere.
- Admin "refresh all images" endpoint.
- Image deduplication across listings.

## Schema

New table `listing_images`:

| column            | type        | notes                                                         |
|-------------------|-------------|---------------------------------------------------------------|
| `listing_id`      | uuid        | FK → `listings.id` ON DELETE CASCADE, part of PK              |
| `position`        | smallint    | 0, 1, or 2, part of PK                                        |
| `source_url`      | text NOT NULL | the original `img.nepremicnine.net` URL                     |
| `image_data`      | bytea NULL  | resized WebP bytes; NULL = "not fetched yet"                  |
| `mime_type`       | text NULL   | always `image/webp` once fetched                              |
| `fetched_at`      | timestamptz NULL | populated on successful fetch                            |
| `fetch_failed_at` | timestamptz NULL | tombstone — once set, the endpoint never retries this URL |

Primary key: `(listing_id, position)`.

`listing.images` (JSONB array of URLs) stays in place untouched. It is no
longer surfaced in API responses, but remains as the original source of
truth for what URL each `position` came from.

## Backend

### Image-serving endpoint

```
GET /api/projects/{project_id}/listings/{listing_id}/image/{position}
```

Lives in `app/api/listings.py` alongside the other listing routes, so it
inherits the `/api/projects` prefix. Unauthenticated — image URLs need to
load in `<img>` tags. The `project_id` segment is required for URL
consistency only; the handler does not verify project ownership. State
machine:

1. Look up the `listing_images` row by `(listing_id, position)`. If no row,
   return 404.
2. If `image_data` is non-NULL → respond `200 image/webp` with
   `Cache-Control: public, max-age=31536000, immutable`. No ETag — the
   `immutable` directive tells browsers not to revalidate, and the URL
   is stable per `(listing_id, position)`, so an ETag adds no value.
3. If `image_data` is NULL and `fetch_failed_at` is non-NULL → return 404
   (tombstone, never retried).
4. Otherwise (NULL bytes, no tombstone): lazy-fetch
   - `httpx.get(source_url, timeout=10)`. On non-200, set `fetch_failed_at`,
     commit, return 404.
   - On 200, decode with Pillow, resize to a max width of 800px (preserve
     aspect ratio, LANCZOS), encode as WebP quality 80.
   - Save `image_data`, `mime_type = image/webp`, `fetched_at = now()`.
   - Respond with the bytes (same headers as case 2).
5. Single-flight: an in-process `asyncio.Lock` per `(listing_id, position)`
   key prevents two concurrent requests from both fetching the same URL.
   (One process per container today — good enough.)

### Scrape-time integration

In `app/services/scraper_sync.py`, when a scraped listing is inserted or
updated, write up to three `listing_images` rows from
`scraped.images[0:3]` with `source_url` set, `image_data` NULL. Use upsert
keyed on `(listing_id, position)`:

- If a row already exists at that position with the same `source_url`,
  leave it alone (preserves any fetched bytes).
- If `source_url` changed, overwrite the whole row (bytes reset to NULL).

Listings with fewer than three images get fewer rows.

### Listing API response

`ListingRead.images` becomes a list of strings whose values are
`/api/projects/{project_id}/listings/{listing_id}/image/{position}` — one entry per row that
exists in `listing_images`, ordered by `position`. The list is built from
`listing_images` rows, not from the legacy `listing.images` JSONB.

`thumbnail_url` is already a computed property of `images[0]`, so it
follows automatically.

### Dependencies

Add to `backend/requirements.txt`:

- `Pillow` (for resize + WebP encode).
- `httpx` (explicit; currently transitive).

## Frontend

No structural changes. The four call sites (`api/listings.ts`,
`features/listings/ListingsView.tsx`, `features/listings/ListingDetailPage.tsx`,
`features/listings/ComparisonPage.tsx`) all consume `listing.images` as
`string[]` and continue to work. Image URLs simply point at our backend
now, which the Vite dev proxy already forwards via `/api`.

## Migration

Alembic revision adds the `listing_images` table and runs the data
backfill in the same upgrade:

```sql
CREATE TABLE listing_images (
    listing_id UUID NOT NULL REFERENCES listing(id) ON DELETE CASCADE,
    position SMALLINT NOT NULL,
    source_url TEXT NOT NULL,
    image_data BYTEA,
    mime_type TEXT,
    fetched_at TIMESTAMPTZ,
    fetch_failed_at TIMESTAMPTZ,
    PRIMARY KEY (listing_id, position)
);

INSERT INTO listing_images (listing_id, position, source_url)
SELECT l.id, idx - 1, l.images->>(idx - 1)
FROM listing l
JOIN LATERAL generate_series(1, LEAST(jsonb_array_length(l.images), 3)) AS idx ON TRUE
WHERE jsonb_array_length(l.images) > 0;
```

Downgrade drops the table.

## Testing

- Unit: Pillow resize step — given a known input image, the output is
  WebP and width ≤ 800.
- Unit: endpoint state machine — 404 (no row), 200 (cached bytes), 200
  (lazy-fetched on first call with `httpx` mocked), 404 (tombstoned).
- Manual: load a known existing listing in the dev UI. Network panel
  shows requests to `/api/listings/.../image/0`. Image renders. After
  page reload, the same request returns from `image_data` without a
  source fetch (verify via a temporary log line or by querying the row).
