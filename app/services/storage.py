from dataclasses import dataclass
from pathlib import Path

import boto3

from app.core.config import get_settings


@dataclass(slots=True)
class StoredAsset:
    bucket: str
    key: str
    size: int


class AssetStore:
    def __init__(self) -> None:
        self.settings = get_settings()

    def store_bytes(self, creation_id: str, filename: str, data: bytes) -> StoredAsset:
        if self.settings.asset_storage_mode == "s3":
            bucket = self.settings.asset_bucket_name
            key = f"creations/{creation_id}/{filename}"
            client = boto3.client("s3", region_name=self.settings.aws_region)
            client.put_object(Bucket=bucket, Key=key, Body=data)
            return StoredAsset(bucket=bucket, key=key, size=len(data))

        root = Path(self.settings.local_asset_root)
        target = root / "creations" / creation_id
        target.mkdir(parents=True, exist_ok=True)
        path = target / filename
        path.write_bytes(data)
        return StoredAsset(bucket="local", key=str(path), size=len(data))

    def delete(self, bucket: str, key: str) -> None:
        if bucket == "local":
            path = Path(key)
            if path.exists():
                path.unlink()
            return

        client = boto3.client("s3", region_name=self.settings.aws_region)
        client.delete_object(Bucket=bucket, Key=key)
