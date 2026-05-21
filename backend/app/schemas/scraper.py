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
