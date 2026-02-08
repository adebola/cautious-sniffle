"""MinIO / S3-compatible object storage service."""

import asyncio
import io
import logging
import uuid

from minio import Minio
from minio.error import S3Error

from app.config import Settings

logger = logging.getLogger(__name__)


class StorageService:
    """Wraps the synchronous Minio client with async-friendly helpers."""

    def __init__(self, settings: Settings) -> None:
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket

    async def ensure_bucket(self) -> None:
        """Create the bucket if it does not already exist."""
        exists = await asyncio.to_thread(self._client.bucket_exists, self._bucket)
        if not exists:
            await asyncio.to_thread(self._client.make_bucket, self._bucket)
            logger.info("Created MinIO bucket: %s", self._bucket)

    async def upload_file(
        self,
        organization_id: str,
        file_name: str,
        file_data: bytes,
        content_type: str,
    ) -> str:
        """Upload a file to MinIO.

        The object is stored under ``{org_id}/{uuid}/{file_name}`` to
        guarantee uniqueness even when filenames collide.

        Returns:
            The storage path (object name) within the bucket.
        """
        unique_id = uuid.uuid4().hex
        storage_path = f"{organization_id}/{unique_id}/{file_name}"

        data_stream = io.BytesIO(file_data)
        data_length = len(file_data)

        await asyncio.to_thread(
            self._client.put_object,
            self._bucket,
            storage_path,
            data_stream,
            data_length,
            content_type=content_type,
        )
        logger.info("Uploaded %s (%d bytes)", storage_path, data_length)
        return storage_path

    async def get_presigned_url(
        self,
        storage_path: str,
        expires: int = 3600,
    ) -> str:
        """Generate a presigned GET URL valid for ``expires`` seconds."""
        from datetime import timedelta

        url: str = await asyncio.to_thread(
            self._client.presigned_get_object,
            self._bucket,
            storage_path,
            expires=timedelta(seconds=expires),
        )
        return url

    async def delete_file(self, storage_path: str) -> bool:
        """Remove a file from MinIO. Returns True on success."""
        try:
            await asyncio.to_thread(
                self._client.remove_object,
                self._bucket,
                storage_path,
            )
            logger.info("Deleted object: %s", storage_path)
            return True
        except S3Error:
            logger.exception("Failed to delete object: %s", storage_path)
            return False
