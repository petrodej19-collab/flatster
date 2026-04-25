import html
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation


@dataclass
class ListingDetail:
    title: str | None = None
    description: str | None = None
    images: list[str] = field(default_factory=list)
    size_m2: Decimal | None = None
    floor: str | None = None
    year_built: int | None = None
    year_renovated: int | None = None
    energy_class: str | None = None
    land_size_m2: Decimal | None = None
    location: str | None = None
    num_bedrooms: int | None = None
    num_bathrooms: int | None = None


def parse_detail_page(html: str) -> ListingDetail:
    return ListingDetail(
        title=_parse_title(html),
        description=_parse_description(html),
        images=_parse_images(html),
        size_m2=_parse_size(html),
        floor=_parse_floor(html),
        year_built=_parse_year_built(html),
        year_renovated=_parse_year_renovated(html),
        energy_class=_parse_energy_class(html),
        land_size_m2=_parse_land_size(html),
        location=_parse_location(html),
        num_bedrooms=_parse_int_attribute(html, r"Št\.\s*spalnic:\s*(\d+)"),
        num_bathrooms=_parse_int_attribute(html, r"Št\.\s*kopalnic:\s*(\d+)"),
    )


def _parse_title(html: str) -> str | None:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
    if match:
        return _clean_text(match.group(1))
    return None


def _parse_description(html: str) -> str | None:
    # Primary: <div itemprop="disambiguatingDescription"> (rich content in detail page)
    match = re.search(
        r'itemprop="disambiguatingDescription">(.*?)</div>',
        html,
        re.DOTALL,
    )
    if match:
        text = _clean_text(match.group(1), preserve_newlines=True)
        if text:
            return text

    # Fallback: content inside id="desc" tab
    match = re.search(
        r'id="desc"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html,
        re.DOTALL,
    )
    if match:
        text = _clean_text(match.group(1), preserve_newlines=True)
        text = re.sub(r"^Dodaten opis nepremičnine\s*", "", text)
        if text:
            return text

    return None


def _parse_images(html: str) -> list[str]:
    # Collect from both data-src and src attributes
    pattern = r'(?:data-src|src)="(https://img\.nepremicnine\.net/slonep_oglasi2?/[^"]+)"'
    urls = re.findall(pattern, html)
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _parse_size(html: str) -> Decimal | None:
    match = re.search(r"Velikost:\s*([\d.,]+)\s*m", html)
    if match:
        try:
            return Decimal(match.group(1).replace(",", "."))
        except InvalidOperation:
            pass
    return None


def _parse_floor(html: str) -> str | None:
    match = re.search(r"Nadstropje:\s*([\d/]+)", html)
    if match:
        return match.group(1)
    if re.search(r"pritličje", html, re.IGNORECASE):
        return "pritličje"
    return None


def _parse_year_built(html: str) -> int | None:
    patterns = [
        r"zgrajeno\s+l\.\s*(\d{4})",
        r"Leto izgradnje[:\s]*(\d{4})",
        r"začetek gradnje l\.\s*(\d{4})",
        r"zgrajena leta\s+(\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _parse_year_renovated(html: str) -> int | None:
    patterns = [
        r"adaptirano\s+l\.\s*(\d{4})",
        r"prenovljeno\s+l\.\s*(\d{4})",
        r"renovirano\s+l\.\s*(\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _parse_energy_class(html: str) -> str | None:
    match = re.search(r"energijski razred[:\s]*([A-G]\d?)", html, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _parse_land_size(html: str) -> Decimal | None:
    match = re.search(r"Zemljišče:\s*([\d.,]+)\s*m", html)
    if match:
        try:
            val = Decimal(match.group(1).replace(",", "."))
            if val > 0:
                return val
        except InvalidOperation:
            pass
    return None


def _parse_location(html: str) -> str | None:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
    if match:
        title = _clean_text(match.group(1))
        parts = title.split(",")
        if parts:
            return parts[0].strip()
    return None


def _parse_int_attribute(html: str, pattern: str) -> int | None:
    match = re.search(pattern, html)
    if match:
        return int(match.group(1))
    return None


def _clean_text(text: str, preserve_newlines: bool = False) -> str:
    if preserve_newlines:
        # Convert block-level HTML to newlines before stripping tags
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        # Collapse spaces within lines but keep newlines
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        text = "\n".join(line for line in lines if line)
    else:
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text)
    return text.strip()
