import os
import sys

import pandas as pd

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    ensure_bucket_exists,
    get_minio_client,
)
from src.processing.silver_builder import build_silver_dataframe


BRONZE_JOB_POSTINGS_PATH = "bronze/kaggle/linkedin_job_postings.csv"
BRONZE_JOB_SKILLS_PATH = "bronze/kaggle/job_skills.csv"

SILVER_OUTPUT_PATH = "silver/kaggle/jobs_silver.parquet"

LOCAL_TEMP_DIR = "data/temp"
LOCAL_JOB_POSTINGS_PATH = f"{LOCAL_TEMP_DIR}/linkedin_job_postings.csv"
LOCAL_JOB_SKILLS_PATH = f"{LOCAL_TEMP_DIR}/job_skills.csv"
LOCAL_SILVER_OUTPUT_PATH = f"{LOCAL_TEMP_DIR}/jobs_silver.parquet"


def download_file_robust(client, bucket_name, object_name, file_path):
    print(f"📥 Đang tải {object_name} -> {file_path} (Stream 1MB)...")
    response = None
    try:
        response = client.get_object(bucket_name, object_name)
        with open(file_path, "wb") as file_data:
            # Tải theo khối 1MB để đạt hiệu năng ghi đĩa và truyền tải tối đa
            for chunk in response.stream(1024 * 1024):
                file_data.write(chunk)
        print(f"✅ Đã tải xong: {object_name}")
    except PermissionError:
        print(f"\n❌ LỖI KHÓA FILE (WinError 32): Không thể ghi vào file '{file_path}'.")
        print("👉 Vui lòng đóng tất cả Jupyter Notebooks, Excel hoặc các tiến trình Python khác đang mở file này và thử lại.\n")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"❌ Lỗi khi tải {object_name}: {e}")
        print("\n🔍 Chi tiết lỗi (Traceback):")
        traceback.print_exc()
        sys.exit(1)
    finally:
        if response:
            response.close()
            response.release_conn()


def download_raw_files(client):
    # Tải dữ liệu raw từ Bronze
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

    # Dọn dẹp các file cũ trước khi ghi
    for path in [LOCAL_JOB_POSTINGS_PATH, LOCAL_JOB_SKILLS_PATH]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                print(f"\n❌ LỖI KHÓA FILE (WinError 32): File '{path}' đang bị khóa bởi tiến trình khác.")
                print("👉 Vui lòng tắt Jupyter Notebook, đóng Excel/VS Code và thử lại.\n")
                sys.exit(1)

    download_file_robust(client, MINIO_BUCKET, BRONZE_JOB_POSTINGS_PATH, LOCAL_JOB_POSTINGS_PATH)
    download_file_robust(client, MINIO_BUCKET, BRONZE_JOB_SKILLS_PATH, LOCAL_JOB_SKILLS_PATH)


def read_raw_files():
    # Đọc dữ liệu raw
    job_postings = pd.read_csv(
        LOCAL_JOB_POSTINGS_PATH,
        low_memory=False,
    )

    job_skills = pd.read_csv(
        LOCAL_JOB_SKILLS_PATH,
        low_memory=False,
    )

    return job_postings, job_skills


def save_silver_file(jobs_silver):
    # Lưu Silver ra local
    jobs_silver.to_parquet(
        LOCAL_SILVER_OUTPUT_PATH,
        index=False,
    )


def upload_silver_file(client):
    # Upload Silver lên MinIO
    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=SILVER_OUTPUT_PATH,
        file_path=LOCAL_SILVER_OUTPUT_PATH,
    )


def main():
    client = get_minio_client()
    ensure_bucket_exists(client)

    print("Downloading raw files...")
    download_raw_files(client)

    print("Reading raw files...")
    job_postings, job_skills = read_raw_files()

    print(f"Job postings raw rows: {len(job_postings):,}")
    print(f"Job skills raw rows: {len(job_skills):,}")

    print("Building Silver dataframe...")
    jobs_silver = build_silver_dataframe(
        job_postings=job_postings,
        job_skills=job_skills,
    )

    print(f"Silver rows: {len(jobs_silver):,}")

    print("Saving Silver file...")
    save_silver_file(jobs_silver)

    print("Uploading Silver file...")
    upload_silver_file(client)

    print(f"Uploaded: {SILVER_OUTPUT_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()