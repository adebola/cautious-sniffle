"""MinIO storage client for downloading document files."""

import logging
import os
import tempfile

from minio import Minio

logger = logging.getLogger(__name__)


class StorageClient:
    """Wraps the MinIO Python client for downloading document files to
    temporary local paths.

    Files are downloaded to a system temp directory so the parsers can
    operate on local file handles.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._bucket = bucket

    async def download_file(self, storage_path: str) -> str:
        """Download a file from MinIO to a temporary path.

        Args:
            storage_path: The object key inside the configured bucket.

        Returns:
            The absolute path to the downloaded temporary file.

        Raises:
            Exception: If the download fails.
        """
        # Determine a safe suffix from the object key
        _, ext = os.path.splitext(storage_path)
        suffix = ext if ext else ""

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="chatcraft_ingest_")
        os.close(tmp_fd)

        try:
            logger.info(
                "Downloading object %s/%s -> %s",
                self._bucket,
                storage_path,
                tmp_path,
            )
            # minio-py's fget_object is synchronous; it is CPU-light (I/O
            # bound) and acceptable to call from an async context within
            # a worker that has its own prefetch concurrency limit.
            self._client.fget_object(self._bucket, storage_path, tmp_path)
            return tmp_path
        except Exception:
            # Clean up partial file on failure
            self.cleanup_temp(tmp_path)
            logger.exception("Failed to download %s from MinIO", storage_path)
            raise

    @staticmethod
    def cleanup_temp(path: str) -> None:
        """Remove a temporary file, suppressing errors if it does not exist."""
        try:
            if path and os.path.exists(path):
                os.unlink(path)
                logger.debug("Cleaned up temp file: %s", path)
        except OSError:
            logger.warning("Could not remove temp file: %s", path, exc_info=True)
