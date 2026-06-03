from io import BytesIO

from PIL import Image


def encode_webp(raw: bytes, max_width: int = 800, quality: int = 80) -> bytes:
    """Decode raw image bytes, downscale if wider than max_width, return WebP bytes."""
    img = Image.open(BytesIO(raw))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if img.width > max_width:
        new_height = round(img.height * max_width / img.width)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, format="WEBP", quality=quality, method=4)
    return out.getvalue()
