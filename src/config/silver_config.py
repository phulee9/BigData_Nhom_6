# =========================================================
# Text cleaning config
# =========================================================

TITLE_REMOVE_PHRASES = [
    "urgent hiring",
    "immediate hiring",
    "we are hiring",
    "now hiring",
    "apply now",
    "job opening",
    "vacancy",
]


TITLE_REPLACEMENTS = {
    "sr": "senior",
    "jr": "junior",
    "wfh": "remote",
    "bi": "business intelligence",
    "ml": "machine learning",
    "dev": "developer",
    "eng": "engineer",
    "mgr": "manager",
}


TECH_REPLACEMENTS = {
    "c++": "cplusplus",
    "c#": "csharp",
    ".net": "dotnet",
    "node.js": "nodejs",
    "react.js": "reactjs",
    "vue.js": "vuejs",
}


# =========================================================
# Title processing config
# =========================================================

SENIORITY_KEYWORDS = {
    "intern": "intern",
    "internship": "intern",
    "trainee": "intern",

    "junior": "junior",
    "jr": "junior",
    "entry": "entry",

    "mid": "middle",
    "middle": "middle",

    "senior": "senior",
    "sr": "senior",

    "lead": "lead",
    "principal": "principal",
    "staff": "staff",

    "manager": "manager",
    "director": "director",
    "head": "head",
    "vp": "vp",
    "vice president": "vp",
}


WORK_MODE_KEYWORDS = {
    "remote": "remote",
    "hybrid": "hybrid",
    "onsite": "onsite",
    "on site": "onsite",
    "work from home": "remote",
    "wfh": "remote",
}


EMPLOYMENT_TYPE_KEYWORDS = {
    "full time": "full_time",
    "fulltime": "full_time",
    "part time": "part_time",
    "parttime": "part_time",
    "contract": "contract",
    "temporary": "temporary",
    "temp": "temporary",
    "internship": "internship",
    "freelance": "freelance",
}


TITLE_REMOVE_TOKENS = {
    "remote",
    "hybrid",
    "onsite",
    "contract",
    "temporary",
    "temp",
    "fulltime",
    "parttime",
    "full",
    "part",
    "time",
    "internship",
    "freelance",
}


# =========================================================
# Silver config
# =========================================================

SKILL_MAPPING_FILE = "data/mapping/skill_alias_mapping.csv"


JOB_POSTING_COLUMNS = [
    "job_link",
    "job_title",
    "company",
    "job_location",
    "search_city",
    "search_country",
    "first_seen",
]


JOB_SKILL_COLUMNS = [
    "job_link",
    "job_skills",
]


SILVER_COLUMNS = [
    "job_id",
    "job_link",
    "company",
    "location_raw",
    "search_city",
    "search_country",
    "first_seen",

    "title_raw",
    "title_clean",
    "title_lemma",
    "title_core",
    "seniority",
    "work_mode",
    "employment_type",

    "skills_raw",
    "skills_clean",
    "skills_normalized",
]


# =========================================================
# Skill candidate config
# =========================================================

SHORT_SKILL_WHITELIST = {
    "r",
    "c",
    "go",
    "qa",
    "ui",
    "ux",
    "bi",
    "hr",
}

SKILL_NOISE_PHRASES = [
    "equal opportunity",
    "job description",
    "benefits",
    "salary",
    "must be able",
    "ability to",
    "fast paced environment",
    "work independently",
    "reliable transportation",
    "background check",
    "drug test",
]