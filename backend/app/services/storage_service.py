"""Storage service abstraction with Local and S3 (MinIO compatible) implementations."""
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.config import get_settings, Settings
from app.api.errors import StorageError


class StorageService(ABC):
    @abstractmethod
    def save_file(self, data: bytes, path: str) -> str:
        """Save file bytes to destination path. Returns storage identifier / path."""
        pass

    @abstractmethod
    def get_file(self, path: str) -> bytes:
        """Retrieve file bytes by storage path."""
        pass

    @abstractmethod
    def get_download_url(self, path: str) -> str:
        """Generate download URL or path for accessing the file."""
        pass

    @abstractmethod
    def delete_file(self, path: str) -> None:
        """Delete file at storage path."""
        pass

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if file exists at storage path."""
        pass

    @abstractmethod
    def get_local_path(self, path: str) -> str:
        """Ensure file is available locally and return local filesystem absolute path."""
        pass


class LocalStorageService(StorageService):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        clean_path = path.lstrip("/\\")
        full_path = (self.base_path / clean_path).resolve()
        # Security check: ensure path does not escape base directory
        if not str(full_path).startswith(str(self.base_path)):
            raise StorageError(f"Access denied: path '{path}' escapes storage root")
        return full_path

    def save_file(self, data: bytes, path: str) -> str:
        try:
            target = self._resolve(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "wb") as f:
                f.write(data)
            return str(target)
        except Exception as e:
            raise StorageError(f"Failed to save local file '{path}': {str(e)}")

    def get_file(self, path: str) -> bytes:
        try:
            target = self._resolve(path)
            if not target.exists():
                raise StorageError(f"File not found: {path}")
            with open(target, "rb") as f:
                return f.read()
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to read file '{path}': {str(e)}")

    def get_download_url(self, path: str) -> str:
        # For local file storage, return relative download endpoint or path
        clean_path = path.replace("\\", "/").lstrip("/")
        return f"/downloads/{clean_path}"

    def delete_file(self, path: str) -> None:
        try:
            target = self._resolve(path)
            if target.exists() and target.is_file():
                target.unlink()
        except Exception as e:
            raise StorageError(f"Failed to delete file '{path}': {str(e)}")

    def file_exists(self, path: str) -> bool:
        try:
            target = self._resolve(path)
            return target.exists() and target.is_file()
        except Exception:
            return False

    def get_local_path(self, path: str) -> str:
        target = self._resolve(path)
        return str(target)


class S3StorageService(StorageService):
    def __init__(
        self,
        bucket: str,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        local_cache_dir: str = "./data/s3_cache"
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.local_cache_dir = Path(local_cache_dir).resolve()
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            import boto3
            from botocore.config import Config

            session = boto3.session.Session()
            self.s3_client = session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version="s3v4")
            )
            # Ensure bucket exists if possible
            try:
                self.s3_client.head_bucket(Bucket=self.bucket)
            except Exception:
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket)
                except Exception:
                    pass
        except ImportError:
            raise StorageError("boto3 is required for S3StorageService")
        except Exception as e:
            raise StorageError(f"Failed to initialize S3 storage client: {str(e)}")

    def save_file(self, data: bytes, path: str) -> str:
        key = path.lstrip("/\\").replace("\\", "/")
        try:
            self.s3_client.put_object(Bucket=self.bucket, Key=key, Body=data)
            return f"s3://{self.bucket}/{key}"
        except Exception as e:
            raise StorageError(f"Failed to upload to S3 ({key}): {str(e)}")

    def get_file(self, path: str) -> bytes:
        key = path.replace(f"s3://{self.bucket}/", "").lstrip("/\\")
        try:
            resp = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()
        except Exception as e:
            raise StorageError(f"Failed to download from S3 ({key}): {str(e)}")

    def get_download_url(self, path: str) -> str:
        key = path.replace(f"s3://{self.bucket}/", "").lstrip("/\\")
        try:
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=3600
            )
        except Exception as e:
            raise StorageError(f"Failed to generate presigned S3 URL: {str(e)}")

    def delete_file(self, path: str) -> None:
        key = path.replace(f"s3://{self.bucket}/", "").lstrip("/\\")
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as e:
            raise StorageError(f"Failed to delete S3 object ({key}): {str(e)}")

    def file_exists(self, path: str) -> bool:
        key = path.replace(f"s3://{self.bucket}/", "").lstrip("/\\")
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def get_local_path(self, path: str) -> str:
        key = path.replace(f"s3://{self.bucket}/", "").lstrip("/\\")
        local_target = self.local_cache_dir / key
        local_target.parent.mkdir(parents=True, exist_ok=True)
        if not local_target.exists():
            data = self.get_file(path)
            with open(local_target, "wb") as f:
                f.write(data)
        return str(local_target)


def create_storage_service(settings: Optional[Settings] = None) -> StorageService:
    cfg = settings or get_settings()
    if cfg.STORAGE_TYPE.lower() == "s3":
        return S3StorageService(
            bucket=cfg.S3_BUCKET,
            endpoint_url=cfg.S3_ENDPOINT,
            access_key=cfg.S3_ACCESS_KEY,
            secret_key=cfg.S3_SECRET_KEY,
            local_cache_dir=os.path.join(cfg.STORAGE_PATH, "cache")
        )
    return LocalStorageService(base_path=cfg.STORAGE_PATH)
