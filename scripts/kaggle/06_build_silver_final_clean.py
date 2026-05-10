import ast
import re
import sys
from pathlib import Path

import pandas as pd

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    SILVER_KAGGLE_INDUSTRY_CLEAN,
    SILVER_KAGGLE_FINAL_CLEAN,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
    upload_df_parquet,
    list_objects,
)


# Mapping nhóm nghề chi tiết sang nhóm nghề cấp cao hơn
OCCUPATION_FAMILY_MAP = {
    "Data & Analytics": "Technology & Analytics",
    "IT / Software": "Technology & Analytics",
    "AI / Machine Learning": "Technology & Analytics",

    "Finance & Accounting": "Business & Finance",
    "Human Resources": "Business & Finance",
    "Legal": "Professional Services",

    "Sales": "Commercial",
    "Marketing / Communications": "Commercial",
    "Customer Service": "Commercial",
    "Retail / Hospitality": "Commercial",

    "Healthcare": "Healthcare",
    "Education / Training": "Education",

    "Logistics / Supply Chain": "Operations",
    "Manufacturing / Production": "Operations",

    "Engineering": "Engineering",

    "Other / Unknown": "Other / Unknown",
}


# Keyword theo title đã canonical
TITLE_GROUP_PATTERNS = {
    "AI / Machine Learning": [
        r"\bai engineer\b",
        r"\bmachine learning engineer\b",
        r"\bml engineer\b",
        r"\bdeep learning engineer\b",
        r"\bcomputer vision engineer\b",
        r"\bnlp engineer\b",
        r"\bprompt engineer\b",
        r"\bmlops engineer\b",
        r"\bai research scientist\b",
    ],
    "Data & Analytics": [
        r"\bdata analyst\b",
        r"\bbusiness intelligence analyst\b",
        r"\breporting analyst\b",
        r"\bdata scientist\b",
        r"\bdata engineer\b",
        r"\banalytics engineer\b",
    ],
    "IT / Software": [
        r"\bsoftware engineer\b",
        r"\bsoftware developer\b",
        r"\bbackend developer\b",
        r"\bfrontend developer\b",
        r"\bfull stack developer\b",
        r"\bdevops engineer\b",
        r"\bprogrammer\b",
        r"\bsystems administrator\b",
    ],
    "Finance & Accounting": [
        r"\bfinancial analyst\b",
        r"\baccountant\b",
        r"\bauditor\b",
        r"\bbookkeeper\b",
        r"\bcontroller\b",
        r"\bpayroll specialist\b",
        r"\btax specialist\b",
    ],
    "Sales": [
        r"\bsales representative\b",
        r"\bsales executive\b",
        r"\baccount executive\b",
        r"\bsales consultant\b",
        r"\bbusiness development representative\b",
        r"\bsales manager\b",
    ],
    "Marketing / Communications": [
        r"\bmarketing specialist\b",
        r"\bmarketing manager\b",
        r"\bseo specialist\b",
        r"\bcontent manager\b",
        r"\bsocial media specialist\b",
        r"\bbrand manager\b",
        r"\bcommunications specialist\b",
    ],
    "Human Resources": [
        r"\bhuman resources specialist\b",
        r"\bhuman resources manager\b",
        r"\brecruiter\b",
        r"\btalent acquisition specialist\b",
        r"\bpeople operations specialist\b",
    ],
    "Healthcare": [
        r"\bregistered nurse\b",
        r"\bnurse\b",
        r"\bmedical assistant\b",
        r"\bphysician\b",
        r"\bpharmacist\b",
        r"\btherapist\b",
        r"\bclinical specialist\b",
    ],
    "Education / Training": [
        r"\bteacher\b",
        r"\binstructor\b",
        r"\bprofessor\b",
        r"\btutor\b",
        r"\bteaching assistant\b",
        r"\btrainer\b",
    ],
    "Logistics / Supply Chain": [
        r"\bwarehouse associate\b",
        r"\blogistics specialist\b",
        r"\bsupply chain specialist\b",
        r"\binventory specialist\b",
        r"\bprocurement specialist\b",
        r"\bbuyer\b",
        r"\bshipping specialist\b",
    ],
    "Customer Service": [
        r"\bcustomer service representative\b",
        r"\bcustomer support specialist\b",
        r"\bcall center representative\b",
        r"\bclient support specialist\b",
        r"\bguest service representative\b",
    ],
    "Engineering": [
        r"\bmechanical engineer\b",
        r"\belectrical engineer\b",
        r"\bcivil engineer\b",
        r"\bmanufacturing engineer\b",
        r"\bprocess engineer\b",
        r"\bquality engineer\b",
    ],
    "Legal": [
        r"\blegal assistant\b",
        r"\bparalegal\b",
        r"\battorney\b",
        r"\blawyer\b",
        r"\blegal counsel\b",
        r"\bcompliance officer\b",
    ],
    "Retail / Hospitality": [
        r"\bcashier\b",
        r"\bstore associate\b",
        r"\bretail associate\b",
        r"\brestaurant staff\b",
        r"\bserver\b",
        r"\bbarista\b",
        r"\bhotel staff\b",
        r"\bhospitality staff\b",
    ],
    "Manufacturing / Production": [
        r"\bproduction worker\b",
        r"\bmachine operator\b",
        r"\bassembler\b",
        r"\bmanufacturing worker\b",
        r"\bproduction supervisor\b",
    ],
}


# Keyword theo skills đã canonical
SKILL_GROUP_KEYWORDS = {
    "AI / Machine Learning": [
        "machine learning",
        "deep learning",
        "tensorflow",
        "pytorch",
        "computer vision",
        "natural language processing",
        "nlp",
        "llm",
        "generative ai",
        "mlops",
    ],
    "Data & Analytics": [
        "sql",
        "power bi",
        "tableau",
        "dashboard",
        "data visualization",
        "statistics",
        "data modeling",
        "microsoft excel",
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
        "profit and loss",
    ],
    "Sales": [
        "crm",
        "salesforce",
        "lead generation",
        "cold calling",
        "negotiation",
        "account management",
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
        "basic life support",
        "electronic medical records",
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
        "warehouse management system",
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


def parse_skills(value) -> list[str]:
    # Chuyển skills_canonical về dạng list
    if isinstance(value, list):
        return value

    if value is None:
        return []

    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)

            if isinstance(parsed, list):
                return parsed
        except Exception:
            return [value]

    return []


def score_title_group(title: str, group: str) -> float:
    # Tính điểm ngành theo job_title_canonical
    title = str(title or "").lower()
    patterns = TITLE_GROUP_PATTERNS.get(group, [])

    for pattern in patterns:
        if re.search(pattern, title):
            return 1.0

    return 0.0


def score_skill_group(skills: list[str], group: str) -> float:
    # Tính điểm ngành theo skills_canonical
    if not skills:
        return 0.0

    keywords = SKILL_GROUP_KEYWORDS.get(group, [])

    if not keywords:
        return 0.0

    skills_text = " ".join([str(skill).lower() for skill in skills])
    match_count = 0

    for keyword in keywords:
        if keyword in skills_text:
            match_count += 1

    return min(match_count / 3, 1.0)


def classify_final(row: pd.Series) -> pd.Series:
    # Lấy dữ liệu đã clean sâu
    title = row.get("job_title_canonical", "")
    skills = parse_skills(row.get("skills_canonical", []))

    preliminary_group = row.get(
        "occupation_group_preliminary",
        "Other / Unknown",
    )

    preliminary_confidence = row.get(
        "occupation_confidence_preliminary",
        0.0,
    )

    # Tính điểm lại cho từng nhóm ngành
    scores = {}

    for group in TITLE_GROUP_PATTERNS.keys():
        title_score = score_title_group(title, group)
        skill_score = score_skill_group(skills, group)

        final_score = 0.75 * title_score + 0.25 * skill_score
        scores[group] = final_score

    best_group = max(scores, key=scores.get)
    best_score = scores[best_group]

    # Nếu final không có tín hiệu rõ, giữ lại kết quả sơ bộ nếu có
    if best_score == 0 and preliminary_group != "Other / Unknown":
        final_group = preliminary_group
        final_confidence = float(preliminary_confidence)
        method = "keep_preliminary"
    elif best_score == 0:
        final_group = "Other / Unknown"
        final_confidence = 0.0
        method = "no_match"
    else:
        final_group = best_group
        final_confidence = float(best_score)
        method = "final_title_skill_rule"

    # Gán nhóm ngành cấp cao
    final_family = OCCUPATION_FAMILY_MAP.get(
        final_group,
        "Other / Unknown",
    )

    # Đánh dấu dòng cần review
    needs_review = final_confidence < 0.65

    return pd.Series(
        {
            "occupation_group_final": final_group,
            "occupation_family_final": final_family,
            "occupation_confidence_final": round(final_confidence, 4),
            "classification_method_final": method,
            "needs_review_final": needs_review,
        }
    )


def build_final_clean(df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bản copy để không làm thay đổi DataFrame gốc
    result_df = df.copy()

    # Chia ngành lại lần cuối
    final_cols = result_df.apply(
        classify_final,
        axis=1,
    )

    # Ghép kết quả final vào DataFrame
    result_df = pd.concat(
        [result_df, final_cols],
        axis=1,
    )

    return result_df


def main() -> None:
    print("Bắt đầu build Silver 05 Final Clean cho Kaggle")

    # Kết nối MinIO
    client = get_minio_client()

    # Đọc dữ liệu Silver 04 Industry Clean
    print("\nBước 1: Đọc dữ liệu Silver 04 Industry Clean")
    industry_clean_df = read_parquet_from_minio(
        client=client,
        object_name=SILVER_KAGGLE_INDUSTRY_CLEAN,
    )

    # Chia ngành lại lần cuối
    print("\nBước 2: Chia ngành final")
    final_clean_df = build_final_clean(industry_clean_df)

    # In thống kê nhóm ngành final
    print("\nThống kê occupation_group_final:")
    print(
        final_clean_df["occupation_group_final"]
        .value_counts()
        .head(30)
    )

    print("\nThống kê occupation_family_final:")
    print(
        final_clean_df["occupation_family_final"]
        .value_counts()
        .head(30)
    )

    print(f"\nSố dòng, số cột: {final_clean_df.shape}")

    # Lưu sang Silver 05 Final Clean
    print("\nBước 3: Lưu dữ liệu sang Silver 05 Final Clean")
    upload_df_parquet(
        client=client,
        df=final_clean_df,
        object_name=SILVER_KAGGLE_FINAL_CLEAN,
    )

    # Kiểm tra vùng Silver 05
    print("\nBước 4: Kiểm tra vùng Silver 05 Final Clean")
    list_objects(
        client=client,
        prefix="silver/kaggle/05_final_clean/",
    )

    print("\nHoàn thành build Silver 05 Final Clean.")


if __name__ == "__main__":
    main()