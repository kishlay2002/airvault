"""AirVault SDK — Synchronous Usage Example.

For codebases that don't use async/await.
"""

from airvault import AirVaultSync, SensitivityTier


def main():
    # No async/await needed
    engine = AirVaultSync()

    # Ingest
    result = engine.ingest_text(
        "The company's data retention policy requires all classified "
        "documents to be retained for a minimum of 7 years. Internal "
        "documents must be reviewed annually for reclassification.",
        source_name="retention_policy.txt",
        collection="policies",
        sensitivity=SensitivityTier.INTERNAL,
    )
    print(f"Ingested: {result.chunk_count} chunks")

    # Query
    results = engine.query(
        "How long should documents be retained?",
        collection="policies",
        clearance="internal",
    )
    print(f"Answer: {results.answer[:200]}")

    engine.close()


if __name__ == "__main__":
    main()
