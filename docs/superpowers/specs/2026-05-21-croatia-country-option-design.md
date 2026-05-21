# Croatia as a country option in project creation

**Date:** 2026-05-21
**Status:** Approved

## Summary

Add Croatia (`hr`) as a selectable country when creating a project, alongside the existing Slovenia (`si`) flow. nepremicnine.net (the only data source) supports Croatian listings under the same URL shape — a region slug drops into position 2 of the path, e.g. `https://www.nepremicnine.net/oglasi-prodaja/primorsko-goranska/stanovanje/`. No new scraper, no new parser, no new URL prefix.

The change introduces a `country` dimension to `ProjectFilters`, branches the region/sub-region taxonomy by country, and surfaces a country dropdown in the create-project dialog.

## Scope

In scope:

- `country: "si" | "hr"` field on `ProjectFilters` (Pydantic + TS).
- Country-keyed `REGIONS` constant in both backend and frontend.
- 21 Croatian counties (no sub-regions in v1).
- Validators that reject mismatched region/country and forbid sub-region for Croatia.
- Country dropdown in `ProjectCreateDialog`, plus the conditional sub-region row.
- Slug verification step during implementation (HEAD-check the 21 Croatian URLs against the live site).

Out of scope:

- Sub-regions for Croatia (the site has none at the level we use).
- Country-specific property types, room types, or transaction types (confirmed identical with user).
- Migrating existing projects (none needed — see "Migration" below).
- A new scraper, parser, or detail parser.

## Approach

Per-country region map, single `country` field on filters. Alternatives (a flat merged region list with no country concept, or a per-country scraper module) were rejected — the former clutters UX and erases room for country-specific behaviour later, the latter is over-engineering for what is effectively a region-list swap on the same site.

## Data model

`ProjectFilters` gets one new field:

```python
country: Literal["si", "hr"] = "si"
```

Default `"si"` so existing rows (whose `filters` JSONB has no `country` key) continue to validate on read. The field is declared **before** `region` so subsequent validators can read it via `info.data["country"]`.

The `Project.filters` column is already `JSONB`. The `Project.scrape_url` column already holds a full URL built at creation time. Neither needs a schema migration.

## Constants restructure

### Backend — `backend/app/scraper/constants.py`

- `REGIONS: dict[str, dict[str, str]]` keyed by country code. `REGIONS["si"]` is the existing 13-entry dict verbatim; `REGIONS["hr"]` is the new 21-entry dict (see "Croatian region slugs" below).
- `SUBREGIONS: dict[str, dict[str, dict[str, str]]]` keyed by country code. `SUBREGIONS["si"]` is the existing dict verbatim; `SUBREGIONS["hr"] = {}` (empty, not absent — so `SUBREGIONS[country]` never `KeyError`s).
- New `COUNTRIES: dict[str, str] = {"si": "Slovenija", "hr": "Hrvaška"}` for label display.
- `PROPERTY_TYPES`, `ROOM_TYPES`, `TRANSACTION_TYPES` — unchanged. Reused for both countries.

### Frontend — `frontend/src/lib/constants.ts`

Mirror the backend changes: `REGIONS` becomes country-keyed; `SUBREGIONS` becomes country-keyed; add `COUNTRIES`. Same content as backend.

### Croatian region slugs

Derived from the dropdown labels using the transliteration rule the site already applies for Slovenian (š→s, ž→z, ć→c, đ→d, lowercase, spaces→hyphens). One slug, `primorsko-goranska`, is confirmed against a live URL provided by the user.

| Slug | Label |
|---|---|
| `primorsko-goranska` | Primorsko-goranska |
| `istrska` | Istrska |
| `mesto-zagreb` | Mesto Zagreb |
| `zagrebska` | Zagrebška |
| `dubrovnisko-neretvanska` | Dubrovniško-neretvanska |
| `splitsko-dalmatinska` | Splitsko-dalmatinska |
| `sibenisko-kninska` | Šibeniško-kninska |
| `zadarska` | Zadarska |
| `osijesko-baranjska` | Osiješko-baranjska |
| `vukovarsko-sremska` | Vukovarsko-sremska |
| `virovitisko-podravska` | Virovitiško-podravska |
| `pozesko-slavonska` | Požeško-slavonska |
| `brodsko-posavska` | Brodsko-posavska |
| `medimurska` | Međimurska |
| `varazdinska` | Varaždinska |
| `bjelovarsko-bilogorska` | Bjelovarsko-bilogorska |
| `sisasko-moslavinska` | Sisaško-moslavinska |
| `karlovska` | Karlovška |
| `koprivnisko-krizevska` | Koprivniško-križevska |
| `krapinsko-zagorska` | Krapinsko-zagorska |
| `lisko-senjska` | Liško-senjska |

The implementation includes a HEAD-check script that fetches `https://www.nepremicnine.net/oglasi-prodaja/{slug}/stanovanje/` for each slug and flags non-200 responses. Any failures are corrected (likely candidates: `mesto-zagreb` could be `grad-zagreb`; `medimurska` could differ) before merging.

## Validators

In `backend/app/schemas/scraper.py`, `ProjectFilters`:

- `country` declared first (so `info.data["country"]` is populated for later validators).
- `validate_region`: `v in REGIONS[info.data["country"]]`. Error message names the country.
- `validate_sub_region`: if `country == "hr"` and `v is not None`, reject. Otherwise behaviour is unchanged (must be in `SUBREGIONS["si"][region]`).
- `validate_rooms`, price/size/year range validators: unchanged, not country-specific.

## URL builder

`backend/app/scraper/url_builder.py` — no changes. Validators ensure the region slug is already correct for the chosen country, and the builder emits it as-is into position 2 of the path. No `/hrvaska/` segment is introduced (confirmed by example URL).

## Parser

`backend/app/scraper/list_parser.py`, `detail_parser.py` — no changes. Site-structural, country-agnostic. Existing transaction/property type maps (`Prodaja`/`Oddaja`/`Stanovanje`/…) continue to apply because property/room/transaction taxonomies are identical across countries on this site.

## Frontend dialog

`frontend/src/features/projects/ProjectCreateDialog.tsx`:

- New `country` state, defaulting to `"si"`.
- A `<select>` populated from `COUNTRIES` rendered above the Transaction/Property-Type row.
- Changing `country` resets `region` and `subRegion` to `""`.
- Region `<select>` reads from `REGIONS[country]`.
- The sub-region row is hidden entirely when `country === "hr"` (region select becomes full-width that row, or the grid collapses to a single column — implementation choice, both acceptable).
- `handleSubmit` includes `country` in the submitted `ProjectFilters`.

`frontend/src/features/projects/ProjectSettingsPanel.tsx`: if it offers filter editing, apply the same country/region/sub-region logic. If it's read-only display, render the country label from `COUNTRIES[filters.country ?? "si"]`. Decide during implementation after reading the file.

`frontend/src/api/projects.ts`: extend the `ProjectFilters` TS type with a required `country: "si" | "hr"` field. The default lives in the form state, not the type — every payload we send already has it.

## Migration

None. Existing projects' `filters` JSONB lacks `country`; Pydantic's default `"si"` populates it on read. `scrape_url` is already a full URL stored at creation, so historical scrapes keep working without rebuild.

## Tests

Add to the existing backend test suite (`backend/tests/`):

- Croatian filter validates: `country="hr", region="primorsko-goranska", sub_region=None, property_type="stanovanje"`.
- Slovenian filter with sub-region still validates (regression).
- Croatian filter with non-null `sub_region` is rejected.
- Croatian filter with a Slovenian region slug (e.g. `gorenjska`) is rejected with a clear error.
- URL builder produces `https://www.nepremicnine.net/oglasi-prodaja/primorsko-goranska/stanovanje/` for the Croatian filter above.
- Defaulting: `ProjectFilters(**{...without country...})` yields `country == "si"`.

Frontend smoke check: open the dialog, switch country to Croatia, verify the region dropdown repopulates with Croatian counties and the sub-region row disappears.

## Risks

- **Slug mismatch:** the 20 unverified slugs may not match nepremicnine.net's actual URL forms. Mitigated by the HEAD-check script during implementation.
- **Form-value vs URL-slug duality:** the site's dropdown uses numeric `value` attributes (33, 34, …) while URLs use slugs. We only ever use slugs; the numeric IDs are not stored anywhere. No risk beyond clarity.
- **Sub-region assumption:** we assume Croatia genuinely has no sub-region selector. If the site exposes one at a level we haven't seen, v1 ships without it and a follow-up adds them. Acceptable per scope.
