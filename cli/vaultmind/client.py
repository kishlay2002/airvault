"""HTTP client for VaultMind API."""

import os
import httpx


def get_client() -> httpx.Client:
    base_url = os.environ.get("VAULTMIND_API_URL", "http://localhost:8000")
    api_key = os.environ.get("VAULTMIND_API_KEY", "")

    return httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
    )
