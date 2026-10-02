"""Crea los buckets en el S3 local (moto) para desarrollo. NO se usa en AWS."""

import os

import boto3

endpoint = os.getenv("S3_ENDPOINT_URL", "http://localhost:5000")
# Usa AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY del entorno (cualquier valor sirve para moto).
s3 = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1")
for bucket in (
    os.getenv("S3_VIDEOS_BUCKET", "streamhub-videos-local"),
    os.getenv("S3_THUMBNAILS_BUCKET", "streamhub-thumbnails-local"),
):
    s3.create_bucket(Bucket=bucket)
    print(f"Bucket listo: {bucket}")
