import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from minio.error import S3Error

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    MINIO_BUCKET,
    silver_crawler_basic_clean,
    silver_crawler_preclassified,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
    upload_df_parquet,
    list_objects,
)


def object_exists(client, object_name: str) -> bool:
    # Kiểm tra object đã tồn tại trên MinIO chưa
    try:
        client.stat_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
        )

        return True

    except S3Error as error:
        if error.code == "NoSuchKey":
            return False

        raise error


def list_basic_clean_batches(client) -> list[str]:
    # Lấy danh sách batch đã có Silver 02 Basic Clean
    objects = client.list_objects(
        bucket_name=MINIO_BUCKET,
        prefix="silver/crawler/",
        recursive=True,
    )

    batch_names = set()

    for obj in objects:
        object_name = obj.object_name

        if not object_name.endswith("/02_basic_clean/jobs_basic_clean.parquet"):
            continue

        # silver/crawler/week_2026_05_09/02_basic_clean/jobs_basic_clean.parquet
        parts = object_name.split("/")

        if len(parts) >= 3:
            batch_names.add(parts[2])

    return sorted(batch_names)


def find_unprocessed_batch(client) -> str | None:
    # Tìm batch đã basic clean nhưng chưa preclassified
    batch_names = list_basic_clean_batches(client)

    if not batch_names:
        print("Không tìm thấy batch nào đã basic clean.")
        return None

    for batch_name in batch_names:
        preclassified_object = silver_crawler_preclassified(batch_name)

        if object_exists(client, preclassified_object):
            print(f"Bỏ qua batch đã preclassified: {batch_name}")
            continue

        return batch_name

    return None


def skills_to_text(skills) -> str:
    # Chuyển skills_basic_clean thành text để phục vụ phân loại ngành

    # Trường hợp rỗng
    if skills is None:
        return ""

    # Trường hợp NaN dạng float
    if isinstance(skills, float) and pd.isna(skills):
        return ""

    # Trường hợp list Python
    if isinstance(skills, list):
        return " ".join(
            str(skill).lower()
            for skill in skills
            if str(skill).strip()
        )

    # Trường hợp numpy array khi đọc từ Parquet
    if isinstance(skills, np.ndarray):
        return " ".join(
            str(skill).lower()
            for skill in skills.tolist()
            if str(skill).strip()
        )

    # Trường hợp tuple hoặc set
    if isinstance(skills, (tuple, set)):
        return " ".join(
            str(skill).lower()
            for skill in list(skills)
            if str(skill).strip()
        )

    # Trường hợp string hoặc kiểu khác
    return str(skills).lower()


def build_classification_text(row: pd.Series) -> str:
    # Ghép title + skills + company để phân loại sơ bộ
    title = str(row.get("job_title_basic_clean", "") or "").lower()
    skills = skills_to_text(row.get("skills_basic_clean", []))
    company = str(row.get("company_clean", "") or "").lower()

    return f"{title} {skills} {company}"


def classify_occupation_group(row: pd.Series) -> str:
    # Phân loại sơ bộ ngành nghề giống logic Kaggle
    text = build_classification_text(row)

    # Data & Analytics
    if re.search(
        r"\b(data analyst|data analytics|analytics|business intelligence|"
        r"bi analyst|power bi|tableau|looker|data scientist|machine learning|"
        r"deep learning|data engineer|analytics engineer|bigquery|databricks|"
        r"data modeling|data analysis|reporting|data visualization)\b",
        text,
    ):
        return "Data & Analytics"

    # IT / Software
    if re.search(
        r"\b(software engineer|software developer|backend|frontend|fullstack|"
        r"full stack|developer|devops|java|python|javascript|typescript|"
        r"node\.?js|react|vue|angular|\.net|c\+\+|golang|kubernetes|docker|"
        r"api|apis|microservices|cloud|aws|azure|qa engineer|test automation|"
        r"solution designer|solution architect|product owner|security engineer|"
        r"soc|cyber security|information security|ai engineer|nlp|llm|rag|"
        r"langchain|langgraph|generative ai)\b",
        text,
    ):
        return "IT / Software"

    # Finance & Accounting
    if re.search(
        r"\b(finance|financial|accountant|accounting|audit|auditor|"
        r"chief accountant|cfo|ifrs|gaap|tax|payroll|investment analyst|"
        r"banking|credit card|wealth banking|budgeting|financial management|"
        r"cash flow|bancassurance)\b",
        text,
    ):
        return "Finance & Accounting"

    # Sales
    if re.search(
        r"\b(sales|account executive|account manager|business development|"
        r"key account|inside sales|country sales|sales manager|sales executive|"
        r"relationship manager|seller management|client engagement|crm|"
        r"salesforce|negotiation|b2b sales)\b",
        text,
    ):
        return "Sales"

    # Marketing / Communications
    if re.search(
        r"\b(marketing|digital marketing|social media|content|seo|sem|"
        r"google analytics|facebook ads|brand|communication|communications|"
        r"user acquisition|growth|performance marketing|media relations|"
        r"influencer|ad tech|campaign|meta ads)\b",
        text,
    ):
        return "Marketing / Communications"

    # Human Resources
    if re.search(
        r"\b(hr|human resources|talent acquisition|recruitment|recruiter|"
        r"learning partner|payroll service|hrbp|employee relations|"
        r"organization development|learning development|hr operations|"
        r"workforce planning|benefits|employee engagement)\b",
        text,
    ):
        return "Human Resources"

    # Healthcare
    if re.search(
        r"\b(nurse|registered nurse|medical|clinical|healthcare|pharma|"
        r"pharmaceutical|lab|regulatory affairs|quality assurance in pharma|"
        r"patient|therapy|hospital)\b",
        text,
    ):
        return "Healthcare"

    # Education / Training
    if re.search(
        r"\b(teacher|trainer|training|education|instructor|learning|"
        r"teaching|professor|tutor|instructional design|curriculum)\b",
        text,
    ):
        return "Education / Training"

    # Logistics / Supply Chain
    if re.search(
        r"\b(logistics|supply chain|warehouse|transportation|procurement|"
        r"purchasing|inventory|shipping|linehaul|spx|scommerce|material coordinator|"
        r"import export|customs|vendor selection|mro sourcing)\b",
        text,
    ):
        return "Logistics / Supply Chain"

    # Customer Service
    if re.search(
        r"\b(customer service|customer support|customer success|client support|"
        r"field service|service engineer|support engineer|customer onboarding|"
        r"customer retention)\b",
        text,
    ):
        return "Customer Service"

    # Engineering
    if re.search(
        r"\b(engineer|mechanical|electrical|civil|hardware|cad|drafter|"
        r"quality engineer|process engineer|manufacturing engineer|"
        r"functional safety|fusa|test engineer|low voltage|interior module|"
        r"pcb|schematic|simulation|autocad|catia|tensorRT|cuda)\b",
        text,
    ):
        return "Engineering"

    # Legal
    if re.search(
        r"\b(legal|law|lawyer|attorney|compliance|ip associate|"
        r"regulatory compliance|trade compliance|contractual|counsel|"
        r"data protection|governance|grc|risk management|audit compliance)\b",
        text,
    ):
        return "Legal"

    # Retail / Hospitality
    if re.search(
        r"\b(retail|hospitality|hotel|resort|housekeeping|restaurant|"
        r"cashier|front office|guest relations|rooms|concierge|cage cashier|"
        r"barista|store manager|store associate)\b",
        text,
    ):
        return "Retail / Hospitality"

    # Manufacturing / Production
    if re.search(
        r"\b(production|manufacturing|factory|smt|equipment maintenance|"
        r"machine|quality control|qc staff|pqa|gmp|visual inspection|"
        r"equipment installation|calibration|process control)\b",
        text,
    ):
        return "Manufacturing / Production"

    return "Other / Unknown"


def build_preclassified_df(df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bản copy để không làm thay đổi DataFrame gốc
    result_df = df.copy()

    # Tạo cột phân loại ngành sơ bộ
    result_df["occupation_group_preliminary"] = result_df.apply(
        classify_occupation_group,
        axis=1,
    )

    return result_df


def main() -> None:
    print("Bắt đầu build Silver 03 Preclassified cho Crawler")

    # Kết nối MinIO
    client = get_minio_client()

    # Tìm batch chưa preclassified
    print("\nBước 1: Tìm batch crawler chưa preclassified")
    batch_name = find_unprocessed_batch(client)

    if batch_name is None:
        print("\nKhông có batch crawler mới cần preclassified.")
        print("Dừng bước 04.")
        return

    basic_clean_object = silver_crawler_basic_clean(batch_name)
    preclassified_object = silver_crawler_preclassified(batch_name)

    print(f"Batch cần xử lý: {batch_name}")
    print(f"Input Silver 02: s3://{MINIO_BUCKET}/{basic_clean_object}")
    print(f"Output Silver 03: s3://{MINIO_BUCKET}/{preclassified_object}")

    # Đọc Silver 02 Basic Clean
    print("\nBước 2: Đọc dữ liệu Silver 02 Basic Clean")
    basic_clean_df = read_parquet_from_minio(
        client=client,
        object_name=basic_clean_object,
    )

    # Chia ngành sơ bộ
    print("\nBước 3: Chia ngành sơ bộ")
    preclassified_df = build_preclassified_df(basic_clean_df)

    # Kiểm tra kết quả
    print("\nThống kê occupation_group_preliminary:")
    print(
        preclassified_df["occupation_group_preliminary"]
        .value_counts()
    )

    print("\nSample Preclassified:")
    print(
        preclassified_df[
            [
                "job_title_basic_clean",
                "skills_basic_clean",
                "occupation_group_preliminary",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print(f"\nSố dòng, số cột: {preclassified_df.shape}")

    # Lưu Silver 03 Preclassified
    print("\nBước 4: Lưu Silver 03 Preclassified lên MinIO")
    upload_df_parquet(
        client=client,
        df=preclassified_df,
        object_name=preclassified_object,
    )

    # Kiểm tra vùng Silver Crawler Preclassified
    print("\nBước 5: Kiểm tra vùng Silver Crawler Preclassified")
    list_objects(
        client=client,
        prefix=f"silver/crawler/{batch_name}/03_preclassified/",
    )

    print("\nHoàn thành build Silver 03 Preclassified cho Crawler.")


if __name__ == "__main__":
    main()