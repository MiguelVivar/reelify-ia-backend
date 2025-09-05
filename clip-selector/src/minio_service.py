import boto3
import os
import logging
from botocore.exceptions import ClientError
from urllib.parse import urlparse
from config import settings

logger = logging.getLogger(__name__)

class MinIOService:
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=f"{'https' if settings.minio_secure else 'http'}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name='us-east-1'
        )
        self.bucket = settings.minio_bucket
        
    async def download_file(self, url: str, local_path: str) -> bool:
        """Download file from MinIO using URL"""
        try:
            # Extract key from URL
            parsed_url = urlparse(url)
            key = parsed_url.path.lstrip('/')
            
            # Remove bucket name from key if present
            if key.startswith(f"{self.bucket}/"):
                key = key[len(f"{self.bucket}/"):]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            self.client.download_file(self.bucket, key, local_path)
            logger.info(f"Downloaded {url} to {local_path}")
            return True
            
        except ClientError as e:
            logger.error(f"Error downloading file from MinIO: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading file: {e}")
            return False
    
    async def upload_file(self, local_path: str, key: str) -> str:
        """Upload file to MinIO and return URL"""
        try:
            self.client.upload_file(local_path, self.bucket, key)
            
            # Generate URL
            url = f"{'https' if settings.minio_secure else 'http'}://{settings.minio_endpoint}/{self.bucket}/{key}"
            logger.info(f"Uploaded {local_path} to {url}")
            return url
            
        except ClientError as e:
            logger.error(f"Error uploading file to MinIO: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            raise
