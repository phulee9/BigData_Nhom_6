from io import BytesIO
from pathlib import Path

import pandas as pd
from minio import Minio

from src.config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET,
    MINIO_SECURE,
)


def get_minio_client() -> Minio:
    # Khởi tạo client để kết nối tới MinIO
    return Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def ensure_bucket(client: Minio, bucket_name: str = MINIO_BUCKET) -> None:
    # Kiểm tra bucket đã tồn tại chưa
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        print(f"Đã tạo bucket: {bucket_name}")
    else:
        print(f"Bucket đã tồn tại: {bucket_name}")


def create_zone(
    client: Minio,
    zone_path: str,
    bucket_name: str = MINIO_BUCKET,
) -> None:
    # MinIO không có folder thật như Windows
    # Folder trên MinIO thực chất là prefix của object
    # Tạo file rỗng .keep để vùng hiển thị rõ trên MinIO Console

    # Chuẩn hóa đường dẫn vùng và tạo object .keep
    object_name = zone_path.rstrip("/") + "/.keep"

    # Tạo dữ liệu rỗng để upload file .keep
    data = BytesIO(b"")

    # Upload object rỗng lên MinIO
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=data,
        length=0,
        content_type="application/octet-stream",
    )

    print(f"Đã tạo vùng: s3://{bucket_name}/{object_name}")


def create_zones(
    client: Minio,
    zones: list[str],
    bucket_name: str = MINIO_BUCKET,
) -> None:
    # Tạo nhiều vùng logic trên MinIO
    for zone in zones:
        create_zone(
            client=client,
            zone_path=zone,
            bucket_name=bucket_name,
        )


def upload_file(
    client: Minio,
    local_path: str,
    object_name: str,
    bucket_name: str = MINIO_BUCKET,
) -> None:
    # Chuyển đường dẫn local sang Path để kiểm tra file tồn tại
    local_file = Path(local_path)

    # Nếu file local không tồn tại thì báo lỗi rõ ràng
    if not local_file.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file local: {local_path}"
        )

    # Upload file local lên MinIO
    client.fput_object(
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=str(local_file),
    )

    print(f"Đã upload: {local_path}")
    print(f"       lên: s3://{bucket_name}/{object_name}")


def list_objects(
    client: Minio,
    prefix: str = "",
    bucket_name: str = MINIO_BUCKET,
) -> None:
    # Liệt kê các object trong bucket theo prefix
    print(f"\nDanh sách object trong s3://{bucket_name}/{prefix}")

    # Lấy danh sách object theo prefix
    objects = client.list_objects(
        bucket_name=bucket_name,
        prefix=prefix,
        recursive=True,
    )

    # In ra tên object và dung lượng
    for obj in objects:
        print(f"- {obj.object_name} | {obj.size} bytes")


def read_csv_from_minio(
    client: Minio,
    object_name: str,
    bucket_name: str = MINIO_BUCKET,
) -> pd.DataFrame:
    # Đọc file CSV từ MinIO về DataFrame
    response = client.get_object(
        bucket_name=bucket_name,
        object_name=object_name,
    )

    try:
        df = pd.read_csv(response)
    finally:
        response.close()
        response.release_conn()

    print(f"Đã đọc CSV: s3://{bucket_name}/{object_name}")
    print(f"Số dòng, số cột: {df.shape}")

    return df


def upload_df_parquet(
    client: Minio,
    df: pd.DataFrame,
    object_name: str,
    bucket_name: str = MINIO_BUCKET,
) -> None:
    # Ghi DataFrame thành Parquet rồi upload lên MinIO
    buffer = BytesIO()

    df.to_parquet(
        buffer,
        index=False,
        engine="pyarrow",
    )

    buffer.seek(0)

    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=buffer,
        length=buffer.getbuffer().nbytes,
        content_type="application/octet-stream",
    )

    print(f"Đã lưu Parquet: s3://{bucket_name}/{object_name}")
    print(f"Số dòng, số cột: {df.shape}")

def read_parquet_from_minio(
    client: Minio,
    object_name: str,
    bucket_name: str = MINIO_BUCKET,
) -> pd.DataFrame:
    # Đọc file Parquet từ MinIO về bộ nhớ dạng bytes
    response = client.get_object(
        bucket_name=bucket_name,
        object_name=object_name,
    )

    try:
        data = response.read()
    finally:
        response.close()
        response.release_conn()

    # Chuyển bytes thành BytesIO để pandas/pyarrow có thể seek
    buffer = BytesIO(data)

    # Đọc Parquet từ buffer
    df = pd.read_parquet(buffer)

    print(f"Đã đọc Parquet: s3://{bucket_name}/{object_name}")
    print(f"Số dòng, số cột: {df.shape}")

    return df

def upload_df_parquet_local_temp(
    client: Minio,
    df: pd.DataFrame,
    object_name: str,
    local_temp_path: str,
    bucket_name: str = MINIO_BUCKET,
) -> None:
    # Ghi DataFrame ra file tạm local để tránh giữ toàn bộ Parquet trong RAM
    temp_file = Path(local_temp_path)

    # Tạo folder temp nếu chưa có
    temp_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Ghi DataFrame thành Parquet ra ổ đĩa
    df.to_parquet(
        temp_file,
        index=False,
        engine="pyarrow",
    )

    # Upload file Parquet tạm lên MinIO
    client.fput_object(
        bucket_name=bucket_name,
        object_name=object_name,
        file_path=str(temp_file),
    )

    print(f"Đã lưu Parquet: s3://{bucket_name}/{object_name}")
    print(f"Số dòng, số cột: {df.shape}")
    print(f"File tạm: {temp_file}")

    # Xóa file tạm sau khi upload xong
    temp_file.unlink(missing_ok=True)