import re

from recommendation.core.skill_config import (
    normalize_skill as normalize_skill_from_config,
    is_valid_skill,
)


SYNONYM_MAP = {
    "sr": "senior",
    "jr": "junior",
    "mgr": "manager",
    "mngr": "manager",
    "dev": "developer",
    "eng": "engineer",
    "swe": "software engineer",
    "frontend": "front end",
    "backend": "back end",
    "fullstack": "full stack",
    "full-stack": "full stack",
    "qa": "quality assurance",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "bi": "business intelligence",
    "ba": "business analyst",
    "pm": "project manager",
    "hr": "human resources",
    "seo": "search engine optimization",
    "powerbi": "power bi",
    "power-bi": "power bi",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "sql server": "sql",
    "postgresql": "postgres",
    "python3": "python",
    "nodejs": "node",
    "node js": "node",
    "node.js": "node",
}

NOISE_PATTERNS = [
    r"\b(remote|hybrid|onsite|on.site)\b",
    r"\b(part.time|full.time|contract|temp|temporary)\b",
    r"\b(urgent|immediate|opening|opportunity|hiring|wanted)\b",
    r"\b(vietnam|viet nam|ho chi minh|hanoi|ha noi|da nang|singapore|london|new york|california|texas|florida|chicago|boston|seattle|austin|canada|australia)\b",
    r"\b(f/m/d|m/f/d|w/m/d|m/w/d)\b",
    r"\b\d+\+?\s*(year|yr|month|week)s?\b",
    r"[-|\\]+.*$",
    r"\(.*?\)",
    r"\[.*?\]",
]

NOT_JOB_TITLE = {
    "compensation", "experience", "salary", "benefit",
    "remote", "hybrid", "travel", "unknown", "other",
    "na", "n/a", "none", "null", "opening", "opportunity",
    "position", "role", "job", "hiring", "wanted",
}

VALID_SINGLE_WORD = {
    "accountant", "analyst", "architect", "consultant",
    "developer", "designer", "engineer", "manager",
    "nurse", "programmer", "recruiter", "scientist",
    "specialist", "supervisor", "teacher", "therapist",
    "coordinator", "administrator", "director", "officer",
    "technician", "mechanic", "driver", "chef", "cook",
    "attorney", "lawyer", "doctor", "pharmacist",
}


def apply_synonym(text: str) -> str:
    if not isinstance(text, str):
        return ""

    for key, value in SYNONYM_MAP.items():
        text = re.sub(rf"\b{re.escape(key)}\b", value, text)

    return text


def normalize_skill(skill: str) -> str:
    if not isinstance(skill, str):
        return ""

    skill = skill.lower().strip()

    # Giữ lại . + # / để skill_config xử lý được node.js, .net, c#, ci/cd
    skill = re.sub(r"[^\w\s\.\+#/]", " ", skill)
    skill = re.sub(r"\s+", " ", skill).strip()

    skill = apply_synonym(skill)
    skill = normalize_skill_from_config(skill)

    if not is_valid_skill(skill):
        return ""

    return skill.strip()


def process_job_title(text: str) -> str:
    if not isinstance(text, str):
        return ""

    text = text.lower()

    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = apply_synonym(text)

    if not text or text in NOT_JOB_TITLE:
        return ""

    if len(text.split()) == 1 and text not in VALID_SINGLE_WORD:
        return ""

    return text


def normalize_location(location: str) -> str:
    location = str(location).lower().strip()

    if not location or location in ["nan", "none", "null"]:
        return "other"

    if "remote" in location:
        return "remote"

    if (
        "vietnam" in location
        or "viet nam" in location
        or "hanoi" in location
        or "ha noi" in location
        or "ho chi minh" in location
        or "hcm" in location
    ):
        return "vietnam"

    if (
        "united states" in location
        or "usa" in location
        or "u.s." in location
        or location == "us"
        or "new york" in location
        or "california" in location
        or "texas" in location
    ):
        return "united states"

    return location