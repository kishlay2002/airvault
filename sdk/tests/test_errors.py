"""Tests for the AirVault error hierarchy."""

import pytest
from airvault.errors import (
    AirVaultError,
    IngestionError,
    ExtractionError,
    UnsupportedFileTypeError,
    DuplicateDocumentError,
    RetrievalError,
    CollectionNotFoundError,
    ConfigurationError,
    StorageError,
)


class TestErrorHierarchy:
    """Verify all errors inherit from AirVaultError."""

    def test_ingestion_error_is_airvault_error(self):
        assert issubclass(IngestionError, AirVaultError)

    def test_extraction_error_is_ingestion_error(self):
        assert issubclass(ExtractionError, IngestionError)
        assert issubclass(ExtractionError, AirVaultError)

    def test_unsupported_file_type_is_ingestion_error(self):
        assert issubclass(UnsupportedFileTypeError, IngestionError)

    def test_duplicate_document_is_ingestion_error(self):
        assert issubclass(DuplicateDocumentError, IngestionError)

    def test_retrieval_error_is_airvault_error(self):
        assert issubclass(RetrievalError, AirVaultError)

    def test_collection_not_found_is_airvault_error(self):
        assert issubclass(CollectionNotFoundError, AirVaultError)

    def test_configuration_error_is_airvault_error(self):
        assert issubclass(ConfigurationError, AirVaultError)

    def test_storage_error_is_airvault_error(self):
        assert issubclass(StorageError, AirVaultError)


class TestErrorMessages:
    """Verify error messages are informative."""

    def test_unsupported_file_type_message(self):
        err = UnsupportedFileTypeError(".xyz", [".pdf", ".txt"])
        assert ".xyz" in str(err)
        assert ".pdf" in str(err)
        assert err.extension == ".xyz"
        assert err.supported == [".pdf", ".txt"]

    def test_duplicate_document_message(self):
        err = DuplicateDocumentError("abc123def456", "uuid-1234")
        assert "abc123def456" in str(err)
        assert "uuid-1234" in str(err)
        assert err.checksum == "abc123def456"
        assert err.existing_id == "uuid-1234"

    def test_duplicate_document_without_id(self):
        err = DuplicateDocumentError("abc123def456")
        assert "abc123def456" in str(err)
        assert err.existing_id is None

    def test_collection_not_found_message(self):
        err = CollectionNotFoundError("my_collection")
        assert "my_collection" in str(err)
        assert err.name == "my_collection"

    def test_catch_all_airvault_errors(self):
        """Callers can catch AirVaultError to handle all SDK errors."""
        errors = [
            IngestionError("fail"),
            ExtractionError("fail"),
            UnsupportedFileTypeError(".bad", []),
            DuplicateDocumentError("abc"),
            RetrievalError("fail"),
            CollectionNotFoundError("x"),
            ConfigurationError("fail"),
            StorageError("fail"),
        ]
        for err in errors:
            with pytest.raises(AirVaultError):
                raise err
