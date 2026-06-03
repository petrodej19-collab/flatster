from io import BytesIO

from PIL import Image

from app.services.image_fetcher import encode_webp


def _make_jpeg(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_encode_webp_resizes_wide_image_to_max_800():
    raw = _make_jpeg(1600, 1200)
    out = encode_webp(raw, max_width=800)
    img = Image.open(BytesIO(out))
    assert img.format == "WEBP"
    assert img.width == 800
    assert img.height == 600


def test_encode_webp_leaves_small_image_unscaled():
    raw = _make_jpeg(400, 300)
    out = encode_webp(raw, max_width=800)
    img = Image.open(BytesIO(out))
    assert img.format == "WEBP"
    assert img.width == 400
    assert img.height == 300


def test_encode_webp_handles_png_input():
    img = Image.new("RGB", (1200, 900), color=(10, 20, 30))
    buf = BytesIO()
    img.save(buf, format="PNG")
    out = encode_webp(buf.getvalue(), max_width=800)
    assert Image.open(BytesIO(out)).format == "WEBP"
