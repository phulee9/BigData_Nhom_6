import sys
from pathlib import Path

import pandas as pd

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    SILVER_KAGGLE_BASIC_CLEAN,
    SILVER_KAGGLE_PRECLASSIFIED,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
    upload_df_parquet,
    list_objects,
)


# Bộ keyword nhận diện nhóm nghề theo job title
TITLE_KEYWORDS = {
    "Data & Analytics": [
        "data analyst",
        "business intelligence",
        "bi analyst",
        "reporting analyst",
        "data scientist",
        "analytics engineer",
        "data engineer",
    ],
    "IT / Software": [
        "software engineer",
        "software developer",
        "developer",
        "backend",
        "front end",
        "frontend",
        "full stack",
        "devops",
        "programmer",
        "systems administrator",
    ],
    "Finance & Accounting": [
        "accountant",
        "financial analyst",
        "finance analyst",
        "auditor",
        "bookkeeper",
        "controller",
        "payroll",
        "tax specialist",
    ],
    "Sales": [
        "sales representative",
        "sales executive",
        "account executive",
        "sales consultant",
        "business development",
        "sales manager",
    ],
    "Marketing / Communications": [
        "marketing specialist",
        "marketing manager",
        "seo",
        "content manager",
        "social media",
        "brand manager",
        "communications",
    ],
    "Human Resources": [
        "human resources",
        "hr specialist",
        "hr manager",
        "recruiter",
        "talent acquisition",
        "people operations",
    ],
    "Healthcare": [
        "registered nurse",
        "nurse",
        "medical assistant",
        "physician",
        "pharmacist",
        "therapist",
        "clinical",
        "healthcare",
    ],
    "Education / Training": [
        "teacher",
        "instructor",
        "professor",
        "tutor",
        "teaching assistant",
        "trainer",
    ],
    "Logistics / Supply Chain": [
        "warehouse",
        "logistics",
        "supply chain",
        "inventory",
        "procurement",
        "buyer",
        "shipping",
    ],
    "Customer Service": [
        "customer service",
        "customer support",
        "call center",
        "client support",
        "guest service",
    ],
    "Engineering": [
        "mechanical engineer",
        "electrical engineer",
        "civil engineer",
        "manufacturing engineer",
        "process engineer",
        "quality engineer",
    ],
    "Legal": [
        "legal assistant",
        "paralegal",
        "attorney",
        "lawyer",
        "legal counsel",
        "compliance officer",
    ],
    "Retail / Hospitality": [
        "cashier",
        "store associate",
        "retail associate",
        "restaurant",
        "server",
        "barista",
        "hotel",
        "hospitality",
    ],
    "Manufacturing / Production": [
        "production worker",
        "machine operator",
        "assembler",
        "manufacturing",
        "production supervisor",
    ],
}


# Bộ keyword nhận diện nhóm nghề theo skills
SKILL_KEYWORDS = {
    "Data & Analytics": [
        "sql",
        "power bi",
        "tableau",
        "python",
        "dashboard",
        "data visualization",
        "statistics",
        "data modeling",
        "excel",
    ],
    "IT / Software": [
        "javascript",
        "java",
        "react",
        "node.js",
        "c++",
        "c#",
        ".net",
        "docker",
        "kubernetes",
        "api",
        "git",
    ],
    "Finance & Accounting": [
        "gaap",
        "ifrs",
        "financial reporting",
        "budgeting",
        "forecasting",
        "accounts payable",
        "accounts receivable",
        "tax",
        "audit",
    ],
    "Sales": [
        "crm",
        "salesforce",
        "lead generation",
        "cold calling",
        "negotiation",
        "account management",
        "b2b",
        "b2c",
    ],
    "Marketing / Communications": [
        "seo",
        "sem",
        "google analytics",
        "content marketing",
        "social media",
        "campaign management",
        "email marketing",
    ],
    "Human Resources": [
        "recruitment",
        "talent acquisition",
        "payroll",
        "hris",
        "employee relations",
        "onboarding",
    ],
    "Healthcare": [
        "patient care",
        "cpr",
        "bls",
        "emr",
        "hipaa",
        "medication administration",
        "clinical care",
    ],
    "Education / Training": [
        "lesson planning",
        "curriculum",
        "teaching",
        "classroom management",
        "training",
        "instruction",
    ],
    "Logistics / Supply Chain": [
        "inventory management",
        "warehouse management",
        "wms",
        "shipping",
        "procurement",
        "forklift",
        "supply chain",
    ],
    "Customer Service": [
        "customer service",
        "customer support",
        "call center",
        "client relations",
        "problem solving",
    ],
    "Engineering": [
        "autocad",
        "solidworks",
        "engineering",
        "quality control",
        "manufacturing process",
        "cad",
    ],
    "Legal": [
        "legal research",
        "contract management",
        "compliance",
        "litigation",
        "paralegal",
    ],
    "Retail / Hospitality": [
        "cash handling",
        "pos",
        "merchandising",
        "food safety",
        "guest service",
        "hospitality",
    ],
    "Manufacturing / Production": [
        "machine operation",
        "assembly",
        "production",
        "quality inspection",
        "lean manufacturing",
        "osha",
    ],
}


GENERIC_TITLES = [
    "analyst",
    "manager",
    "specialist",
    "associate",
    "consultant",
    "coordinator",
    "assistant",
    "technician",
]


def to_skill_list(value) -> list[str]:
    # Chuẩn hóa skills_basic_clean về dạng list
    if isinstance(value, list):
        return value

    if value is None:
        return []

    if isinstance(value, str):
        return [value]

    try:
        return list(value)
    except TypeError:
        return []


def calculate_title_score(title: str, group: str) -> float:
    # Tính điểm nhóm nghề dựa trên title
    title = title or ""

    keywords = TITLE_KEYWORDS.get(group, [])

    for keyword in keywords:
        if keyword in title:
            return 1.0

    return 0.0


def calculate_skill_score(skills: list[str], group: str) -> float:
    # Tính điểm nhóm nghề dựa trên skills
    keywords = SKILL_KEYWORDS.get(group, [])

    if not skills or not keywords:
        return 0.0

    skills_text = " ".join(skills)
    match_count = 0

    for keyword in keywords:
        if keyword in skills_text:
            match_count += 1

    return min(match_count / 3, 1.0)


def is_generic_title(title: str) -> bool:
    # Kiểm tra title có quá chung chung không
    title = title or ""

    return title.strip() in GENERIC_TITLES


def classify_occupation(row: pd.Series) -> pd.Series:
    # Lấy title và skills đã clean nhẹ
    title = row.get("job_title_basic_clean", "")
    skills = to_skill_list(row.get("skills_basic_clean", []))

    scores = {}

    # Tính điểm cho từng nhóm nghề
    for group in TITLE_KEYWORDS.keys():
        title_score = calculate_title_score(title, group)
        skill_score = calculate_skill_score(skills, group)

        if is_generic_title(title):
            final_score = 0.25 * title_score + 0.75 * skill_score
        else:
            final_score = 0.70 * title_score + 0.30 * skill_score

        scores[group] = final_score

    # Lấy nhóm nghề có điểm cao nhất
    best_group = max(scores, key=scores.get)
    best_score = scores[best_group]

    # Nếu không có tín hiệu rõ ràng thì đưa về Other / Unknown
    if best_score == 0:
        best_group = "Other / Unknown"
        method = "no_match"
        needs_review = True
    else:
        method = "title_skill_rule"
        needs_review = best_score < 0.65

    return pd.Series(
        {
            "occupation_group_preliminary": best_group,
            "occupation_confidence_preliminary": round(float(best_score), 4),
            "classification_method_preliminary": method,
            "needs_review_preliminary": needs_review,
        }
    )


def build_preclassified(df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bản copy để không làm thay đổi DataFrame gốc
    result_df = df.copy()

    # Chia ngành sơ bộ
    classified_cols = result_df.apply(
        classify_occupation,
        axis=1,
    )

    # Ghép kết quả phân ngành vào DataFrame
    result_df = pd.concat(
        [result_df, classified_cols],
        axis=1,
    )

    return result_df


def main() -> None:
    print("Bắt đầu build Silver 03 Preclassified cho Kaggle")

    # Kết nối MinIO
    client = get_minio_client()

    # Đọc dữ liệu Silver 02 Basic Clean
    print("\nBước 1: Đọc dữ liệu Silver 02 Basic Clean")
    basic_clean_df = read_parquet_from_minio(
        client=client,
        object_name=SILVER_KAGGLE_BASIC_CLEAN,
    )

    # Chia ngành sơ bộ
    print("\nBước 2: Chia ngành sơ bộ")
    preclassified_df = build_preclassified(basic_clean_df)

    # In thống kê nhóm nghề
    print("\nThống kê occupation_group_preliminary:")
    print(
        preclassified_df["occupation_group_preliminary"]
        .value_counts()
        .head(20)
    )

    print(f"\nSố dòng, số cột: {preclassified_df.shape}")

    # Lưu sang Silver 03 Preclassified
    print("\nBước 3: Lưu dữ liệu sang Silver 03 Preclassified")
    upload_df_parquet(
        client=client,
        df=preclassified_df,
        object_name=SILVER_KAGGLE_PRECLASSIFIED,
    )

    # Kiểm tra vùng Silver 03
    print("\nBước 4: Kiểm tra vùng Silver 03 Preclassified")
    list_objects(
        client=client,
        prefix="silver/kaggle/03_preclassified/",
    )

    print("\nHoàn thành build Silver 03 Preclassified.")


if __name__ == "__main__":
    main()