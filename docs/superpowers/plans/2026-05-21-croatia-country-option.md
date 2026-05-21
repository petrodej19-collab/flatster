# Croatia Country Option Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users pick Croatia (alongside Slovenia) when creating a project. Filter validation, region taxonomy, and the create-project dialog all become country-aware.

**Architecture:** Add a `country: "si" | "hr"` field to `ProjectFilters` (Pydantic + TS), default `"si"`. Replace flat `REGIONS`/`SUBREGIONS` dicts with country-keyed ones in both `backend/app/scraper/constants.py` and `frontend/src/lib/constants.ts`. Validators branch on `country`. URL builder and parsers are unchanged — nepremicnine.net uses the same URL shape for Croatian regions (`/oglasi-prodaja/<region-slug>/<property-type>/`).

**Tech Stack:** Python 3 / FastAPI / Pydantic / SQLAlchemy (JSONB column) / pytest on the backend. React 19 / TypeScript / Vite / React Query on the frontend.

---

## File Structure

**Backend, modify:**
- `backend/app/scraper/constants.py` — country-key `REGIONS` and `SUBREGIONS`, add `COUNTRIES`.
- `backend/app/schemas/scraper.py` — add `country` field, update `validate_region` and `validate_sub_region`.
- `backend/tests/test_url_builder.py` — extend `TestProjectFiltersValidation` with country cases; add Croatia URL tests.

**Backend, create:**
- `backend/scripts/verify_hr_slugs.py` — one-off HEAD-check script for the 21 Croatian region URLs.

**Frontend, modify:**
- `frontend/src/lib/constants.ts` — country-key `REGIONS`/`SUBREGIONS`, add `COUNTRIES`.
- `frontend/src/api/projects.ts` — add `country` to `ProjectFilters` type.
- `frontend/src/features/projects/ProjectCreateDialog.tsx` — country dropdown, conditional sub-region row, reset region/sub-region on country change.
- `frontend/src/features/projects/ProjectSettingsPanel.tsx` — lookup region label via country-keyed dict; display country.

**Untouched (confirm during implementation):**
- `backend/app/scraper/url_builder.py`
- `backend/app/scraper/list_parser.py`
- `backend/app/scraper/detail_parser.py`
- `backend/app/api/projects.py` (request body type already references `ProjectFilters`)

---

### Task 1: Backend constants — restructure REGIONS/SUBREGIONS by country, add COUNTRIES and Croatian regions

**Files:**
- Modify: `backend/app/scraper/constants.py`

- [ ] **Step 1: Read the current file to confirm structure**

Run: `wc -l backend/app/scraper/constants.py` (sanity check before editing; expect ~148 lines).

- [ ] **Step 2: Restructure REGIONS, SUBREGIONS; add COUNTRIES**

Replace the existing `REGIONS` and `SUBREGIONS` blocks (top of file, through the closing `}` of `SUBREGIONS`) with:

```python
COUNTRIES: dict[str, str] = {
    "si": "Slovenija",
    "hr": "Hrvaška",
}

REGIONS: dict[str, dict[str, str]] = {
    "si": {
        "ljubljana-mesto": "LJ-mesto",
        "ljubljana-okolica": "LJ-okolica",
        "gorenjska": "Gorenjska",
        "juzna-primorska": "J. Primorska",
        "severna-primorska": "S. Primorska",
        "notranjska": "Notranjska",
        "savinjska": "Savinjska",
        "podravska": "Podravska",
        "koroska": "Koroška",
        "dolenjska": "Dolenjska",
        "posavska": "Posavska",
        "zasavska": "Zasavska",
        "pomurska": "Pomurska",
    },
    "hr": {
        "primorsko-goranska": "Primorsko-goranska",
        "istrska": "Istrska",
        "mesto-zagreb": "Mesto Zagreb",
        "zagrebska": "Zagrebška",
        "dubrovnisko-neretvanska": "Dubrovniško-neretvanska",
        "splitsko-dalmatinska": "Splitsko-dalmatinska",
        "sibenisko-kninska": "Šibeniško-kninska",
        "zadarska": "Zadarska",
        "osijesko-baranjska": "Osiješko-baranjska",
        "vukovarsko-sremska": "Vukovarsko-sremska",
        "virovitisko-podravska": "Virovitiško-podravska",
        "pozesko-slavonska": "Požeško-slavonska",
        "brodsko-posavska": "Brodsko-posavska",
        "medimurska": "Međimurska",
        "varazdinska": "Varaždinska",
        "bjelovarsko-bilogorska": "Bjelovarsko-bilogorska",
        "sisasko-moslavinska": "Sisaško-moslavinska",
        "karlovska": "Karlovška",
        "koprivnisko-krizevska": "Koprivniško-križevska",
        "krapinsko-zagorska": "Krapinsko-zagorska",
        "lisko-senjska": "Liško-senjska",
    },
}

SUBREGIONS: dict[str, dict[str, dict[str, str]]] = {
    "si": {
        "ljubljana-mesto": {
            "lj-bezigrad": "Lj. Bežigrad",
            "lj-center": "Lj. Center",
            "lj-moste-polje": "Lj. Moste-Polje",
            "lj-siska": "Lj. Šiška",
            "lj-vic-rudnik": "Lj. Vič-Rudnik",
        },
        "ljubljana-okolica": {
            "domzale": "Domžale",
            "grosuplje": "Grosuplje",
            "kamnik": "Kamnik",
            "litija": "Litija",
            "lj-jz-del-vic-rudnik": "Lj. J&Z del (Vič, Rudnik)",
            "lj-sv-del-bezigrad": "Lj. SV del (Bežigrad)",
            "lj-sz-del-siska": "Lj. SZ del (Šiška)",
            "lj-v-del-moste-polje": "Lj. V del (Moste-Polje)",
            "logatec": "Logatec",
            "vrhnika": "Vrhnika",
        },
        "gorenjska": {
            "jesenice": "Jesenice",
            "kranj": "Kranj",
            "radovljica": "Radovljica",
            "skofja-loka": "Škofja Loka",
            "trzic": "Tržič",
        },
        "juzna-primorska": {
            "izola": "Izola",
            "koper": "Koper",
            "piran": "Piran",
            "sezana": "Sežana",
        },
        "severna-primorska": {
            "ajdovscina": "Ajdovščina",
            "idrija": "Idrija",
            "nova-gorica": "Nova Gorica",
            "tolmin": "Tolmin",
        },
        "notranjska": {
            "cerknica": "Cerknica",
            "ilirska-bistrica": "Ilirska Bistrica",
            "postojna": "Postojna",
        },
        "savinjska": {
            "celje": "Celje",
            "lasko": "Laško",
            "mozirje": "Mozirje",
            "slovenske-konjice": "Slovenske Konjice",
            "sentjur": "Šentjur",
            "smarje-pri-jelsah": "Šmarje pri Jelšah",
            "velenje": "Velenje",
            "zalec": "Žalec",
        },
        "podravska": {
            "lenart": "Lenart",
            "maribor": "Maribor",
            "ormoz": "Ormož",
            "pesnica": "Pesnica",
            "ptuj": "Ptuj",
            "ruse": "Ruše",
            "slovenska-bistrica": "Slovenska Bistrica",
        },
        "koroska": {
            "dravograd": "Dravograd",
            "radlje-ob-dravi": "Radlje ob Dravi",
            "ravne-na-koroskem": "Ravne na Koroškem",
            "slovenj-gradec": "Slovenj Gradec",
        },
        "dolenjska": {
            "crnomelj": "Črnomelj",
            "kocevje": "Kočevje",
            "metlika": "Metlika",
            "novo-mesto": "Novo mesto",
            "ribnica": "Ribnica",
            "trebnje": "Trebnje",
        },
        "posavska": {
            "brezice": "Brežice",
            "krsko": "Krško",
            "sevnica": "Sevnica",
        },
        "zasavska": {
            "hrastnik": "Hrastnik",
            "trbovlje": "Trbovlje",
            "zagorje-ob-savi": "Zagorje ob Savi",
        },
        "pomurska": {
            "gornja-radgona": "Gornja Radgona",
            "lendava": "Lendava",
            "ljutomer": "Ljutomer",
            "murska-sobota": "Murska Sobota",
        },
    },
    "hr": {},
}
```

Leave `PROPERTY_TYPES`, `ROOM_TYPES`, `TRANSACTION_TYPES`, `BASE_URL`, `USER_AGENT`, `LISTINGS_PER_PAGE` untouched.

- [ ] **Step 3: Static check — import the module without errors**

Run: `cd backend && python -c "from app.scraper.constants import REGIONS, SUBREGIONS, COUNTRIES; print(len(REGIONS['hr']), len(SUBREGIONS['hr']))"`
Expected output: `21 0`

- [ ] **Step 4: Commit**

```bash
git add backend/app/scraper/constants.py
git commit -m "Add country-keyed REGIONS/SUBREGIONS with Croatian counties"
```

---

### Task 2: Backend schema — add country field and update validators (test-first)

**Files:**
- Modify: `backend/app/schemas/scraper.py`
- Modify: `backend/tests/test_url_builder.py` (adds tests to existing `TestProjectFiltersValidation`)

- [ ] **Step 1: Write failing tests**

Append the following to `backend/tests/test_url_builder.py` (inside `TestProjectFiltersValidation`):

```python
    def test_country_defaults_to_si(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="gorenjska",
            property_type="stanovanje",
        )
        assert filters.country == "si"

    def test_croatian_country_with_croatian_region(self):
        filters = ProjectFilters(
            country="hr",
            transaction="prodaja",
            region="primorsko-goranska",
            property_type="stanovanje",
        )
        assert filters.country == "hr"
        assert filters.region == "primorsko-goranska"

    def test_croatian_country_with_slovenian_region_rejected(self):
        with pytest.raises(ValueError, match="Invalid region"):
            ProjectFilters(
                country="hr",
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
            )

    def test_slovenian_country_with_croatian_region_rejected(self):
        with pytest.raises(ValueError, match="Invalid region"):
            ProjectFilters(
                country="si",
                transaction="prodaja",
                region="primorsko-goranska",
                property_type="stanovanje",
            )

    def test_croatian_country_rejects_sub_region(self):
        with pytest.raises(ValueError, match="sub_region"):
            ProjectFilters(
                country="hr",
                transaction="prodaja",
                region="primorsko-goranska",
                sub_region="anything",
                property_type="stanovanje",
            )

    def test_croatian_country_allows_null_sub_region(self):
        filters = ProjectFilters(
            country="hr",
            transaction="prodaja",
            region="istrska",
            sub_region=None,
            property_type="stanovanje",
        )
        assert filters.sub_region is None

    def test_invalid_country_value_rejected(self):
        with pytest.raises(ValueError):
            ProjectFilters(
                country="xx",
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_url_builder.py::TestProjectFiltersValidation -v`
Expected: all seven new tests FAIL (most with attribute/field errors since `country` doesn't exist yet).

- [ ] **Step 3: Update the schema to add `country` and branch validators**

Replace the contents of `backend/app/schemas/scraper.py` with:

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator

from app.scraper.constants import PROPERTY_TYPES, REGIONS, ROOM_TYPES, SUBREGIONS


class ProjectFilters(BaseModel):
    country: Literal["si", "hr"] = "si"
    transaction: Literal["prodaja", "oddaja"]
    region: str
    sub_region: str | None = None
    property_type: str
    rooms: list[str] | None = None
    price_from: int | None = None
    price_to: int | None = None
    size_from: int | None = None
    size_to: int | None = None
    year_from: int | None = None
    year_to: int | None = None

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str, info) -> str:
        country = info.data.get("country", "si")
        valid = REGIONS.get(country, {})
        if v not in valid:
            raise ValueError(
                f"Invalid region: {v} for country {country}. Must be one of: {list(valid.keys())}"
            )
        return v

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v: str) -> str:
        if v not in PROPERTY_TYPES:
            raise ValueError(f"Invalid property_type: {v}. Must be one of: {list(PROPERTY_TYPES.keys())}")
        return v

    @field_validator("sub_region")
    @classmethod
    def validate_sub_region(cls, v: str | None, info) -> str | None:
        if v is None:
            return v
        country = info.data.get("country", "si")
        region = info.data.get("region")
        country_subs = SUBREGIONS.get(country, {})
        if not country_subs:
            raise ValueError(
                f"sub_region is not supported for country {country}"
            )
        if region and region in country_subs:
            if v not in country_subs[region]:
                valid = list(country_subs[region].keys())
                raise ValueError(
                    f"Invalid sub_region: {v} for region {region}. Must be one of: {valid}"
                )
        return v

    @field_validator("rooms")
    @classmethod
    def validate_rooms(cls, v: list[str] | None, info) -> list[str] | None:
        if v is None:
            return v
        property_type = info.data.get("property_type")
        if property_type and property_type != "stanovanje":
            raise ValueError("rooms filter is only valid for property_type 'stanovanje'")
        for room in v:
            if room not in ROOM_TYPES:
                raise ValueError(f"Invalid room type: {room}. Must be one of: {ROOM_TYPES}")
        return v

    @field_validator("price_to")
    @classmethod
    def validate_price_range(cls, v: int | None, info) -> int | None:
        if v is not None and info.data.get("price_from") is not None:
            if v < info.data["price_from"]:
                raise ValueError("price_to must be >= price_from")
        return v

    @field_validator("size_to")
    @classmethod
    def validate_size_range(cls, v: int | None, info) -> int | None:
        if v is not None and info.data.get("size_from") is not None:
            if v < info.data["size_from"]:
                raise ValueError("size_to must be >= size_from")
        return v

    @field_validator("year_to")
    @classmethod
    def validate_year_range(cls, v: int | None, info) -> int | None:
        if v is not None and info.data.get("year_from") is not None:
            if v < info.data["year_from"]:
                raise ValueError("year_to must be >= year_from")
        return v


class ScrapedListing(BaseModel):
    external_id: str
    url: str
    title: str
    location: str | None = None
    region: str | None = None
    property_type: str | None = None
    transaction_type: str | None = None
    price: Decimal | None = None
    price_per_m2: Decimal | None = None
    size_m2: Decimal | None = None
    rooms: str | None = None
    year_built: int | None = None
    year_renovated: int | None = None
    floor: str | None = None
    land_size_m2: Decimal | None = None
    energy_class: str | None = None
    description: str | None = None
    images: list[str] = []
    agency: str | None = None
```

Notes:
- `country` is declared first so `info.data["country"]` is populated by the time `validate_region` and `validate_sub_region` run.
- `validate_region` reads `info.data.get("country", "si")` defensively in case a future caller passes data out of order.
- `ScrapedListing` is unchanged; included for clarity since we replaced the whole file.

- [ ] **Step 4: Run the new validator tests**

Run: `cd backend && pytest tests/test_url_builder.py::TestProjectFiltersValidation -v`
Expected: all tests in the class PASS (both the original ones and the seven new ones).

- [ ] **Step 5: Run the full url_builder test file as a regression check**

Run: `cd backend && pytest tests/test_url_builder.py -v`
Expected: all tests PASS. None of the existing Slovenia-only URL tests should break, because `country` defaults to `"si"`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/scraper.py backend/tests/test_url_builder.py
git commit -m "Add country field to ProjectFilters, branch region/sub_region validators"
```

---

### Task 3: Backend — Croatian URL builder regression tests

**Files:**
- Modify: `backend/tests/test_url_builder.py`

The URL builder source code does not change (validator guarantees the right region slug). We add tests to lock that in.

- [ ] **Step 1: Add Croatian URL builder tests**

Append the following methods to `class TestBuildScrapeUrl` in `backend/tests/test_url_builder.py`:

```python
    def test_croatian_basic_url(self):
        filters = ProjectFilters(
            country="hr",
            transaction="prodaja",
            region="primorsko-goranska",
            property_type="stanovanje",
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/primorsko-goranska/stanovanje/"

    def test_croatian_url_with_price_range(self):
        filters = ProjectFilters(
            country="hr",
            transaction="prodaja",
            region="istrska",
            property_type="hisa",
            price_from=100000,
            price_to=300000,
        )
        url = build_scrape_url(filters)
        assert url == (
            "https://www.nepremicnine.net/oglasi-prodaja/istrska/hisa/"
            "cena-od-100000-do-300000-eur/"
        )

    def test_croatian_url_rent(self):
        filters = ProjectFilters(
            country="hr",
            transaction="oddaja",
            region="mesto-zagreb",
            property_type="stanovanje",
            rooms=["2-sobno", "3-sobno"],
        )
        url = build_scrape_url(filters)
        assert url == (
            "https://www.nepremicnine.net/oglasi-oddaja/mesto-zagreb/stanovanje/"
            "2-sobno,3-sobno/"
        )
```

- [ ] **Step 2: Run the tests**

Run: `cd backend && pytest tests/test_url_builder.py::TestBuildScrapeUrl -v`
Expected: all tests PASS, including the three new Croatian ones.

- [ ] **Step 3: Run the full backend test suite as a wider regression check**

Run: `cd backend && pytest -v`
Expected: all tests PASS. No existing test depends on the old flat `REGIONS`/`SUBREGIONS` shape (verified by Task 2 step 5, but rerun here in case other tests touch them).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_url_builder.py
git commit -m "Add Croatian URL builder regression tests"
```

---

### Task 4: Backend — slug verification script

**Files:**
- Create: `backend/scripts/verify_hr_slugs.py`

A one-off check that HEAD-requests each Croatian region URL on nepremicnine.net and reports anything that's not 200. Catches slug derivations that don't match the live site (most likely candidates: `mesto-zagreb`, `medimurska`).

- [ ] **Step 1: Check that the scripts directory exists**

Run: `ls backend/scripts 2>/dev/null || echo NO_DIR`
If `NO_DIR`: `mkdir -p backend/scripts`.

- [ ] **Step 2: Create the verification script**

Write `backend/scripts/verify_hr_slugs.py`:

```python
"""Verify Croatian region slugs against nepremicnine.net.

Usage:
    python -m backend.scripts.verify_hr_slugs

Issues a HEAD request for each Croatian region slug as it would appear in a
search URL, and prints a summary of any slugs the site doesn't serve.
"""
from __future__ import annotations

import sys

import httpx

from app.scraper.constants import REGIONS

BASE = "https://www.nepremicnine.net/oglasi-prodaja"
PROPERTY = "stanovanje"


def check_slug(client: httpx.Client, slug: str) -> int:
    url = f"{BASE}/{slug}/{PROPERTY}/"
    response = client.head(url, follow_redirects=True, timeout=15.0)
    return response.status_code


def main() -> int:
    failures: list[tuple[str, int | str]] = []
    with httpx.Client(headers={"User-Agent": "FlatsterSlugCheck/1.0"}) as client:
        for slug, label in REGIONS["hr"].items():
            try:
                status_code = check_slug(client, slug)
            except httpx.HTTPError as exc:
                failures.append((slug, f"error: {exc}"))
                print(f"FAIL  {slug:30s} {label!r:35s} {exc}")
                continue
            marker = "OK  " if status_code == 200 else "FAIL"
            print(f"{marker}  {slug:30s} {label!r:35s} {status_code}")
            if status_code != 200:
                failures.append((slug, status_code))
    if failures:
        print(f"\n{len(failures)} slug(s) failed:")
        for slug, info in failures:
            print(f"  - {slug}: {info}")
        return 1
    print(f"\nAll {len(REGIONS['hr'])} Croatian slugs OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run the script**

Run: `cd backend && python -m scripts.verify_hr_slugs`
Expected: 21 OK lines, exit code 0. If any fail (`mesto-zagreb`, `medimurska`, or others), record the failures and proceed to Step 4.

- [ ] **Step 4 (conditional): Fix any failing slugs**

For each failed slug:
1. Open the nepremicnine.net Croatian search page in a browser, pick the region in the dropdown, submit, and read the resulting URL.
2. Update `REGIONS["hr"]` in `backend/app/scraper/constants.py` and `REGIONS.hr` in `frontend/src/lib/constants.ts` (added in Task 5) with the correct slug.
3. Re-run `python -m scripts.verify_hr_slugs` until all 21 pass.

If no slugs failed, skip this step.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/verify_hr_slugs.py
# If Step 4 made fixes:
git add backend/app/scraper/constants.py
git commit -m "Add Croatian slug verification script (and any required slug fixes)"
```

---

### Task 5: Frontend constants — mirror backend structure

**Files:**
- Modify: `frontend/src/lib/constants.ts`

- [ ] **Step 1: Replace the file contents**

Overwrite `frontend/src/lib/constants.ts` with:

```typescript
export const COUNTRIES: Record<string, string> = {
  "si": "Slovenija",
  "hr": "Hrvaška",
}

export const REGIONS: Record<string, Record<string, string>> = {
  si: {
    "ljubljana-mesto": "LJ-mesto",
    "ljubljana-okolica": "LJ-okolica",
    "gorenjska": "Gorenjska",
    "juzna-primorska": "J. Primorska",
    "severna-primorska": "S. Primorska",
    "notranjska": "Notranjska",
    "savinjska": "Savinjska",
    "podravska": "Podravska",
    "koroska": "Koroška",
    "dolenjska": "Dolenjska",
    "posavska": "Posavska",
    "zasavska": "Zasavska",
    "pomurska": "Pomurska",
  },
  hr: {
    "primorsko-goranska": "Primorsko-goranska",
    "istrska": "Istrska",
    "mesto-zagreb": "Mesto Zagreb",
    "zagrebska": "Zagrebška",
    "dubrovnisko-neretvanska": "Dubrovniško-neretvanska",
    "splitsko-dalmatinska": "Splitsko-dalmatinska",
    "sibenisko-kninska": "Šibeniško-kninska",
    "zadarska": "Zadarska",
    "osijesko-baranjska": "Osiješko-baranjska",
    "vukovarsko-sremska": "Vukovarsko-sremska",
    "virovitisko-podravska": "Virovitiško-podravska",
    "pozesko-slavonska": "Požeško-slavonska",
    "brodsko-posavska": "Brodsko-posavska",
    "medimurska": "Međimurska",
    "varazdinska": "Varaždinska",
    "bjelovarsko-bilogorska": "Bjelovarsko-bilogorska",
    "sisasko-moslavinska": "Sisaško-moslavinska",
    "karlovska": "Karlovška",
    "koprivnisko-krizevska": "Koprivniško-križevska",
    "krapinsko-zagorska": "Krapinsko-zagorska",
    "lisko-senjska": "Liško-senjska",
  },
}

export const SUBREGIONS: Record<string, Record<string, Record<string, string>>> = {
  si: {
    "ljubljana-mesto": {
      "lj-bezigrad": "Lj. Bežigrad",
      "lj-center": "Lj. Center",
      "lj-moste-polje": "Lj. Moste-Polje",
      "lj-siska": "Lj. Šiška",
      "lj-vic-rudnik": "Lj. Vič-Rudnik",
    },
    "ljubljana-okolica": {
      "domzale": "Domžale",
      "grosuplje": "Grosuplje",
      "kamnik": "Kamnik",
      "litija": "Litija",
      "lj-jz-del-vic-rudnik": "Lj. J&Z del (Vič, Rudnik)",
      "lj-sv-del-bezigrad": "Lj. SV del (Bežigrad)",
      "lj-sz-del-siska": "Lj. SZ del (Šiška)",
      "lj-v-del-moste-polje": "Lj. V del (Moste-Polje)",
      "logatec": "Logatec",
      "vrhnika": "Vrhnika",
    },
    "gorenjska": {
      "jesenice": "Jesenice",
      "kranj": "Kranj",
      "radovljica": "Radovljica",
      "skofja-loka": "Škofja Loka",
      "trzic": "Tržič",
    },
    "juzna-primorska": {
      "izola": "Izola",
      "koper": "Koper",
      "piran": "Piran",
      "sezana": "Sežana",
    },
    "severna-primorska": {
      "ajdovscina": "Ajdovščina",
      "idrija": "Idrija",
      "nova-gorica": "Nova Gorica",
      "tolmin": "Tolmin",
    },
    "notranjska": {
      "cerknica": "Cerknica",
      "ilirska-bistrica": "Ilirska Bistrica",
      "postojna": "Postojna",
    },
    "savinjska": {
      "celje": "Celje",
      "lasko": "Laško",
      "mozirje": "Mozirje",
      "slovenske-konjice": "Slovenske Konjice",
      "sentjur": "Šentjur",
      "smarje-pri-jelsah": "Šmarje pri Jelšah",
      "velenje": "Velenje",
      "zalec": "Žalec",
    },
    "podravska": {
      "lenart": "Lenart",
      "maribor": "Maribor",
      "ormoz": "Ormož",
      "pesnica": "Pesnica",
      "ptuj": "Ptuj",
      "ruse": "Ruše",
      "slovenska-bistrica": "Slovenska Bistrica",
    },
    "koroska": {
      "dravograd": "Dravograd",
      "radlje-ob-dravi": "Radlje ob Dravi",
      "ravne-na-koroskem": "Ravne na Koroškem",
      "slovenj-gradec": "Slovenj Gradec",
    },
    "dolenjska": {
      "crnomelj": "Črnomelj",
      "kocevje": "Kočevje",
      "metlika": "Metlika",
      "novo-mesto": "Novo mesto",
      "ribnica": "Ribnica",
      "trebnje": "Trebnje",
    },
    "posavska": {
      "brezice": "Brežice",
      "krsko": "Krško",
      "sevnica": "Sevnica",
    },
    "zasavska": {
      "hrastnik": "Hrastnik",
      "trbovlje": "Trbovlje",
      "zagorje-ob-savi": "Zagorje ob Savi",
    },
    "pomurska": {
      "gornja-radgona": "Gornja Radgona",
      "lendava": "Lendava",
      "ljutomer": "Ljutomer",
      "murska-sobota": "Murska Sobota",
    },
  },
  hr: {},
}

export const PROPERTY_TYPES: Record<string, string> = {
  "stanovanje": "Stanovanje",
  "hisa": "Hiša",
  "vikend": "Vikend",
  "posest": "Posest",
  "poslovni-prostor": "Poslovni prostor",
  "garaza": "Garaža",
  "pocitniski-objekt": "Počitniški objekt",
}

export const ROOM_TYPES: string[] = [
  "garsonjera",
  "1-sobno",
  "15-sobno",
  "2-sobno",
  "25-sobno",
  "3-sobno",
  "35-sobno",
  "4-sobno",
  "45-sobno",
  "5-in-vecsobno",
  "apartma",
  "soba",
]

export const TRANSACTION_TYPES = [
  { value: "prodaja", label: "Prodaja" },
  { value: "oddaja", label: "Oddaja" },
]
```

- [ ] **Step 2: TypeScript build to catch usage errors**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: build FAILS with errors in `ProjectCreateDialog.tsx` and `ProjectSettingsPanel.tsx` (they still index `REGIONS` as a flat dict). Those callers are fixed in Tasks 6 and 7. Note the errors but do not fix them here.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/constants.ts
git commit -m "Country-key frontend REGIONS/SUBREGIONS, add COUNTRIES and Croatian regions"
```

---

### Task 6: Frontend API type — add country to ProjectFilters

**Files:**
- Modify: `frontend/src/api/projects.ts`

- [ ] **Step 1: Add country field**

Replace the `ProjectFilters` interface (lines 4–16 of the file) with:

```typescript
export interface ProjectFilters {
  country: "si" | "hr"
  transaction: string
  region: string
  sub_region?: string | null
  property_type: string
  rooms?: string[] | null
  price_from?: number | null
  price_to?: number | null
  size_from?: number | null
  size_to?: number | null
  year_from?: number | null
  year_to?: number | null
}
```

Other interfaces and hooks in this file are unchanged.

- [ ] **Step 2: TypeScript build**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: still FAILS at `ProjectCreateDialog.tsx` (missing `country` on submission) and `ProjectSettingsPanel.tsx` (REGIONS shape). These get resolved by Tasks 7 and 8.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/projects.ts
git commit -m "Add country to frontend ProjectFilters type"
```

---

### Task 7: Frontend create dialog — country dropdown and conditional sub-region

**Files:**
- Modify: `frontend/src/features/projects/ProjectCreateDialog.tsx`

- [ ] **Step 1: Replace the file contents**

Overwrite `frontend/src/features/projects/ProjectCreateDialog.tsx` with:

```tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useCreateProject, type ProjectFilters } from "@/api/projects"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  COUNTRIES,
  REGIONS,
  SUBREGIONS,
  PROPERTY_TYPES,
  ROOM_TYPES,
  TRANSACTION_TYPES,
} from "@/lib/constants"

type Country = "si" | "hr"

export function ProjectCreateDialog() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [country, setCountry] = useState<Country>("si")
  const [transaction, setTransaction] = useState("prodaja")
  const [region, setRegion] = useState("")
  const [subRegion, setSubRegion] = useState("")
  const [propertyType, setPropertyType] = useState("stanovanje")
  const [rooms, setRooms] = useState<string[]>([])
  const [priceFrom, setPriceFrom] = useState("")
  const [priceTo, setPriceTo] = useState("")
  const [sizeFrom, setSizeFrom] = useState("")
  const [sizeTo, setSizeTo] = useState("")
  const [yearFrom, setYearFrom] = useState("")
  const [yearTo, setYearTo] = useState("")
  const [error, setError] = useState("")

  const createProject = useCreateProject()
  const navigate = useNavigate()

  const countryRegions = REGIONS[country] || {}
  const countrySubregions = SUBREGIONS[country] || {}
  const subRegions = region ? countrySubregions[region] || {} : {}
  const hasSubRegions = Object.keys(countrySubregions).length > 0
  const showRooms = propertyType === "stanovanje"

  const handleCountryChange = (value: string) => {
    const next = (value === "hr" ? "hr" : "si") as Country
    setCountry(next)
    setRegion("")
    setSubRegion("")
  }

  const handleRoomToggle = (room: string) => {
    setRooms((prev) =>
      prev.includes(room) ? prev.filter((r) => r !== room) : [...prev, room]
    )
  }

  const handleSubmit = async () => {
    if (!name || !region) {
      setError("Name and region are required")
      return
    }

    const filters: ProjectFilters = {
      country,
      transaction,
      region,
      sub_region: hasSubRegions ? subRegion || null : null,
      property_type: propertyType,
      rooms: showRooms && rooms.length > 0 ? rooms : null,
      price_from: priceFrom ? Number(priceFrom) : null,
      price_to: priceTo ? Number(priceTo) : null,
      size_from: sizeFrom ? Number(sizeFrom) : null,
      size_to: sizeTo ? Number(sizeTo) : null,
      year_from: yearFrom ? Number(yearFrom) : null,
      year_to: yearTo ? Number(yearTo) : null,
    }

    try {
      const project = await createProject.mutateAsync({ name, filters })
      setOpen(false)
      navigate(`/projects/${project.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create project")
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>
        New Project
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Project</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My search" />
          </div>

          <div className="space-y-2">
            <Label>Country</Label>
            <select
              className="w-full rounded-md border px-3 py-2 text-sm"
              value={country}
              onChange={(e) => handleCountryChange(e.target.value)}
            >
              {Object.entries(COUNTRIES).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Transaction</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={transaction}
                onChange={(e) => setTransaction(e.target.value)}
              >
                {TRANSACTION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Property Type</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={propertyType}
                onChange={(e) => {
                  setPropertyType(e.target.value)
                  if (e.target.value !== "stanovanje") setRooms([])
                }}
              >
                {Object.entries(PROPERTY_TYPES).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>

          {hasSubRegions ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Region</Label>
                <select
                  className="w-full rounded-md border px-3 py-2 text-sm"
                  value={region}
                  onChange={(e) => {
                    setRegion(e.target.value)
                    setSubRegion("")
                  }}
                >
                  <option value="">Select region...</option>
                  {Object.entries(countryRegions).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Sub-region (optional)</Label>
                <select
                  className="w-full rounded-md border px-3 py-2 text-sm"
                  value={subRegion}
                  onChange={(e) => setSubRegion(e.target.value)}
                  disabled={!region}
                >
                  <option value="">All</option>
                  {Object.entries(subRegions).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <Label>Region</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
              >
                <option value="">Select region...</option>
                {Object.entries(countryRegions).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          )}

          {showRooms && (
            <div className="space-y-2">
              <Label>Rooms</Label>
              <div className="flex flex-wrap gap-2">
                {ROOM_TYPES.map((room) => (
                  <button
                    key={room}
                    type="button"
                    onClick={() => handleRoomToggle(room)}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      rooms.includes(room)
                        ? "border-primary bg-primary text-primary-foreground"
                        : "hover:bg-muted"
                    }`}
                  >
                    {room}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Price from (EUR)</Label>
              <Input type="number" value={priceFrom} onChange={(e) => setPriceFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Price to (EUR)</Label>
              <Input type="number" value={priceTo} onChange={(e) => setPriceTo(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Size from (m2)</Label>
              <Input type="number" value={sizeFrom} onChange={(e) => setSizeFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Size to (m2)</Label>
              <Input type="number" value={sizeTo} onChange={(e) => setSizeTo(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Year from</Label>
              <Input type="number" value={yearFrom} onChange={(e) => setYearFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Year to</Label>
              <Input type="number" value={yearTo} onChange={(e) => setYearTo(e.target.value)} />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button className="w-full" onClick={handleSubmit} disabled={createProject.isPending}>
            {createProject.isPending ? "Creating..." : "Create Project"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

Notes on changes vs. the original file:
- New `country` state, defaulting to `"si"`.
- New top-level country `<select>` (its own row, full width).
- Region/sub-region row is conditional on `hasSubRegions` — for Croatia (`SUBREGIONS["hr"] = {}`) the region select takes the full row width.
- Changing country resets region and sub-region.
- `handleSubmit` includes `country` in the payload.

- [ ] **Step 2: TypeScript build**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: only one remaining error class — in `ProjectSettingsPanel.tsx`. Fixed in Task 8.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/projects/ProjectCreateDialog.tsx
git commit -m "Add country dropdown to project create dialog, conditional sub-region"
```

---

### Task 8: Frontend settings panel — country-aware region lookup, display country

**Files:**
- Modify: `frontend/src/features/projects/ProjectSettingsPanel.tsx`

- [ ] **Step 1: Update region lookup and add country display**

Edit `frontend/src/features/projects/ProjectSettingsPanel.tsx`:

1. Change the import line:

```typescript
import { COUNTRIES, REGIONS, PROPERTY_TYPES } from "@/lib/constants"
```

2. Replace the region display block (the `<div>` containing `REGIONS[project.filters.region]`) with the country + region lookup:

```tsx
        <div>
          <span className="text-muted-foreground">Country: </span>
          {COUNTRIES[project.filters.country ?? "si"] ?? project.filters.country ?? "si"}
        </div>
        <div>
          <span className="text-muted-foreground">Region: </span>
          {REGIONS[project.filters.country ?? "si"]?.[project.filters.region]
            ?? project.filters.region}
        </div>
```

The `?? "si"` fallback handles historical projects whose `filters` JSONB was written before the `country` field existed and where the response surface might still hand back a row without it (the backend's Pydantic default fills it in, but defensive coding here is cheap).

- [ ] **Step 2: TypeScript build**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: PASS. No remaining type errors anywhere in the project.

- [ ] **Step 3: Frontend production build**

Run: `cd frontend && npm run build`
Expected: build succeeds, no errors.

- [ ] **Step 4: Manual smoke test in the dev server**

Run the app per the project's normal dev workflow (likely `docker-compose up` from the repo root or `cd frontend && npm run dev` against a running backend). In the browser:
1. Open "New Project". Country dropdown shows "Slovenija" and "Hrvaška". Default is Slovenija. Two-column region/sub-region grid is visible.
2. Switch country to "Hrvaška". Region dropdown now lists the 21 Croatian counties starting with Primorsko-goranska. The sub-region selector is gone; the region select spans the full row.
3. Pick "Primorsko-goranska", property type Stanovanje, fill name, click "Create Project". Project is created and you navigate to its detail page.
4. On the detail page, the settings panel shows "Country: Hrvaška" and "Region: Primorsko-goranska".
5. Switch back to "New Project" → country Slovenija → confirm the Slovenian region list returns and the sub-region row reappears.

Record any failures and address them before committing. If verification succeeds, proceed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/projects/ProjectSettingsPanel.tsx
git commit -m "Display country and country-aware region label in project settings"
```

---

## Verification (end-of-plan)

- [ ] **Backend test suite green**

Run: `cd backend && pytest -v`
Expected: every test PASSES. No regressions in existing Slovenian-flow tests; new Croatian validator and URL builder tests pass.

- [ ] **Croatian slugs verified against live site**

Confirm Task 4 Step 3 reported all 21 OK (or that Step 4 patched any failures and the re-run was OK).

- [ ] **Frontend type-check and build green**

Run: `cd frontend && npx tsc -b --noEmit && npm run build`
Expected: both succeed.

- [ ] **Manual smoke test pass**

Task 8 Step 4 completed without issues.

- [ ] **Existing projects still work**

Open a project that existed before this change. The settings panel renders without error, shows "Country: Slovenija" via the `?? "si"` fallback, and the region label resolves correctly. Trigger a scrape and confirm it succeeds.
