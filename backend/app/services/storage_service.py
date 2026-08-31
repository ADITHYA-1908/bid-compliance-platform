"""
Storage Service for Part 3D: Bid Document Upload
Provides unified storage abstraction for private procurement documents.
Supports Supabase Storage private buckets with secure fallback to local filesystem storage.
"""

import os
import re
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple
import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes user-provided filename by removing dangerous characters, path traversal tokens,
    and keeping only safe alphanumeric, dots, hyphens, and underscores.
    """
    clean = os.path.basename(filename)
    clean = re.sub(r"[^\w\.\-\_]", "_", clean)
    clean = re.sub(r"\.{2,}", ".", clean)  # prevent multiple consecutive dots
    if not clean or clean.startswith("."):
        clean = f"document_{uuid.uuid4().hex[:8]}{clean}"
    return clean[:100]  # Limit length


class StorageService:
    def __init__(self):
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self.supabase_url = settings.SUPABASE_URL.rstrip("/") if settings.SUPABASE_URL else None
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.local_dir = Path(settings.LOCAL_STORAGE_DIR)
        self.local_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.service_role_key)

    def upload_file(
        self,
        storage_path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Uploads document binary to the private storage bucket.
        Returns the persistent storage path.
        """
        # Always write to local storage as fallback / cache
        local_file_path = self.local_dir / storage_path
        local_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_file_path, "wb") as f:
            f.write(content)

        if self.is_supabase_configured:
            try:
                url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{storage_path}"
                headers = {
                    "Authorization": f"Bearer {self.service_role_key}",
                    "apikey": self.service_role_key,
                    "Content-Type": content_type,
                    "x-upsert": "true",
                }
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, headers=headers, content=content)
                    if resp.status_code not in (200, 201):
                        logger.warning(
                            "Supabase storage upload returned status %d: %s. Using local storage path.",
                            resp.status_code,
                            resp.text,
                        )
            except Exception as e:
                logger.warning("Supabase storage upload failed with error: %s. Relying on local storage.", e)

        return storage_path

    def delete_file(self, storage_path: str) -> bool:
        """Removes the file from storage if present."""
        deleted = False

        local_file_path = self.local_dir / storage_path
        if local_file_path.exists():
            try:
                local_file_path.unlink()
                deleted = True
            except Exception as e:
                logger.warning("Failed to delete local file %s: %s", storage_path, e)

        if self.is_supabase_configured:
            try:
                url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{storage_path}"
                headers = {
                    "Authorization": f"Bearer {self.service_role_key}",
                    "apikey": self.service_role_key,
                }
                with httpx.Client(timeout=15.0) as client:
                    resp = client.delete(url, headers=headers)
                    if resp.status_code == 200:
                        deleted = True
            except Exception as e:
                logger.warning("Failed to delete Supabase storage object %s: %s", storage_path, e)

        return deleted

    def create_signed_url(self, storage_path: str, expires_in_seconds: int = 300) -> Optional[str]:
        """
        Creates a time-limited signed URL for viewing / downloading private documents.
        Returns None if Supabase Storage is not configured.
        """
        if not self.is_supabase_configured:
            return None

        try:
            url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket}/{storage_path}"
            headers = {
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key,
                "Content-Type": "application/json",
            }
            payload = {"expiresIn": expires_in_seconds}
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    signed_path = data.get("signedURL")
                    if signed_path:
                        if signed_path.startswith("http"):
                            return signed_path
                        return f"{self.supabase_url}/storage/v1{signed_path}"
        except Exception as e:
            logger.warning("Failed to generate Supabase signed URL for %s: %s", storage_path, e)

        return None

    def file_exists(self, storage_path: str) -> bool:
        """Checks if file exists in local storage cache or Supabase storage bucket."""
        local_file_path = self.local_dir / storage_path
        if local_file_path.exists():
            return True

        if self.is_supabase_configured:
            try:
                url = f"{self.supabase_url}/storage/v1/object/info/authenticated/{self.bucket}/{storage_path}"
                headers = {
                    "Authorization": f"Bearer {self.service_role_key}",
                    "apikey": self.service_role_key,
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return True
            except Exception as e:
                logger.warning("Supabase storage file existence check error for %s: %s", storage_path, e)

        return False

    def get_file_bytes(self, storage_path: str) -> bytes:
        """Retrieves raw file content bytes from storage for streaming/download."""
        local_file_path = self.local_dir / storage_path
        if local_file_path.exists():
            with open(local_file_path, "rb") as f:
                return f.read()

        if self.is_supabase_configured:
            try:
                url = f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket}/{storage_path}"
                headers = {
                    "Authorization": f"Bearer {self.service_role_key}",
                    "apikey": self.service_role_key,
                }
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return resp.content
            except Exception as e:
                logger.error("Failed to read Supabase storage object %s: %s", storage_path, e)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document binary file was not found in storage.",
        )

    def download_file(self, storage_path: str) -> bytes:
        """Alias for get_file_bytes to retrieve binary document bytes for extraction pipeline."""
        return self.get_file_bytes(storage_path)


storage_service = StorageService()
