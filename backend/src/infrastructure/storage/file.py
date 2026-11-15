from pathlib import Path

import aioboto3
import aiofiles

from src.core import Settings
from src.core import settings as global_settings
from src.domain.interfaces import FileStorageProtocol


class LocalFileStorage:
    def __init__(
        self,
        local_dir: str | Path | None = None,
        base_url: str | None = None,
    ) -> None:
        cfg_dir = local_dir or global_settings.media_local_dir
        self.local_dir = Path(cfg_dir)
        self.base_url = (base_url or global_settings.media_base_url).rstrip("/")

    async def upload_file(self, *, key: str, data: bytes, content_type: str) -> str:
        clean_key = key.lstrip("/\\")
        dest = self.local_dir / clean_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            await f.write(data)
        return f"{self.base_url}/{clean_key}"

    async def delete_file(self, *, key: str) -> None:
        clean_key = key.lstrip("/\\")
        dest = self.local_dir / clean_key
        if dest.exists():
            dest.unlink()


class S3FileStorage:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or global_settings
        self._session = aioboto3.Session()

    async def upload_file(self, *, key: str, data: bytes, content_type: str) -> str:
        clean_key = key.lstrip("/\\")
        async with self._session.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key or "stub",
            aws_secret_access_key=self.settings.s3_secret_key or "stub",
            region_name=self.settings.s3_region,
        ) as s3:
            await s3.put_object(
                Bucket=self.settings.s3_bucket,
                Key=clean_key,
                Body=data,
                ContentType=content_type,
            )
        endpoint = (
            self.settings.s3_endpoint_url
            or f"https://s3.{self.settings.s3_region}.amazonaws.com"
        ).rstrip("/")
        return f"{endpoint}/{self.settings.s3_bucket}/{clean_key}"

    async def delete_file(self, *, key: str) -> None:
        clean_key = key.lstrip("/\\")
        async with self._session.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key or "stub",
            aws_secret_access_key=self.settings.s3_secret_key or "stub",
            region_name=self.settings.s3_region,
        ) as s3:
            await s3.delete_object(
                Bucket=self.settings.s3_bucket,
                Key=clean_key,
            )


def get_file_storage(settings: Settings | None = None) -> FileStorageProtocol:
    cfg = settings or global_settings
    if cfg.storage_backend == "s3":
        return S3FileStorage(settings=cfg)
    return LocalFileStorage(
        local_dir=cfg.media_local_dir,
        base_url=cfg.media_base_url,
    )
