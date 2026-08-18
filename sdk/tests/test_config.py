"""Tests for AirVaultConfig — env var loading, defaults, overrides."""

import os
import pytest
from airvault.config import AirVaultConfig


class TestConfigDefaults:
    """Verify sensible defaults."""

    def test_default_qdrant_host(self):
        config = AirVaultConfig()
        assert config.qdrant_host == "localhost"

    def test_default_qdrant_port(self):
        config = AirVaultConfig()
        assert config.qdrant_port == 6333

    def test_default_embedding_model(self):
        config = AirVaultConfig()
        assert "bge-small" in config.embedding_model

    def test_default_dimension(self):
        config = AirVaultConfig()
        assert config.embedding_dimension == 384

    def test_default_chunk_size(self):
        config = AirVaultConfig()
        assert config.chunk_size == 512

    def test_default_dedup_enabled(self):
        config = AirVaultConfig()
        assert config.dedup_enabled is True

    def test_default_embedding_batch_size(self):
        config = AirVaultConfig()
        assert config.embedding_batch_size == 64


class TestConfigOverrides:
    """Verify constructor overrides work."""

    def test_override_qdrant_host(self):
        config = AirVaultConfig(qdrant_host="10.0.0.5")
        assert config.qdrant_host == "10.0.0.5"

    def test_override_embedding_model(self):
        config = AirVaultConfig(embedding_model="BAAI/bge-base-en-v1.5", embedding_dimension=768)
        assert config.embedding_model == "BAAI/bge-base-en-v1.5"
        assert config.embedding_dimension == 768

    def test_override_chunk_params(self):
        config = AirVaultConfig(chunk_size=256, chunk_overlap=32, min_chunk_size=25)
        assert config.chunk_size == 256
        assert config.chunk_overlap == 32
        assert config.min_chunk_size == 25

    def test_disable_dedup(self):
        config = AirVaultConfig(dedup_enabled=False)
        assert config.dedup_enabled is False


class TestConfigFromEnv:
    """Verify AIRVAULT_* env vars are picked up."""

    def test_env_qdrant_host(self, monkeypatch):
        monkeypatch.setenv("AIRVAULT_QDRANT_HOST", "10.0.0.99")
        config = AirVaultConfig()
        assert config.qdrant_host == "10.0.0.99"

    def test_env_embedding_model(self, monkeypatch):
        monkeypatch.setenv("AIRVAULT_EMBEDDING_MODEL", "custom/model")
        config = AirVaultConfig()
        assert config.embedding_model == "custom/model"

    def test_env_dedup_disabled(self, monkeypatch):
        monkeypatch.setenv("AIRVAULT_DEDUP_ENABLED", "false")
        config = AirVaultConfig()
        assert config.dedup_enabled is False

    def test_env_log_level(self, monkeypatch):
        monkeypatch.setenv("AIRVAULT_LOG_LEVEL", "DEBUG")
        config = AirVaultConfig()
        assert config.log_level == "DEBUG"

    def test_constructor_overrides_env(self, monkeypatch):
        monkeypatch.setenv("AIRVAULT_QDRANT_HOST", "from-env")
        config = AirVaultConfig(qdrant_host="from-constructor")
        assert config.qdrant_host == "from-constructor"
