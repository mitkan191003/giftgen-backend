from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import boto3


@lru_cache(maxsize=16)
def get_secret_payload(secret_id: str, region_name: str) -> dict[str, Any]:
    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_id)
    secret_string = response.get("SecretString")
    if not isinstance(secret_string, str) or not secret_string.strip():
        raise RuntimeError(f"Secrets Manager secret {secret_id} did not contain a SecretString payload")

    payload = json.loads(secret_string)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Secrets Manager secret {secret_id} did not contain a JSON object payload")
    return payload
