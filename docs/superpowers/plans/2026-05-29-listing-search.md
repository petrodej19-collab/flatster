# Listing Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-project free-text search box on the listings page that filters by title, location, and description.

**Architecture:** Backend gains a `q` query param on the existing list endpoint; tokenized on whitespace, AND across tokens, OR across the three fields, using `lower(field) LIKE lower(%token%)` for Unicode-safe case folding. Frontend adds a debounced search input that pushes into the existing `ListingFilters` state.

**Tech Stack:** FastAPI / SQLAlchemy (async) / Postgres on the backend, React + TanStack Query on the frontend.

**Spec:** `docs/superpowers/specs/2026-05-29-listing-search-design.md`

---

## File Structure

- Modify: `backend/app/api/listings.py` — add `q` query param and the SQL filter helper to `list_listings`.
- Modify: `backend/tests/test_listings_search.py` — new test file for the tokenization helper.
- Modify: `frontend/src/api/listings.ts` — extend `ListingFilters` with `q?: string` and serialize.
- Modify: `frontend/src/features/listings/ListingsView.tsx` — search input + 300 ms debounce.

---

## Task 1: Backend tokenizer

**Files:**
- Modify: `backend/app/api/listings.py` (add helper near the top)
- Create: `backend/tests/test_listings_search.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_listings_search.py`:

```python
from app.api.listings import _search_tokens


def test_empty_string_returns_empty_list():
    assert _search_tokens("") == []


def test_whitespace_only_returns_empty_list():
    assert _search_tokens("   \t\n  ") == []


def test_single_token_lowercased():
    assert _search_tokens("Tržaška") == ["tržaška"]


def test_multiple_tokens_split_on_whitespace():
    assert _search_tokens("novogradnja balkon") == ["novogradnja", "balkon"]


def test_consecutive_spaces_collapsed():
    assert _search_tokens("novogradnja   balkon") == ["novogradnja", "balkon"]
```

- [ ] **Step 2: Run test to verify it fails**

Run from the `backend/` directory:

```bash
docker compose exec app pytest tests/test_listings_search.py -v
```

Expected: ImportError on `_search_tokens`.

- [ ] **Step 3: Implement the tokenizer**

Add near the top of `backend/app/api/listings.py` (after imports, before any route):

```python
def _search_tokens(q: str | None) -> list[str]:
    """Split a search query on whitespace and lowercase the tokens.

    Lowercasing here means the SQL only needs to lowercase the column side.
    """
    if not q:
        return []
    return [t.lower() for t in q.split() if t]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
docker compose exec app pytest tests/test_listings_search.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/listings.py backend/tests/test_listings_search.py
git commit -m "Add search-query tokenizer for listings endpoint"
```

---

## Task 2: Wire `q` into the listings endpoint

**Files:**
- Modify: `backend/app/api/listings.py` — `list_listings` route.

- [ ] **Step 1: Add `q` to the list route**

Find the existing route in `backend/app/api/listings.py`:

```python
@router.get("/{project_id}/listings", response_model=PaginatedListings)
async def list_listings(
    project_id: UUID,
    status_filter: str | None = Query(None, alias="status"),
    ...
```

Add a `q` parameter alongside the other filters:

```python
@router.get("/{project_id}/listings", response_model=PaginatedListings)
async def list_listings(
    project_id: UUID,
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = Query(None),
    min_price: Decimal | None = Query(None, alias="min_price"),
    # ... (other existing params)
```

(Match the exact existing signature order; insert `q` next to the other text-style filters.)

- [ ] **Step 2: Apply the search filter to the query**

In the same function, after the existing `query = select(Listing).where(Listing.project_id == project_id)` and the other `if status_filter`/`if min_price` etc. blocks, add:

```python
    from sqlalchemy import func, or_

    for token in _search_tokens(q):
        like_pattern = f"%{token}%"
        query = query.where(
            or_(
                func.lower(Listing.title).like(like_pattern),
                func.lower(Listing.location).like(like_pattern),
                func.lower(Listing.description).like(like_pattern),
            )
        )
```

`func.lower(...)` on the column side is Unicode-safe; the token is already lowercased by `_search_tokens`. Move the `from sqlalchemy import ...` to the existing import block at the top of the file if `func` / `or_` aren't already imported.

- [ ] **Step 3: Verify the count query already wraps as a subquery**

Locate this existing line in the same function (should be a few lines below the filter block):

```python
count_query = select(func.count()).select_from(query.subquery())
```

If it already uses `query.subquery()`, the search filter is automatically included in the count — no change needed. If the count query is built differently, change it to wrap `query.subquery()` so the filter applies.

- [ ] **Step 4: Restart the backend and smoke-test**

```bash
docker compose restart app
curl -s -H "Cookie: <your-auth-cookie>" \
  "http://localhost:8000/api/projects/<a-project-id>/listings?q=balkon&per_page=5" \
  | python3 -m json.tool | head -40
```

Expected: only listings whose title/location/description contain "balkon" (case-insensitive). Confirm `total` matches the filtered count.

(If you don't have a cookie handy, log in via the frontend dev tools first and copy it; or hit the same URL through the running frontend at `http://localhost:5173`.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/listings.py
git commit -m "Filter listings by free-text query across title/location/description"
```

---

## Task 3: Frontend filter type and API plumbing

**Files:**
- Modify: `frontend/src/api/listings.ts`

- [ ] **Step 1: Inspect the current shape**

Open `frontend/src/api/listings.ts` and find the `ListingFilters` type. Note the existing fields (status, min_price, etc.) and how the URL is built (likely a function that constructs URLSearchParams).

- [ ] **Step 2: Add `q` to the type**

```typescript
export type ListingFilters = {
  // ... existing fields ...
  q?: string
  // ... existing fields ...
}
```

(Insert in a sensible position — near `status` makes sense since they're both text filters.)

- [ ] **Step 3: Serialize `q` into the URL**

In the same file, find where filters get turned into query params. Add a guarded append:

```typescript
if (filters.q && filters.q.trim()) {
  params.set("q", filters.q.trim())
}
```

Untrimmed/empty `q` should NOT be set so the URL stays clean.

- [ ] **Step 4: Verify the TanStack Query key includes `q`**

If `useListings` uses `[..., filters]` as the query key, no change needed — it'll automatically refetch on `q` change. If the key destructures specific fields, add `filters.q`.

- [ ] **Step 5: Type-check the frontend**

```bash
cd frontend && npm run typecheck
```

Expected: no errors. (If the project uses `tsc --noEmit` differently, match its `package.json` script.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/listings.ts
git commit -m "Add q to ListingFilters and serialize into listings request"
```

---

## Task 4: Search input UI with debounce

**Files:**
- Modify: `frontend/src/features/listings/ListingsView.tsx`

- [ ] **Step 1: Add local search-input state**

Near the top of the component, alongside the other `useState` calls:

```typescript
const [searchInput, setSearchInput] = useState<string>("")
```

- [ ] **Step 2: Debounce the input into `filters.q`**

Add a debounced effect that updates `filters.q` 300 ms after the last keystroke:

```typescript
useEffect(() => {
  const trimmed = searchInput.trim()
  const t = setTimeout(() => {
    setFilters((prev) => {
      const nextQ = trimmed || undefined
      if (prev.q === nextQ) return prev
      return { ...prev, q: nextQ, page: 1 }
    })
  }, 300)
  return () => clearTimeout(t)
}, [searchInput])
```

- [ ] **Step 3: Render the search input**

Above the existing filter row (status dropdown, price/size inputs), add a new row:

```tsx
<div className="mb-3">
  <input
    type="text"
    value={searchInput}
    onChange={(e) => setSearchInput(e.target.value)}
    placeholder="Search listings…"
    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
  />
</div>
```

(Match the existing Tailwind classes used by the other inputs in this file so the styling lines up.)

- [ ] **Step 4: Manual UI check**

```bash
docker compose up -d
# wait a few seconds
```

Open http://localhost:5173, navigate to a project's listings, type a query like "Tržaška". After ~300 ms the table refetches and shows matching rows. Confirm:

- Typing fast doesn't trigger one request per keystroke (DevTools Network tab).
- Clearing the box restores all listings.
- Switching between projects clears `searchInput` (component remount).
- The existing status / price / size filters still compose correctly.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/listings/ListingsView.tsx
git commit -m "Add debounced search input to listings page"
```

---

## Task 5: Manual end-to-end verification

- [ ] **Step 1: Slovenian-diacritic case folding**

In the running UI, find a listing whose title contains `Tržaška`. Type `tržaška` (all lowercase) in the search box. Confirm the result appears.

- [ ] **Step 2: Multi-word AND**

Type two tokens that you know appear in the same listing's description (e.g., `balkon parking`). Confirm only listings containing both tokens (across any of the three fields) show up.

- [ ] **Step 3: Composes with status filter**

Set the status filter to `active`, then add a search query. Confirm only active listings matching the query appear.

- [ ] **Step 4: Pagination reset**

Page through to page 2 of a large project, then type a query. Confirm the view jumps back to page 1.

No commit needed — verification only.
