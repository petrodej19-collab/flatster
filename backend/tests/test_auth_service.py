from uuid import uuid4

import pytest


class TestHashPassword:
    def test_returns_bcrypt_hash(self):
        from app.services.auth import hash_password

        result = hash_password("testpass123")
        assert result.startswith("$2b$")

    def test_different_passwords_different_hashes(self):
        from app.services.auth import hash_password

        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2


class TestVerifyPassword:
    def test_correct_password(self):
        from app.services.auth import hash_password, verify_password

        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_wrong_password(self):
        from app.services.auth import hash_password, verify_password

        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False


class TestCreateAccessToken:
    def test_returns_string(self):
        from app.services.auth import create_access_token

        token = create_access_token(uuid4())
        assert isinstance(token, str)
        assert len(token) > 0

    def test_contains_three_parts(self):
        from app.services.auth import create_access_token

        token = create_access_token(uuid4())
        parts = token.split(".")
        assert len(parts) == 3


class TestDecodeAccessToken:
    def test_roundtrip(self):
        from app.services.auth import create_access_token, decode_access_token

        user_id = uuid4()
        token = create_access_token(user_id)
        decoded_id = decode_access_token(token)
        assert decoded_id == user_id

    def test_invalid_token_raises(self):
        from app.services.auth import decode_access_token

        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token("not.a.token")

    def test_expired_token_raises(self):
        from datetime import timedelta
        from app.services.auth import _create_token_with_expiry, decode_access_token

        user_id = uuid4()
        token = _create_token_with_expiry(user_id, timedelta(seconds=-1))
        with pytest.raises(ValueError, match="Token has expired"):
            decode_access_token(token)
