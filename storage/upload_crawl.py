import os
from datetime import datetime
from pathlib import Path
from minio import Minio
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
BUCKET = os.getenv("MINIO_BUCKET")
TODAY  = datetime.now().strftime("%Y-%m-%d")

# Thư mục data crawl local
DATA_DIR = Path(__file__).parent.parent / "data"


def is_uploaded(source: str, filename: str) -> bool:
    # Kiểm tra file đã upload lên MinIO chưa
    path = f"bronze/crawled/{source}/{filename}"
    try:
        client.stat_object(BUCKET, path)
        return True
    except Exception:
        return False


def upload_file(local_path: Path, source: str):
    # Upload 1 file crawl lên Bronze theo nguồn
    filename = local_path.name

    if is_uploaded(source, filename):
        print(f"Da upload: {source}/{filename}, bo qua")
        return

    path = f"bronze/crawled/{source}/{filename}"
    client.fput_object(BUCKET, path, str(local_path))
    print(f"Da upload: {path}")


def upload_source(source: str):
    # Upload tất cả file chưa upload của 1 nguồn
    source_dir = DATA_DIR / source
    if not source_dir.exists():
        print(f"Khong co thu muc: {source_dir}")
        return

    files = list(source_dir.glob("*.csv")) + \
            list(source_dir.glob("*.json"))

    if not files:
        print(f"Khong co file moi: {source}")
        return

    print(f"Tim thay {len(files)} file tu {source}...")
    for f in sorted(files):
        upload_file(f, source)


if __name__ == "__main__":
    # Upload từng nguồn crawl
    sources = ["indeed", "monster", "linkedin"]
    for source in sources:
        upload_source(source)

    print("Upload xong!")