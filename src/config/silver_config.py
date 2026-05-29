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

CITY_ALIASES = {
    # Centrally governed cities
    "ha noi": "hanoi",
    "hanoi": "hanoi",

    "ho chi minh": "ho chi minh",
    "ho chi minh city": "ho chi minh",
    "hcm": "ho chi minh",
    "hcmc": "ho chi minh",
    "sai gon": "ho chi minh",
    "saigon": "ho chi minh",

    "hai phong": "hai phong",
    "haiphong": "hai phong",

    "da nang": "da nang",
    "danang": "da nang",

    "can tho": "can tho",
    "cantho": "can tho",

    # Northern provinces
    "ha giang": "ha giang",
    "cao bang": "cao bang",
    "bac kan": "bac kan",
    "tuyen quang": "tuyen quang",
    "lao cai": "lao cai",
    "dien bien": "dien bien",
    "lai chau": "lai chau",
    "son la": "son la",
    "yen bai": "yen bai",
    "hoa binh": "hoa binh",
    "thai nguyen": "thai nguyen",
    "lang son": "lang son",
    "quang ninh": "quang ninh",
    "bac giang": "bac giang",
    "phu tho": "phu tho",
    "vinh phuc": "vinh phuc",
    "bac ninh": "bac ninh",

    # Red River Delta
    "hai duong": "hai duong",
    "hung yen": "hung yen",
    "thai binh": "thai binh",
    "ha nam": "ha nam",
    "nam dinh": "nam dinh",
    "ninh binh": "ninh binh",

    # North Central and Central Coast
    "thanh hoa": "thanh hoa",
    "nghe an": "nghe an",
    "ha tinh": "ha tinh",
    "quang binh": "quang binh",
    "quang tri": "quang tri",
    "thua thien hue": "thua thien hue",
    "hue": "thua thien hue",
    "quang nam": "quang nam",
    "quang ngai": "quang ngai",
    "binh dinh": "binh dinh",
    "phu yen": "phu yen",
    "khanh hoa": "khanh hoa",
    "ninh thuan": "ninh thuan",
    "binh thuan": "binh thuan",

    # Central Highlands
    "kon tum": "kon tum",
    "gia lai": "gia lai",
    "dak lak": "dak lak",
    "dak nong": "dak nong",
    "lam dong": "lam dong",

    # Southeast
    "binh phuoc": "binh phuoc",
    "tay ninh": "tay ninh",
    "binh duong": "binh duong",
    "dong nai": "dong nai",
    "ba ria vung tau": "ba ria vung tau",
    "ba ria - vung tau": "ba ria vung tau",
    "vung tau": "ba ria vung tau",

    # Mekong Delta
    "long an": "long an",
    "tien giang": "tien giang",
    "ben tre": "ben tre",
    "tra vinh": "tra vinh",
    "vinh long": "vinh long",
    "dong thap": "dong thap",
    "an giang": "an giang",
    "kien giang": "kien giang",
    "hau giang": "hau giang",
    "soc trang": "soc trang",
    "bac lieu": "bac lieu",
    "ca mau": "ca mau",

    # Generic
    "vietnam": "vietnam",
    "viet nam": "vietnam",
}