import os
import socket

from dotenv import load_dotenv
from minio import Minio


# Load biến môi trường từ file .env
load_dotenv(override=True)


# Đọc cấu hình MinIO từ .env
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Tự động chuyển đổi endpoint nếu chạy ở ngoài Docker container (không resolve được hostname 'minio')
if MINIO_ENDPOINT:
    try:
        host = MINIO_ENDPOINT.split(":")[0]
        socket.getaddrinfo(host, None)
    except socket.gaierror:
        if host == "minio":
            MINIO_ENDPOINT = MINIO_ENDPOINT.replace("minio", "localhost", 1)


def get_minio_client():
    # Khởi tạo kết nối tới MinIO
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def ensure_bucket_exists(client):
    # Tạo bucket nếu chưa tồn tại
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)