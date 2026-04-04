import os
from minio import Minio
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)

BUCKET = os.getenv("MINIO_BUCKET")

if not client.bucket_exists(BUCKET):
    client.make_bucket(BUCKET)
    print(f"✓ Tạo bucket: {BUCKET}")
else:
    print(f"✓ Bucket đã tồn tại: {BUCKET}")