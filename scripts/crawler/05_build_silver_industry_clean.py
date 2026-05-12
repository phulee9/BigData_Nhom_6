import ast
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
    silver_crawler_preclassified,
    silver_crawler_industry_clean,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
    upload_df_parquet,
    list_objects,
)


TITLE_PATTERNS = {
    "Data & Analytics": [
        (r"\bdata analyst\b", "Data Analyst", "Analytics"),
        (r"\bbusiness analyst\b", "Business Analyst", "Business Analysis"),
        (r"\bbusiness intelligence\b", "Business Intelligence Analyst", "BI"),
        (r"\bbi analyst\b", "Business Intelligence Analyst", "BI"),
        (r"\bdata scientist\b", "Data Scientist", "Data Science"),
        (r"\bdata engineer\b", "Data Engineer", "Data Engineering"),
        (r"\banalytics engineer\b", "Analytics Engineer", "Analytics"),
        (r"\bproduct analyst\b", "Product Analyst", "Product Analytics"),
    ],
    "IT / Software": [
        (r"\bai engineer\b", "AI Engineer", "AI Engineering"),
        (r"\bnlp data engineer\b", "NLP Data Engineer", "Data Engineering"),
        (r"\bsoftware engineer\b", "Software Engineer", "Software Development"),
        (r"\bsoftware developer\b", "Software Developer", "Software Development"),
        (r"\bbackend\b", "Backend Developer", "Software Development"),
        (r"\bfront end\b", "Frontend Developer", "Software Development"),
        (r"\bfrontend\b", "Frontend Developer", "Software Development"),
        (r"\bfullstack\b", "Full Stack Developer", "Software Development"),
        (r"\bfull stack\b", "Full Stack Developer", "Software Development"),
        (r"\b\.net developer\b", ".NET Developer", "Software Development"),
        (r"\bdevops\b", "DevOps Engineer", "Infrastructure"),
        (r"\bqa engineer\b", "QA Engineer", "Quality Assurance"),
        (r"\btest automation\b", "Test Automation Engineer", "Quality Assurance"),
        (r"\bsolution designer\b", "Solution Designer", "Solution Architecture"),
        (r"\bsolution architect\b", "Solution Architect", "Solution Architecture"),
        (r"\bproduct owner\b", "Product Owner", "Product Management"),
        (r"\bsecurity operations center\b", "SOC Engineer", "Cyber Security"),
        (r"\bsoc engineer\b", "SOC Engineer", "Cyber Security"),
        (r"\bcyber security\b", "Cyber Security Specialist", "Cyber Security"),
        (r"\binformation security\b", "Information Security Specialist", "Cyber Security"),
    ],
    "Finance & Accounting": [
        (r"\bfinancial analyst\b", "Financial Analyst", "Finance"),
        (r"\bfinance\b", "Finance Specialist", "Finance"),
        (r"\baccountant\b", "Accountant", "Accounting"),
        (r"\bchief accountant\b", "Chief Accountant", "Accounting"),
        (r"\bauditor\b", "Auditor", "Audit"),
        (r"\bit audit\b", "IT Auditor", "Audit"),
        (r"\binvestment analyst\b", "Investment Analyst", "Investment"),
        (r"\brelationship manager\b", "Relationship Manager", "Banking"),
    ],
    "Sales": [
        (r"\bsales executive\b", "Sales Executive", "Sales"),
        (r"\bsales manager\b", "Sales Manager", "Sales"),
        (r"\bsales lead\b", "Sales Lead", "Sales"),
        (r"\baccount executive\b", "Account Executive", "Sales"),
        (r"\baccount manager\b", "Account Manager", "Sales"),
        (r"\bbusiness development\b", "Business Development Specialist", "Sales"),
        (r"\bkey account\b", "Key Account Manager", "Sales"),
        (r"\binside sales\b", "Inside Sales Representative", "Sales"),
    ],
    "Marketing / Communications": [
        (r"\bmarketing specialist\b", "Marketing Specialist", "Marketing"),
        (r"\bmarketing manager\b", "Marketing Manager", "Marketing"),
        (r"\bdigital marketing\b", "Digital Marketing Specialist", "Digital Marketing"),
        (r"\bsocial media\b", "Social Media Specialist", "Digital Marketing"),
        (r"\bseo\b", "SEO Specialist", "Digital Marketing"),
        (r"\bsem\b", "SEM Specialist", "Digital Marketing"),
        (r"\bbrand\b", "Brand Specialist", "Brand"),
        (r"\bgrowth\b", "Growth Manager", "Growth"),
        (r"\buser acquisition\b", "User Acquisition Specialist", "Growth"),
    ],
    "Human Resources": [
        (r"\bhuman resources\b", "Human Resources Specialist", "HR"),
        (r"\bhr officer\b", "Human Resources Officer", "HR"),
        (r"\bhrbp\b", "HR Business Partner", "HR"),
        (r"\brecruitment\b", "Recruitment Specialist", "Recruitment"),
        (r"\brecruiter\b", "Recruiter", "Recruitment"),
        (r"\btalent acquisition\b", "Talent Acquisition Specialist", "Recruitment"),
        (r"\blearning partner\b", "Learning and Development Specialist", "Learning and Development"),
    ],
    "Healthcare": [
        (r"\bregistered nurse\b", "Registered Nurse", "Clinical Care"),
        (r"\bnurse\b", "Nurse", "Clinical Care"),
        (r"\bmedical\b", "Medical Specialist", "Healthcare"),
        (r"\bclinical\b", "Clinical Specialist", "Clinical Care"),
        (r"\bregulatory affairs\b", "Regulatory Affairs Specialist", "Regulatory Affairs"),
        (r"\blab manager\b", "Lab Manager", "Laboratory"),
    ],
    "Education / Training": [
        (r"\bteacher\b", "Teacher", "Teaching"),
        (r"\binstructor\b", "Instructor", "Teaching"),
        (r"\btrainer\b", "Trainer", "Training"),
        (r"\btraining\b", "Training Specialist", "Training"),
        (r"\blearning\b", "Learning Specialist", "Learning and Development"),
    ],
    "Logistics / Supply Chain": [
        (r"\blogistics\b", "Logistics Specialist", "Logistics"),
        (r"\bsupply chain\b", "Supply Chain Specialist", "Supply Chain"),
        (r"\bwarehouse\b", "Warehouse Specialist", "Warehousing"),
        (r"\btransportation\b", "Transportation Specialist", "Transportation"),
        (r"\bprocurement\b", "Procurement Specialist", "Procurement"),
        (r"\bpurchasing\b", "Purchasing Specialist", "Procurement"),
        (r"\bmaterial coordinator\b", "Material Coordinator", "Supply Chain"),
    ],
    "Customer Service": [
        (r"\bcustomer service\b", "Customer Service Representative", "Customer Service"),
        (r"\bcustomer support\b", "Customer Support Specialist", "Customer Support"),
        (r"\bcustomer success\b", "Customer Success Manager", "Customer Success"),
        (r"\bfield service\b", "Field Service Engineer", "Field Service"),
    ],
    "Engineering": [
        (r"\bmechanical\b", "Mechanical Engineer", "Engineering"),
        (r"\belectrical\b", "Electrical Engineer", "Engineering"),
        (r"\bcivil\b", "Civil Engineer", "Engineering"),
        (r"\bhardware\b", "Hardware Engineer", "Engineering"),
        (r"\bcad drafter\b", "CAD Drafter", "Design Engineering"),
        (r"\bdrafter\b", "Drafter", "Design Engineering"),
        (r"\bquality engineer\b", "Quality Engineer", "Quality Engineering"),
        (r"\btest engineer\b", "Test Engineer", "Testing Engineering"),
        (r"\bprocess engineer\b", "Process Engineer", "Process Engineering"),
        (r"\bengineer\b", "Engineer", "Engineering"),
    ],
    "Legal": [
        (r"\blegal\b", "Legal Specialist", "Legal"),
        (r"\blaw\b", "Legal Specialist", "Legal"),
        (r"\bcompliance\b", "Compliance Specialist", "Compliance"),
        (r"\bip associate\b", "IP Associate", "Intellectual Property"),
        (r"\btrade compliance\b", "Trade Compliance Specialist", "Compliance"),
    ],
    "Retail / Hospitality": [
        (r"\bhotel\b", "Hotel Staff", "Hospitality"),
        (r"\bresort\b", "Resort Staff", "Hospitality"),
        (r"\bhousekeeping\b", "Housekeeping Manager", "Hospitality"),
        (r"\brestaurant\b", "Restaurant Staff", "Food Service"),
        (r"\bcashier\b", "Cashier", "Retail"),
        (r"\bstore manager\b", "Store Manager", "Retail"),
    ],
    "Manufacturing / Production": [
        (r"\bproduction\b", "Production Specialist", "Production"),
        (r"\bmanufacturing\b", "Manufacturing Specialist", "Manufacturing"),
        (r"\bqc staff\b", "QC Staff", "Quality Control"),
        (r"\bquality control\b", "Quality Control Specialist", "Quality Control"),
        (r"\bsmt\b", "SMT Engineer", "Manufacturing Engineering"),
    ],
}


SKILL_ALIASES = {
    "ai": "AI",
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "microsoft power bi": "Power BI",
    "excel": "Microsoft Excel",
    "ms excel": "Microsoft Excel",
    "microsoft excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "ms powerpoint": "Microsoft PowerPoint",
    "sql": "SQL",
    "sql server": "SQL Server",
    "mssql": "SQL Server",
    "mysql": "MySQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "node.js": "Node.js",
    "reactjs": "React",
    "react js": "React",
    "react.js": "React",
    "vuejs": "Vue.js",
    "vue js": "Vue.js",
    "vue": "Vue.js",
    "devops": "DevOps",
    "aws": "AWS",
    "aws cloud": "AWS Cloud",
    "azure": "Azure",
    "azure cloud": "Azure Cloud",
    "restful apis": "RESTful APIs",
    "apis": "APIs",
    "api design": "API Design",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "nlp": "NLP",
    "llm": "LLM",
    "rag": "RAG",
    "crm": "CRM",
    "salesforce crm": "Salesforce CRM",
    "jira": "JIRA",
    "ifrs": "IFRS",
    "gaap": "GAAP",
    "seo": "SEO",
    "sem": "SEM",
}


NOISE_SKILL_PATTERNS = [
    r"\b\d+\+?\s*(years?|yrs?)\b",
    r"\bexperience\b",
    r"\bdegree\b",
    r"\bbachelor\b",
    r"\bmaster\b",
    r"\bphd\b",
    r"\bability to\b",
    r"\bresponsible for\b",
    r"\bsalary\b",
    r"\bbenefits?\b",
]


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


def list_preclassified_batches(client) -> list[str]:
    # Lấy danh sách batch đã có Silver 03 Preclassified
    objects = client.list_objects(
        bucket_name=MINIO_BUCKET,
        prefix="silver/crawler/",
        recursive=True,
    )

    batch_names = set()

    for obj in objects:
        object_name = obj.object_name

        if not object_name.endswith("/03_preclassified/jobs_preclassified.parquet"):
            continue

        parts = object_name.split("/")

        if len(parts) >= 3:
            batch_names.add(parts[2])

    return sorted(batch_names)


def find_unprocessed_batch(client) -> str | None:
    # Tìm batch đã preclassified nhưng chưa industry clean
    batch_names = list_preclassified_batches(client)

    if not batch_names:
        print("Không tìm thấy batch nào đã preclassified.")
        return None

    for batch_name in batch_names:
        industry_clean_object = silver_crawler_industry_clean(batch_name)

        if object_exists(client, industry_clean_object):
            print(f"Bỏ qua batch đã industry clean: {batch_name}")
            continue

        return batch_name

    return None


def parse_skills(value) -> list[str]:
    # Chuyển skills_basic_clean về list thật
    if value is None:
        return []

    if isinstance(value, float) and pd.isna(value):
        return []

    if isinstance(value, list):
        return [
            str(skill).strip()
            for skill in value
            if str(skill).strip()
        ]

    if isinstance(value, np.ndarray):
        return [
            str(skill).strip()
            for skill in value.tolist()
            if str(skill).strip()
        ]

    if isinstance(value, (tuple, set)):
        return [
            str(skill).strip()
            for skill in list(value)
            if str(skill).strip()
        ]

    if isinstance(value, str):
        text = value.strip()

        if text.lower() in ["", "[]", "nan", "none", "null"]:
            return []

        try:
            parsed = ast.literal_eval(text)

            if isinstance(parsed, list):
                return [
                    str(skill).strip()
                    for skill in parsed
                    if str(skill).strip()
                ]

            if isinstance(parsed, (tuple, set)):
                return [
                    str(skill).strip()
                    for skill in list(parsed)
                    if str(skill).strip()
                ]
        except Exception:
            pass

        return [text]

    return []


def normalize_title_text(title: str) -> str:
    # Chuẩn hóa text title để so khớp regex
    text = str(title or "").strip()
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = re.sub(r"\s+", " ", text)

    return text


def extract_seniority(title: str) -> str:
    # Tách cấp bậc từ title
    text = str(title or "").lower()

    if re.search(r"\b(intern|internship|trainee)\b", text):
        return "Intern"

    if re.search(r"\b(junior|entry level|entry)\b", text):
        return "Junior"

    if re.search(r"\b(senior|lead|principal|staff|expert)\b", text):
        return "Senior"

    if re.search(r"\b(manager|head|director|vp|chief|cfo|country manager)\b", text):
        return "Manager"

    return "Not specified"


def canonicalize_title(title: str, occupation_group: str) -> tuple[str, str]:
    # Chuẩn hóa job title theo nhóm ngành sơ bộ
    title = normalize_title_text(title)
    title_lower = title.lower()

    patterns = TITLE_PATTERNS.get(occupation_group, [])

    for pattern, canonical_title, function_group in patterns:
        if re.search(pattern, title_lower):
            return canonical_title, function_group

    if not title:
        return "", "Other"

    return title.title(), "Other"


def is_noise_skill(skill: str) -> bool:
    # Kiểm tra skill có phải nhiễu không
    text = str(skill or "").strip().lower()

    if len(text) <= 1:
        return True

    if text in ["null", "none", "nan"]:
        return True

    if len(text.split()) > 8:
        return True

    for pattern in NOISE_SKILL_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


def canonicalize_skill(skill: str) -> str:
    # Chuẩn hóa một skill về tên chuẩn
    text = str(skill or "").strip()
    text = re.sub(r"\s+", " ", text)

    if not text:
        return ""

    key = text.lower()

    if key in SKILL_ALIASES:
        return SKILL_ALIASES[key]

    if any(char in text for char in ["#", "+", ".", "/", "-"]):
        return text

    return text.title()


def canonicalize_skills(skills: list[str]) -> list[str]:
    # Chuẩn hóa danh sách skills
    result = []

    for skill in skills:
        if is_noise_skill(skill):
            continue

        canonical_skill = canonicalize_skill(skill)

        if canonical_skill:
            result.append(canonical_skill)

    return list(dict.fromkeys(result))


def build_industry_clean_df(df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bản copy để không làm thay đổi DataFrame gốc
    result_df = df.copy()

    # Chuẩn hóa title và function group
    title_result = result_df.apply(
        lambda row: canonicalize_title(
            row.get("job_title_basic_clean", ""),
            row.get("occupation_group_preliminary", "Other / Unknown"),
        ),
        axis=1,
    )

    result_df["job_title_canonical"] = title_result.apply(lambda value: value[0])
    result_df["function_group"] = title_result.apply(lambda value: value[1])

    # Tách seniority
    result_df["seniority"] = result_df["job_title_basic_clean"].apply(
        extract_seniority
    )

    # Chuẩn hóa skills
    result_df["skills_canonical"] = result_df["skills_basic_clean"].apply(
        lambda value: canonicalize_skills(parse_skills(value))
    )

    # Đếm số skill sau clean
    result_df["skills_count_clean"] = result_df["skills_canonical"].apply(len)

    return result_df


def main() -> None:
    print("Bắt đầu build Silver 04 Industry Clean cho Crawler")

    # Kết nối MinIO
    client = get_minio_client()

    # Tìm batch chưa industry clean
    print("\nBước 1: Tìm batch crawler chưa industry clean")
    batch_name = find_unprocessed_batch(client)

    if batch_name is None:
        print("\nKhông có batch crawler mới cần industry clean.")
        print("Dừng bước 05.")
        return

    preclassified_object = silver_crawler_preclassified(batch_name)
    industry_clean_object = silver_crawler_industry_clean(batch_name)

    print(f"Batch cần xử lý: {batch_name}")
    print(f"Input Silver 03: s3://{MINIO_BUCKET}/{preclassified_object}")
    print(f"Output Silver 04: s3://{MINIO_BUCKET}/{industry_clean_object}")

    # Đọc Silver 03 Preclassified
    print("\nBước 2: Đọc dữ liệu Silver 03 Preclassified")
    preclassified_df = read_parquet_from_minio(
        client=client,
        object_name=preclassified_object,
    )

    # Industry clean
    print("\nBước 3: Clean sâu title và skills theo ngành")
    industry_clean_df = build_industry_clean_df(preclassified_df)

    # Kiểm tra kết quả
    print("\nSample Industry Clean:")
    print(
        industry_clean_df[
            [
                "job_title_basic_clean",
                "job_title_canonical",
                "occupation_group_preliminary",
                "function_group",
                "seniority",
                "skills_canonical",
                "skills_count_clean",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print(f"\nSố dòng, số cột: {industry_clean_df.shape}")

    print("\nThống kê skills_count_clean:")
    print(industry_clean_df["skills_count_clean"].describe())

    print("\nThống kê seniority:")
    print(industry_clean_df["seniority"].value_counts())

    # Lưu Silver 04 Industry Clean
    print("\nBước 4: Lưu Silver 04 Industry Clean lên MinIO")
    upload_df_parquet(
        client=client,
        df=industry_clean_df,
        object_name=industry_clean_object,
    )

    # Kiểm tra vùng Silver Crawler Industry Clean
    print("\nBước 5: Kiểm tra vùng Silver Crawler Industry Clean")
    list_objects(
        client=client,
        prefix=f"silver/crawler/{batch_name}/04_industry_clean/",
    )

    print("\nHoàn thành build Silver 04 Industry Clean cho Crawler.")


if __name__ == "__main__":
    main()