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
    "hà nội": "hanoi",
    "hanoi": "hanoi",

    "ho chi minh": "ho chi minh",
    "hồ chí minh": "ho chi minh",
    "ho chi minh city": "ho chi minh",
    "hồ chí minh city": "ho chi minh",
    "hồ chí minh": "ho chi minh",
    "hcm": "ho chi minh",
    "hcmc": "ho chi minh",
    "sai gon": "ho chi minh",
    "sài gòn": "ho chi minh",
    "saigon": "ho chi minh",

    "hai phong": "hai phong",
    "hải phòng": "hai phong",
    "haiphong": "hai phong",

    "da nang": "da nang",
    "đà nẵng": "da nang",
    "danang": "da nang",

    "can tho": "can tho",
    "cần thơ": "can tho",
    "cantho": "can tho",

    # Northern provinces
    "ha giang": "ha giang",
    "hà giang": "ha giang",

    "cao bang": "cao bang",
    "cao bằng": "cao bang",

    "bac kan": "bac kan",
    "bắc kạn": "bac kan",

    "tuyen quang": "tuyen quang",
    "tuyên quang": "tuyen quang",

    "lao cai": "lao cai",
    "lào cai": "lao cai",

    "dien bien": "dien bien",
    "điện biên": "dien bien",

    "lai chau": "lai chau",
    "lai châu": "lai chau",

    "son la": "son la",
    "sơn la": "son la",

    "yen bai": "yen bai",
    "yên bái": "yen bai",

    "hoa binh": "hoa binh",
    "hòa bình": "hoa binh",

    "thai nguyen": "thai nguyen",
    "thái nguyên": "thai nguyen",

    "lang son": "lang son",
    "lạng sơn": "lang son",

    "quang ninh": "quang ninh",
    "quảng ninh": "quang ninh",

    "bac giang": "bac giang",
    "bắc giang": "bac giang",

    "phu tho": "phu tho",
    "phú thọ": "phu tho",

    "vinh phuc": "vinh phuc",
    "vĩnh phúc": "vinh phuc",

    "bac ninh": "bac ninh",
    "bắc ninh": "bac ninh",

    # Red River Delta
    "hai duong": "hai duong",
    "hải dương": "hai duong",

    "hung yen": "hung yen",
    "hưng yên": "hung yen",

    "thai binh": "thai binh",
    "thái bình": "thai binh",

    "ha nam": "ha nam",
    "hà nam": "ha nam",

    "nam dinh": "nam dinh",
    "nam định": "nam dinh",

    "ninh binh": "ninh binh",
    "ninh bình": "ninh binh",

    # North Central and Central Coast
    "thanh hoa": "thanh hoa",
    "thanh hóa": "thanh hoa",
    "thanh hoá": "thanh hoa",

    "nghe an": "nghe an",
    "nghệ an": "nghe an",

    "ha tinh": "ha tinh",
    "hà tĩnh": "ha tinh",

    "quang binh": "quang binh",
    "quảng bình": "quang binh",

    "quang tri": "quang tri",
    "quảng trị": "quang tri",

    "thua thien hue": "thua thien hue",
    "thừa thiên huế": "thua thien hue",
    "hue": "thua thien hue",
    "huế": "thua thien hue",

    "quang nam": "quang nam",
    "quảng nam": "quang nam",

    "quang ngai": "quang ngai",
    "quảng ngãi": "quang ngai",

    "binh dinh": "binh dinh",
    "bình định": "binh dinh",

    "phu yen": "phu yen",
    "phú yên": "phu yen",

    "khanh hoa": "khanh hoa",
    "khánh hòa": "khanh hoa",
    "khánh hoà": "khanh hoa",

    "ninh thuan": "ninh thuan",
    "ninh thuận": "ninh thuan",

    "binh thuan": "binh thuan",
    "bình thuận": "binh thuan",

    # Central Highlands
    "kon tum": "kon tum",

    "gia lai": "gia lai",

    "dak lak": "dak lak",
    "đắk lắk": "dak lak",
    "đắc lắc": "dak lak",

    "dak nong": "dak nong",
    "đắk nông": "dak nong",
    "đắc nông": "dak nong",

    "lam dong": "lam dong",
    "lâm đồng": "lam dong",

    # Southeast
    "binh phuoc": "binh phuoc",
    "bình phước": "binh phuoc",

    "tay ninh": "tay ninh",
    "tây ninh": "tay ninh",

    "binh duong": "binh duong",
    "bình dương": "binh duong",

    "dong nai": "dong nai",
    "đồng nai": "dong nai",

    "ba ria vung tau": "ba ria vung tau",
    "bà rịa vũng tàu": "ba ria vung tau",
    "ba ria - vung tau": "ba ria vung tau",
    "bà rịa - vũng tàu": "ba ria vung tau",
    "vung tau": "ba ria vung tau",
    "vũng tàu": "ba ria vung tau",

    # Mekong Delta
    "long an": "long an",

    "tien giang": "tien giang",
    "tiền giang": "tien giang",

    "ben tre": "ben tre",
    "bến tre": "ben tre",

    "tra vinh": "tra vinh",
    "trà vinh": "tra vinh",

    "vinh long": "vinh long",
    "vĩnh long": "vinh long",

    "dong thap": "dong thap",
    "đồng tháp": "dong thap",

    "an giang": "an giang",

    "kien giang": "kien giang",
    "kiên giang": "kien giang",

    "hau giang": "hau giang",
    "hậu giang": "hau giang",

    "soc trang": "soc trang",
    "sóc trăng": "soc trang",

    "bac lieu": "bac lieu",
    "bạc liêu": "bac lieu",

    "ca mau": "ca mau",
    "cà mau": "ca mau",

    # Generic
    "vietnam": "vietnam",
    "viet nam": "vietnam",
    "việt nam": "vietnam",
}