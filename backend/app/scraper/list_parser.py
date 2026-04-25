import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.scraper.constants import BASE_URL


@dataclass
class ListingCard:
    external_id: str
    url: str
    title: str
    price: Decimal | None = None
    size_m2: Decimal | None = None
    rooms: str | None = None
    year_built: int | None = None
    floor: str | None = None
    property_type: str | None = None
    transaction_type: str | None = None
    agency: str | None = None
    thumbnail_url: str | None = None


def parse_list_page(html: str) -> tuple[list[ListingCard], int]:
    """Parse listing cards and total page count from a search results HTML page."""
    cards = _parse_cards(html)
    total_pages = _parse_total_pages(html)
    return cards, total_pages


def _parse_cards(html: str) -> list[ListingCard]:
    cards: list[ListingCard] = []
    parts = re.split(r'<div\s+class="property-box\s', html)

    for part in parts[1:]:
        card = _parse_single_card(part)
        if card:
            cards.append(card)

    return cards


def _parse_single_card(card_html: str) -> ListingCard | None:
    # External ID + URL
    url_match = re.search(
        r'href="(https://www\.nepremicnine\.net/[^"]*_(\d+)/)"', card_html
    )
    if not url_match:
        url_match = re.search(r'href="(/[^"]*_(\d+)/)"', card_html)
        if not url_match:
            return None

    raw_url = url_match.group(1)
    url = raw_url if raw_url.startswith("http") else BASE_URL + raw_url
    external_id = url_match.group(2)

    # Title
    title_match = re.search(r"<h2[^>]*>(.*?)</h2>", card_html, re.DOTALL)
    title = _clean_text(title_match.group(1)) if title_match else ""

    # Price
    price = None
    price_match = re.search(r'itemprop="price"\s+content="([^"]+)"', card_html)
    if price_match:
        try:
            price = Decimal(price_match.group(1))
        except InvalidOperation:
            pass

    # Size/Year/Floor — from <ul itemprop="disambiguatingDescription">
    size_m2 = None
    year_built = None
    floor = None
    dd_match = re.search(
        r'itemprop="disambiguatingDescription">(.*?)</ul>', card_html, re.DOTALL
    )
    if dd_match:
        dd_html = dd_match.group(1)

        size_match = re.search(r"([\d.,]+)\s*m<sup>2", dd_html)
        if size_match:
            try:
                size_m2 = Decimal(size_match.group(1).replace(",", "."))
            except InvalidOperation:
                pass

        year_match = re.search(r"leto\.svg[^>]*>(\d{4})", dd_html)
        if year_match:
            year_built = int(year_match.group(1))

        floor_match = re.search(r"nadstropje\.svg[^>]*>([\w/]+)", dd_html)
        if floor_match:
            floor = floor_match.group(1)

    # Rooms
    rooms = None
    rooms_match = re.search(r'class="tipi"[^>]*>(.*?)</span>', card_html, re.DOTALL)
    if rooms_match:
        rooms = _clean_text(rooms_match.group(1))

    # Transaction + property type
    property_type = None
    transaction_type = None
    type_match = re.search(
        r'class="font-roboto"[^>]*>\s*(Prodaja|Oddaja|Najem|Nakup):\s*(\w+)',
        card_html,
        re.DOTALL,
    )
    if type_match:
        trans_map = {
            "Prodaja": "prodaja",
            "Oddaja": "oddaja",
            "Najem": "oddaja",
            "Nakup": "prodaja",
        }
        transaction_type = trans_map.get(
            type_match.group(1), type_match.group(1).lower()
        )
        prop_map = {
            "Stanovanje": "stanovanje",
            "Hiša": "hisa",
            "Vikend": "vikend",
            "Posest": "posest",
            "Poslovni": "poslovni-prostor",
            "Garaža": "garaza",
            "Počitniški": "pocitniski-objekt",
        }
        property_type = prop_map.get(
            type_match.group(2), type_match.group(2).lower()
        )

    # Agency
    agency = None
    agency_match = re.search(
        r'itemprop="seller".*?itemprop="name"\s+content="([^"]+)"',
        card_html,
        re.DOTALL,
    )
    if agency_match:
        agency = _clean_text(agency_match.group(1))

    # Thumbnail
    thumbnail_url = None
    thumb_match = re.search(
        r'data-src="(https://img\.nepremicnine\.net/slonep_oglasi[^"]+)"', card_html
    )
    if thumb_match:
        thumbnail_url = thumb_match.group(1)

    return ListingCard(
        external_id=external_id,
        url=url,
        title=title,
        price=price,
        size_m2=size_m2,
        rooms=rooms,
        year_built=year_built,
        floor=floor,
        property_type=property_type,
        transaction_type=transaction_type,
        agency=agency,
        thumbnail_url=thumbnail_url,
    )


def _parse_total_pages(html: str) -> int:
    # Use data-pages attribute on the pagination ul
    data_pages = re.search(r'data-pages="(\d+)"', html)
    if data_pages:
        return int(data_pages.group(1))

    # Fallback: find highest numbered page link
    page_matches = re.findall(r'href="[^"]+/(\d+)/"[^>]*>\s*\1\s*<', html)
    if page_matches:
        return max(int(p) for p in page_matches)

    return 1


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
