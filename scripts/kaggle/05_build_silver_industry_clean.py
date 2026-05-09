import ast
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    SILVER_KAGGLE_PRECLASSIFIED,
    SILVER_KAGGLE_INDUSTRY_CLEAN,
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
        (r"\bbusiness intelligence\b", "Business Intelligence Analyst", "BI"),
        (r"\bbi analyst\b", "Business Intelligence Analyst", "BI"),
        (r"\breporting analyst\b", "Reporting Analyst", "Analytics"),
        (r"\bdata scientist\b", "Data Scientist", "Data Science"),
        (r"\bdata engineer\b", "Data Engineer", "Data Engineering"),
        (r"\banalytics engineer\b", "Analytics Engineer", "Analytics"),
    ],
    "IT / Software": [
        (r"\bsoftware engineer\b", "Software Engineer", "Software Development"),
        (r"\bsoftware developer\b", "Software Developer", "Software Development"),
        (r"\bbackend\b", "Backend Developer", "Software Development"),
        (r"\bfront end\b", "Frontend Developer", "Software Development"),
        (r"\bfrontend\b", "Frontend Developer", "Software Development"),
        (r"\bfull stack\b", "Full Stack Developer", "Software Development"),
        (r"\bdevops\b", "DevOps Engineer", "Infrastructure"),
        (r"\bprogrammer\b", "Programmer", "Software Development"),
        (r"\bsystems administrator\b", "Systems Administrator", "Infrastructure"),
    ],
    "Finance & Accounting": [
        (r"\bfinancial analyst\b", "Financial Analyst", "Finance"),
        (r"\bfinance analyst\b", "Financial Analyst", "Finance"),
        (r"\baccountant\b", "Accountant", "Accounting"),
        (r"\bauditor\b", "Auditor", "Audit"),
        (r"\bbookkeeper\b", "Bookkeeper", "Accounting"),
        (r"\bcontroller\b", "Controller", "Accounting"),
        (r"\bpayroll\b", "Payroll Specialist", "Payroll"),
        (r"\btax\b", "Tax Specialist", "Tax"),
    ],
    "Sales": [
        (r"\bsales representative\b", "Sales Representative", "Sales"),
        (r"\bsales executive\b", "Sales Executive", "Sales"),
        (r"\baccount executive\b", "Account Executive", "Sales"),
        (r"\bsales consultant\b", "Sales Consultant", "Sales"),
        (r"\bbusiness development\b", "Business Development Representative", "Sales"),
        (r"\bsales manager\b", "Sales Manager", "Sales"),
    ],
    "Marketing / Communications": [
        (r"\bmarketing specialist\b", "Marketing Specialist", "Marketing"),
        (r"\bmarketing manager\b", "Marketing Manager", "Marketing"),
        (r"\bseo\b", "SEO Specialist", "Digital Marketing"),
        (r"\bcontent manager\b", "Content Manager", "Content"),
        (r"\bsocial media\b", "Social Media Specialist", "Digital Marketing"),
        (r"\bbrand manager\b", "Brand Manager", "Brand"),
        (r"\bcommunications\b", "Communications Specialist", "Communications"),
    ],
    "Human Resources": [
        (r"\bhuman resources\b", "Human Resources Specialist", "HR"),
        (r"\bhr specialist\b", "Human Resources Specialist", "HR"),
        (r"\bhr manager\b", "Human Resources Manager", "HR"),
        (r"\brecruiter\b", "Recruiter", "Recruitment"),
        (r"\btalent acquisition\b", "Talent Acquisition Specialist", "Recruitment"),
        (r"\bpeople operations\b", "People Operations Specialist", "HR Operations"),
    ],
    "Healthcare": [
        (r"\bregistered nurse\b", "Registered Nurse", "Clinical Care"),
        (r"\bnurse\b", "Nurse", "Clinical Care"),
        (r"\bmedical assistant\b", "Medical Assistant", "Healthcare Support"),
        (r"\bphysician\b", "Physician", "Clinical Care"),
        (r"\bpharmacist\b", "Pharmacist", "Pharmacy"),
        (r"\btherapist\b", "Therapist", "Therapy"),
        (r"\bclinical\b", "Clinical Specialist", "Clinical Care"),
    ],
    "Education / Training": [
        (r"\bteacher\b", "Teacher", "Teaching"),
        (r"\binstructor\b", "Instructor", "Teaching"),
        (r"\bprofessor\b", "Professor", "Higher Education"),
        (r"\btutor\b", "Tutor", "Teaching"),
        (r"\bteaching assistant\b", "Teaching Assistant", "Teaching Support"),
        (r"\btrainer\b", "Trainer", "Training"),
    ],
    "Logistics / Supply Chain": [
        (r"\bwarehouse\b", "Warehouse Associate", "Warehousing"),
        (r"\blogistics\b", "Logistics Specialist", "Logistics"),
        (r"\bsupply chain\b", "Supply Chain Specialist", "Supply Chain"),
        (r"\binventory\b", "Inventory Specialist", "Inventory"),
        (r"\bprocurement\b", "Procurement Specialist", "Procurement"),
        (r"\bbuyer\b", "Buyer", "Procurement"),
        (r"\bshipping\b", "Shipping Specialist", "Logistics"),
    ],
    "Customer Service": [
        (r"\bcustomer service\b", "Customer Service Representative", "Customer Support"),
        (r"\bcustomer support\b", "Customer Support Specialist", "Customer Support"),
        (r"\bcall center\b", "Call Center Representative", "Customer Support"),
        (r"\bclient support\b", "Client Support Specialist", "Customer Support"),
        (r"\bguest service\b", "Guest Service Representative", "Customer Service"),
    ],
    "Engineering": [
        (r"\bmechanical engineer\b", "Mechanical Engineer", "Engineering"),
        (r"\belectrical engineer\b", "Electrical Engineer", "Engineering"),
        (r"\bcivil engineer\b", "Civil Engineer", "Engineering"),
        (r"\bmanufacturing engineer\b", "Manufacturing Engineer", "Manufacturing Engineering"),
        (r"\bprocess engineer\b", "Process Engineer", "Process Engineering"),
        (r"\bquality engineer\b", "Quality Engineer", "Quality Engineering"),
    ],
    "Legal": [
        (r"\blegal assistant\b", "Legal Assistant", "Legal Support"),
        (r"\bparalegal\b", "Paralegal", "Legal Support"),
        (r"\battorney\b", "Attorney", "Legal"),
        (r"\blawyer\b", "Lawyer", "Legal"),
        (r"\blegal counsel\b", "Legal Counsel", "Legal"),
        (r"\bcompliance officer\b", "Compliance Officer", "Compliance"),
    ],
    "Retail / Hospitality": [
        (r"\bcashier\b", "Cashier", "Retail"),
        (r"\bstore associate\b", "Store Associate", "Retail"),
        (r"\bretail associate\b", "Retail Associate", "Retail"),
        (r"\brestaurant\b", "Restaurant Staff", "Food Service"),
        (r"\bserver\b", "Server", "Food Service"),
        (r"\bbarista\b", "Barista", "Food Service"),
        (r"\bhotel\b", "Hotel Staff", "Hospitality"),
        (r"\bhospitality\b", "Hospitality Staff", "Hospitality"),
    ],
    "Manufacturing / Production": [
        (r"\bproduction worker\b", "Production Worker", "Production"),
        (r"\bmachine operator\b", "Machine Operator", "Production"),
        (r"\bassembler\b", "Assembler", "Production"),
        (r"\bmanufacturing\b", "Manufacturing Worker", "Manufacturing"),
        (r"\bproduction supervisor\b", "Production Supervisor", "Production"),
    ],
}


SKILL_ALIASES = {
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "microsoft power bi": "Power BI",
    "excel": "Microsoft Excel",
    "ms excel": "Microsoft Excel",
    "microsoft excel": "Microsoft Excel",
    "sql server": "SQL Server",
    "mssql": "SQL Server",
    "mysql": "MySQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "node.js": "Node.js",
    "reactjs": "React",
    "react js": "React",
    "react.js": "React",
    "c sharp": "C#",
    "c#": "C#",
    "c plus plus": "C++",
    "c++": "C++",
    "dotnet": ".NET",
    "dot net": ".NET",
    ".net": ".NET",
    "gaap": "GAAP",
    "ifrs": "IFRS",
    "p&l": "Profit and Loss",
    "crm": "CRM",
    "salesforce": "Salesforce",
    "seo": "SEO",
    "sem": "SEM",
    "cpr": "CPR",
    "bls": "Basic Life Support",
    "emr": "Electronic Medical Records",
    "hipaa": "HIPAA",
    "wms": "Warehouse Management System",
    "osha": "OSHA",
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


def parse_skills(value) -> list[str]:
    # Chuyển skills_basic_clean về list thật

    # Xử lý giá trị rỗng
    if value is None:
        return []

    # Xử lý NaN dạng float
    if isinstance(value, float) and pd.isna(value):
        return []

    # Xử lý list Python
    if isinstance(value, list):
        return [
            str(skill).strip()
            for skill in value
            if str(skill).strip()
        ]

    # Xử lý numpy array khi đọc list từ Parquet
    if isinstance(value, np.ndarray):
        return [
            str(skill).strip()
            for skill in value.tolist()
            if str(skill).strip()
        ]

    # Xử lý tuple hoặc set
    if isinstance(value, (tuple, set)):
        return [
            str(skill).strip()
            for skill in list(value)
            if str(skill).strip()
        ]

    # Xử lý string
    if isinstance(value, str):
        text = value.strip()

        # String rỗng hoặc biểu diễn rỗng
        if text in ["", "[]", "nan", "None", "null"]:
            return []

        # String dạng "['SQL', 'Power BI']"
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

        # Nếu là string thường thì coi là một skill
        return [text]

    # Các kiểu khác chưa xử lý thì trả về rỗng
    return []


def extract_seniority(title: str) -> str:
    # Tách cấp bậc từ title
    title = title or ""

    if re.search(r"\b(intern|trainee)\b", title):
        return "Intern"

    if re.search(r"\b(junior|entry level|entry)\b", title):
        return "Junior"

    if re.search(r"\b(senior|lead|principal|staff)\b", title):
        return "Senior"

    if re.search(r"\b(manager|head|director|vp|chief)\b", title):
        return "Manager"

    return "Not specified"


def canonicalize_title(title: str, occupation_group: str) -> tuple[str, str]:
    # Chuẩn hóa job title theo nhóm ngành sơ bộ
    title = str(title or "").strip()

    patterns = TITLE_PATTERNS.get(occupation_group, [])

    for pattern, canonical_title, function_group in patterns:
        if re.search(pattern, title):
            return canonical_title, function_group

    if not title:
        return "", "Other"

    return title.title(), "Other"


def is_noise_skill(skill: str) -> bool:
    # Kiểm tra skill có phải nhiễu không
    skill = str(skill or "").strip().lower()

    if len(skill) <= 1:
        return True

    if len(skill.split()) > 7:
        return True

    for pattern in NOISE_SKILL_PATTERNS:
        if re.search(pattern, skill):
            return True

    return False


def canonicalize_skill(skill: str) -> str:
    # Chuẩn hóa một skill về tên chuẩn
    skill = str(skill or "").strip().lower()
    skill = re.sub(r"\s+", " ", skill)

    if not skill:
        return ""

    if skill in SKILL_ALIASES:
        return SKILL_ALIASES[skill]

    if any(char in skill for char in ["#", "+", ".", "/"]):
        return skill

    return skill.title()


def canonicalize_skills(skills: list[str]) -> list[str]:
    # Chuẩn hóa danh sách skills
    result = []

    for skill in skills:
        if is_noise_skill(skill):
            continue

        canonical_skill = canonicalize_skill(skill)

        if canonical_skill:
            result.append(canonical_skill)

    # Xóa trùng nhưng giữ thứ tự
    return list(dict.fromkeys(result))


def build_industry_clean(df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bản copy để không làm thay đổi DataFrame gốc
    result_df = df.copy()

    # Chuẩn hóa job title và function group
    title_result = result_df.apply(
        lambda row: canonicalize_title(
            row.get("job_title_basic_clean", ""),
            row.get("occupation_group_preliminary", "Other / Unknown"),
        ),
        axis=1,
    )

    result_df["job_title_canonical"] = title_result.apply(lambda x: x[0])
    result_df["function_group"] = title_result.apply(lambda x: x[1])

    # Tách seniority
    result_df["seniority"] = result_df["job_title_basic_clean"].apply(
        extract_seniority
    )

    # Chuẩn hóa skills
    result_df["skills_canonical"] = result_df["skills_basic_clean"].apply(
        lambda x: canonicalize_skills(parse_skills(x))
    )

    # Đếm số skill sau chuẩn hóa
    result_df["skills_count_clean"] = result_df["skills_canonical"].apply(len)

    return result_df


def main() -> None:
    print("Bắt đầu build Silver 04 Industry Clean cho Kaggle")

    # Kết nối MinIO
    client = get_minio_client()

    # Đọc dữ liệu Silver 03 Preclassified
    print("\nBước 1: Đọc dữ liệu Silver 03 Preclassified")
    preclassified_df = read_parquet_from_minio(
        client=client,
        object_name=SILVER_KAGGLE_PRECLASSIFIED,
    )

    # Kiểm tra kiểu dữ liệu skills_basic_clean trước khi clean
    print("\nKiểu dữ liệu của skills_basic_clean:")
    print(
        preclassified_df["skills_basic_clean"]
        .apply(type)
        .value_counts()
        .head(10)
    )

    # Clean sâu theo ngành sơ bộ
    print("\nBước 2: Clean sâu job_title và skills")
    industry_clean_df = build_industry_clean(preclassified_df)

    # Kiểm tra nhanh kết quả
    print("\nKết quả Industry Clean:")
    print(
        industry_clean_df[
            [
                "job_title_basic_clean",
                "job_title_canonical",
                "occupation_group_preliminary",
                "seniority",
                "skills_basic_clean",
                "skills_canonical",
                "skills_count_clean",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print(f"\nSố dòng, số cột: {industry_clean_df.shape}")

    # Thống kê số skill sau clean
    print("\nThống kê skills_count_clean:")
    print(industry_clean_df["skills_count_clean"].describe())

    # Kiểm tra tỷ lệ dòng không có skill
    no_skill_count = (
        industry_clean_df["skills_count_clean"] == 0
    ).sum()

    print("\nSố dòng không có skill sau clean:")
    print(no_skill_count)

    print("\nTỷ lệ dòng không có skill sau clean:")
    print(round(no_skill_count / len(industry_clean_df) * 100, 2), "%")

    # In sample dòng có skill để kiểm tra
    has_skill_df = industry_clean_df[
        industry_clean_df["skills_count_clean"] > 0
    ]

    print("\nSample dòng có skill sau clean:")
    if len(has_skill_df) > 0:
        print(
            has_skill_df[
                [
                    "job_title_canonical",
                    "skills_basic_clean",
                    "skills_canonical",
                    "skills_count_clean",
                ]
            ]
            .head(10)
            .to_string(index=False)
        )
    else:
        print("Không tìm thấy dòng nào có skill. Cần kiểm tra lại bước Silver 02 Basic Clean.")

    # Lưu sang Silver 04 Industry Clean
    print("\nBước 3: Lưu dữ liệu sang Silver 04 Industry Clean")
    upload_df_parquet(
        client=client,
        df=industry_clean_df,
        object_name=SILVER_KAGGLE_INDUSTRY_CLEAN,
    )

    # Kiểm tra vùng Silver 04
    print("\nBước 4: Kiểm tra vùng Silver 04 Industry Clean")
    list_objects(
        client=client,
        prefix="silver/kaggle/04_industry_clean/",
    )

    print("\nHoàn thành build Silver 04 Industry Clean.")


if __name__ == "__main__":
    main()