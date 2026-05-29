# Listing text search

## Goal

A search box on the project listings page that filters the current
project's listings by free-text query across the most relevant text
fields. Composes with the existing status / price / size filters.

## Scope

In scope:

- Per-project search on the existing listings page (`ListingsView.tsx`).
- Matches across `title`, `location`, `description`.
- Multi-word AND semantics (every token must match somewhere).
- Case-insensitive, Unicode-safe (works for Slovenian diacritics).

Out of scope:

- Global search across multiple projects.
- Full-text search with stemming / ranking.
- Match highlighting in the table.
- Saved searches.
- Search suggestions / autocomplete.

## Backend

Add an optional `q: str | None = Query(None)` parameter to
`GET /api/projects/{project_id}/listings` in `app/api/listings.py`.

Logic, applied on top of the existing filters:

1. Strip `q`; if empty after stripping, ignore it.
2. Split on whitespace into tokens.
3. For each token, add a `WHERE` clause:
   ```
   lower(title) LIKE lower('%' || :token || '%')
   OR lower(location) LIKE lower('%' || :token || '%')
   OR lower(description) LIKE lower('%' || :token || '%')
   ```
4. All tokens must match (AND across tokens, OR across fields).

`lower(...) LIKE` is used instead of `ILIKE` because `ILIKE` only folds
ASCII case — Slovenian characters like `Č`/`č` would not match. `lower()`
on both sides is Unicode-safe.

No new index. At the current scale (max ~5k rows per project) sequential
scan with `lower() LIKE` is sub-50ms. If that ever becomes a problem,
the follow-up is a `pg_trgm` GIN index on a generated `text` column
concatenating the three fields.

The existing `count_query` keeps working because it wraps the filtered
query as a subquery.

## Frontend

`frontend/src/api/listings.ts`:

- Add `q?: string` to the `ListingFilters` type.
- When `q` is non-empty after trimming, include it in the request query
  string. Otherwise omit it entirely (so the URL stays clean for the
  default state).

`frontend/src/features/listings/ListingsView.tsx`:

- Add a search `<input>` on its own row above the existing filter row.
  Placeholder: `Search listings…`. Width: full container.
- Local state `searchInput: string` for the input value, debounced 300 ms
  before pushing into `filters.q` and resetting `page` to 1.
- Empty / whitespace-only input clears `filters.q` (does not set it to
  an empty string in the URL).
- No `localStorage` persistence — unlike `sort_by`, the search query is
  transient between visits.

The search composes with the existing `status` / price / size filters
and with sorting; pagination resets to page 1 on a new query.

## Edge cases

- Whitespace-only `q` → treated as no search.
- Multiple consecutive spaces → collapsed by the split.
- Very long `q` (>200 chars) → no special handling; Postgres handles it
  fine and the user obviously meant it.
- A token that contains SQL wildcards (`%`, `_`) → harmless because the
  query is parameterized; the wildcards become literal matches against
  whatever happens to contain them, which is the intuitive behavior.

## Testing

- Unit: the SQL builder produces the expected `WHERE` clause for 0 / 1 /
  3 tokens.
- Integration: seed three listings, one matching only title, one only
  description, one neither; assert `q=` returns the right two.
- Integration: Slovenian-diacritic case folding — seed a listing with
  `Tržaška` in the title, search `tržaška` (lowercase), assert match.
- Manual: type in the search box in the dev UI; debounce delays the
  refetch by ~300 ms; results compose with an active status filter.
