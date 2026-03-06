import uuid

from app.utils.errors import AWSServiceError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """Handles S3 file storage operations."""

    def __init__(self, s3_client, bucket_name: str):
        self.s3 = s3_client
        self.bucket_name = bucket_name

    def store_file(self, data: bytes, prefix: str, filename: str, content_type: str) -> str:
        """Store file in S3 with prefix-based key. Returns the S3 key."""
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        unique_id = str(uuid.uuid4())
        key = f"{prefix}{unique_id}.{ext}"
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except Exception as e:
            logger.error(f"S3 store_file failed: {e}")
            raise AWSServiceError("S3", "put_object", str(e))
        logger.info(f"Stored file: {key}")
        return key

    def get_file(self, key: str) -> bytes:
        """Retrieve file from S3."""
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"S3 get_file failed: {e}")
            raise AWSServiceError("S3", "get_object", str(e))

    def generate_presigned_url(self, key: str, expiry: int = 3600) -> str:
        """Generate a presigned download URL."""
        try:
            url = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiry,
            )
            return url
        except Exception as e:
            logger.error(f"S3 generate_presigned_url failed: {e}")
            raise AWSServiceError("S3", "generate_presigned_url", str(e))

    def delete_file(self, key: str) -> None:
        """Delete file from S3."""
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=key)
        except Exception as e:
            logger.error(f"S3 delete_file failed: {e}")
            raise AWSServiceError("S3", "delete_object", str(e))
