"""Tests for API key authentication."""

import pytest
from app.services.auth import AuthService


class TestAuthService:
    def test_generate_api_key_format(self):
        key = AuthService.generate_api_key()
        assert key.startswith("vm_")
        assert len(key) > 30

    def test_generate_unique_keys(self):
        keys = {AuthService.generate_api_key() for _ in range(100)}
        assert len(keys) == 100  # All unique

    def test_hash_and_verify(self):
        key = AuthService.generate_api_key()
        hashed = AuthService.hash_api_key(key)
        assert AuthService.verify_api_key(key, hashed) is True

    def test_wrong_key_fails_verification(self):
        key = AuthService.generate_api_key()
        hashed = AuthService.hash_api_key(key)
        wrong_key = AuthService.generate_api_key()
        assert AuthService.verify_api_key(wrong_key, hashed) is False

    def test_hash_is_not_plaintext(self):
        key = AuthService.generate_api_key()
        hashed = AuthService.hash_api_key(key)
        assert key not in hashed
