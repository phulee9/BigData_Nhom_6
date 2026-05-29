import argparse
import os
import sys

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    ensure_bucket_exists,
    get_minio_client,
)


BRONZE_CRAWLER_RAW_TEMPLATE = "bronze/crawler/raw/{week}.json"


def upload_raw_file(client, local_file, week):
    # Upload file JSON raw lên Bronze
    object_path = BRONZE_CRAWLER_RAW_TEMPLATE.format(week=week)

    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_path,
        file_path=local_file,
    )

    print(f"Uploaded: {object_path}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--week",
        required=True,
        help="Tên tuần, ví dụ: week_2026_05_09",
    )

    parser.add_argument(
        "--local-file",
        required=True,
        help="Đường dẫn file JSON raw local",
    )

    args = parser.parse_args()

    if not os.path.exists(args.local_file):
        raise FileNotFoundError(f"Raw file not found: {args.local_file}")

    client = get_minio_client()
    ensure_bucket_exists(client)

    upload_raw_file(
        client=client,
        local_file=args.local_file,
        week=args.week,
    )

    print("Done.")


if __name__ == "__main__":
    main()