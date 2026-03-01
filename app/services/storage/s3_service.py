"""
AWS S3 File Storage Service

Handles PDF report uploads, downloads, and presigned URL generation.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
import os
import io

logger = logging.getLogger(__name__)


class S3Service:
    """
    Service for managing file storage in AWS S3.
    
    Features:
    - Upload PDF reports
    - Generate presigned URLs (7-day expiration)
    - Automatic file cleanup (30 days)
    - Encryption at rest (S3 SSE)
    """
    
    def __init__(self):
        """Initialize S3 service with AWS credentials."""
        self.aws_access_key_id = os.getenv("SETTLE_AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("SETTLE_AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("SETTLE_AWS_REGION", "us-west-2")
        self.bucket_name = os.getenv("SETTLE_S3_BUCKET", "truevow-settle-reports")
        self.cloudfront_domain = os.getenv("SETTLE_CLOUDFRONT_DOMAIN")
        
        self.enabled = bool(self.aws_access_key_id and self.aws_secret_access_key)
        
        if not self.enabled:
            logger.warning("AWS S3 credentials not configured. File storage will be mocked.")
        else:
            self._initialize_s3_client()
    
    def _initialize_s3_client(self):
        """Initialize boto3 S3 client."""
        try:
            import boto3
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
            logger.info(f"S3 client initialized: bucket={self.bucket_name}, region={self.aws_region}")
        except ImportError:
            logger.error("boto3 not installed. S3 functionality disabled.")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}", exc_info=True)
            self.enabled = False
    
    async def upload_report(
        self,
        report_id: str,
        pdf_bytes: bytes,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload PDF report to S3.
        
        Args:
            report_id: UUID of the report
            pdf_bytes: PDF file content
            metadata: Optional metadata dictionary
            
        Returns:
            S3 object key (path)
        """
        if not self.enabled:
            logger.info(f"[MOCK] Upload report {report_id}: {len(pdf_bytes)} bytes")
            return f"mock://reports/2025/12/{report_id}.pdf"
        
        try:
            # Generate S3 key with date-based folder structure
            now = datetime.utcnow()
            s3_key = f"reports/{now.year}/{now.month:02d}/{report_id}.pdf"
            
            # Prepare metadata
            s3_metadata = metadata or {}
            s3_metadata.update({
                'report-id': report_id,
                'upload-date': now.isoformat(),
                'content-type': 'application/pdf'
            })
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType='application/pdf',
                Metadata=s3_metadata,
                ServerSideEncryption='AES256',  # Encryption at rest
                StorageClass='STANDARD_IA'  # Infrequent Access (cheaper)
            )
            
            logger.info(f"Report uploaded to S3: {s3_key} ({len(pdf_bytes)} bytes)")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to upload report to S3: {str(e)}", exc_info=True)
            return f"error://{report_id}"
    
    async def generate_presigned_url(
        self,
        s3_key: str,
        expiration_days: int = 7
    ) -> str:
        """
        Generate presigned URL for downloading a report.
        
        Args:
            s3_key: S3 object key
            expiration_days: Days until URL expires
            
        Returns:
            Presigned URL
        """
        if not self.enabled:
            logger.info(f"[MOCK] Generate presigned URL for {s3_key}")
            return f"https://mock-download.truevow.law/{s3_key}?expires={expiration_days}d"
        
        try:
            expiration_seconds = expiration_days * 24 * 60 * 60
            
            # If CloudFront is configured, use it
            if self.cloudfront_domain:
                # TODO: Implement CloudFront signed URLs
                logger.info("CloudFront presigned URLs not yet implemented, using S3")
            
            # Generate S3 presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration_seconds
            )
            
            logger.info(f"Generated presigned URL for {s3_key} (expires in {expiration_days} days)")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}", exc_info=True)
            return ""
    
    async def delete_report(self, s3_key: str) -> bool:
        """
        Delete a report from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if deleted successfully
        """
        if not self.enabled:
            logger.info(f"[MOCK] Delete report {s3_key}")
            return True
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Report deleted from S3: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete report from S3: {str(e)}", exc_info=True)
            return False
    
    async def list_expired_reports(self, days_old: int = 30) -> list:
        """
        List reports older than specified days for cleanup.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            List of S3 keys to delete
        """
        if not self.enabled:
            logger.info(f"[MOCK] List expired reports older than {days_old} days")
            return []
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            expired_keys = []
            
            # List objects in bucket
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix='reports/'
            )
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                            expired_keys.append(obj['Key'])
            
            logger.info(f"Found {len(expired_keys)} expired reports")
            return expired_keys
            
        except Exception as e:
            logger.error(f"Failed to list expired reports: {str(e)}", exc_info=True)
            return []
    
    async def cleanup_expired_reports(self, days_old: int = 30) -> int:
        """
        Delete reports older than specified days.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of reports deleted
        """
        if not self.enabled:
            logger.info(f"[MOCK] Cleanup expired reports older than {days_old} days")
            return 0
        
        try:
            expired_keys = await self.list_expired_reports(days_old)
            
            if not expired_keys:
                logger.info("No expired reports to clean up")
                return 0
            
            # Delete in batches of 1000 (S3 limit)
            deleted_count = 0
            batch_size = 1000
            
            for i in range(0, len(expired_keys), batch_size):
                batch = expired_keys[i:i + batch_size]
                delete_dict = {'Objects': [{'Key': key} for key in batch]}
                
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete=delete_dict
                )
                
                deleted_count += len(response.get('Deleted', []))
            
            logger.info(f"Cleaned up {deleted_count} expired reports")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired reports: {str(e)}", exc_info=True)
            return 0
    
    async def get_storage_stats(self) -> dict:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        if not self.enabled:
            return {
                "enabled": False,
                "bucket": self.bucket_name,
                "total_reports": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0
            }
        
        try:
            total_size = 0
            total_count = 0
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix='reports/'
            )
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        total_count += 1
            
            return {
                "enabled": True,
                "bucket": self.bucket_name,
                "region": self.aws_region,
                "total_reports": total_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {str(e)}", exc_info=True)
            return {
                "enabled": True,
                "error": str(e)
            }


# Global S3 service instance
s3_service = S3Service()


