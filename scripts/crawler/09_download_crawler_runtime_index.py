import sys
from pathlib import Path

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    MINIO_BUCKET,
    GOLD_CRAWLER_METADATA,
    GOLD_CRAWLER_TITLE_INDEX,
    GOLD_CRAWLER_SKILLS_INDEX,
    GOLD_CRAWLER_FULL_INDEX,
)
from src.storage.minio_client import get_minio_client


LOCAL_RUNTIME_DIR = Path("data/runtime_index/crawler")

FILES_TO_DOWNLOAD = [
    {
        "object_name": GOLD_CRAWLER_METADATA,
        "local_path": LOCAL_RUNTIME_DIR / "metadata.parquet",
    },
    {
        "object_name": GOLD_CRAWLER_TITLE_INDEX,
        "local_path": LOCAL_RUNTIME_DIR / "title.faiss.index",
    },
    {
        "object_name": GOLD_CRAWLER_SKILLS_INDEX,
        "local_path": LOCAL_RUNTIME_DIR / "skills.faiss.index",
    },
    {
        "object_name": GOLD_CRAWLER_FULL_INDEX,
        "local_path": LOCAL_RUNTIME_DIR / "full.faiss.index",
    },
]


def download_file(client, object_name: str, local_path: Path) -> None:
    # Tạo thư mục local nếu chưa có
    local_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Xóa file cũ nếu đã tồn tại để đảm bảo tải bản mới nhất
    if local_path.exists():
        local_path.unlink()
        print(f"Đã xóa file local cũ: {local_path}")

    # Tải file từ MinIO về local
    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        file_path=str(local_path),
    )

    print(f"Đã tải: s3://{MINIO_BUCKET}/{object_name}")
    print(f"   về: {local_path}")


def main() -> None:
    print("Bắt đầu tải crawler runtime index từ MinIO về local")

    # Kết nối MinIO
    client = get_minio_client()

    # Tải từng file cần cho recommendation
    for item in FILES_TO_DOWNLOAD:
        download_file(
            client=client,
            object_name=item["object_name"],
            local_path=item["local_path"],
        )

    print("\nHoàn thành tải crawler runtime index.")
    print(f"Thư mục local: {LOCAL_RUNTIME_DIR}")


if __name__ == "__main__":
    main()