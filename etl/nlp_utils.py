import re
import json
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from pathlib import Path

# Setup NLTK
for pkg in ["wordnet", "omw-1.4", "stopwords"]:
    try:
        nltk.data.find(f"corpora/{pkg}")
    except Exception:
        nltk.download(pkg, quiet=True)

lemmatizer = WordNetLemmatizer()
STOP_WORDS = set(stopwords.words("english"))

# Đường dẫn whitelist
WHITELIST_PATH = Path(__file__).parent.parent / "recommendation" / "data" / "skill_whitelist.json"

# Bảng synonym chuẩn hóa job_title và job_skills
SYNONYM_MAP = {
    # Cấp bậc
    "sr": "senior", "jr": "junior", "mid": "mid",
    "lead": "senior", "principal": "senior",
    "intern": "intern", "trainee": "junior",
    # Chức danh
    "mgr": "manager", "mngr": "manager",
    "dir": "director", "vp": "vice president",
    "assoc": "associate", "asst": "assistant",
    "rep": "representative", "exec": "executive",
    "admin": "administrator",
    # Kỹ thuật
    "dev": "developer", "eng": "engineer",
    "swe": "software engineer",
    "frontend": "front end", "backend": "back end",
    "fullstack": "full stack", "full-stack": "full stack",
    "qa": "quality assurance",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "ds": "data scientist", "de": "data engineer",
    "fe": "front end", "be": "back end",
    # Kinh doanh
    "bi": "business intelligence",
    "biz": "business", "bd": "business development",
    "ba": "business analyst", "pm": "project manager",
    # Khác
    "hr": "human resources",
    "cs": "customer service",
    "ae": "account executive",
    "am": "account manager",
    "mkt": "marketing",
    "seo": "search engine optimization",
    "rn": "registered nurse",
    "lpn": "licensed practical nurse",
    "np": "nurse practitioner",
    "md": "medical doctor",
    "ops": "operations",
    "coo": "chief operating officer",
    "cto": "chief technology officer",
    "ceo": "chief executive officer",
    "&": "and", "/": " ",
    "pt": "part time", "ft": "full time",
}

# Patterns loại bỏ noise trong job_title
NOISE_PATTERNS = [
    r'\b(remote|hybrid|onsite|on.site)\b',
    r'\b(part.time|full.time|contract|temp|temporary)\b',
    r'\b(urgent|immediate|opening|opportunity|hiring|wanted)\b',
    r'\b(vietnam|ho chi minh|hanoi|da nang|singapore|'
    r'london|new york|california|texas|florida|'
    r'chicago|boston|seattle|austin|canada|australia)\b',
    r'\b(f/m/d|m/f/d|w/m/d|m/w/d)\b',
    r'\b\d+\+?\s*(year|yr|month|week)s?\b',
    r'[-|\\]+.*$',
    r'\(.*?\)', r'\[.*?\]',
]

NOT_JOB_TITLE = {
    "compensation", "experience", "salary", "benefits",
    "remote", "hybrid", "travel", "unknown", "other",
    "na", "n/a", "none", "null", "opening", "opportunity",
    "position", "role", "job", "hiring", "wanted"
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


# Lazy load whitelist
_WHITELIST = None

def get_whitelist() -> set:
    global _WHITELIST
    if _WHITELIST is None:
        if WHITELIST_PATH.exists():
            with open(WHITELIST_PATH, "r", encoding="utf-8") as f:
                _WHITELIST = set(json.load(f))
            print(f"Loaded whitelist: {len(_WHITELIST):,} skills")
        else:
            _WHITELIST = set()
            print("Khong co whitelist, bo qua filter")
    return _WHITELIST


# Lazy load spaCy
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            from spacy.cli import download
            download("en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
    return _nlp


def process_job_title(text: str) -> str:
    if not isinstance(text, str):
        return ""

    # Dùng spaCy NER loại bỏ tên tổ chức, địa điểm
    nlp = get_nlp()
    doc = nlp(text.strip())
    remove_spans = [
        (ent.start_char, ent.end_char)
        for ent in doc.ents
        if ent.label_ in ["ORG", "GPE", "LOC", "NORP"]
    ]
    for start, end in sorted(remove_spans, reverse=True):
        text = text[:start] + " " + text[end:]

    # Lowercase và loại bỏ noise patterns
    text = text.lower()
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+",     " ", text).strip()

    # Chuẩn hóa synonym
    for k, v in SYNONYM_MAP.items():
        text = re.sub(rf"\b{k}\b", v, text)

    # Bỏ stopwords và lemmatize
    tokens = [w for w in text.split() if w not in STOP_WORDS]
    text   = " ".join(lemmatizer.lemmatize(w) for w in tokens).strip()

    if not text or text in NOT_JOB_TITLE:
        return ""
    if len(text.split()) == 1 and text not in VALID_SINGLE_WORD:
        return ""

    return text


def process_job_skills(text: str, max_words: int = 4) -> str:
    if not isinstance(text, str):
        return ""

    whitelist = get_whitelist()

    # Chuẩn hóa dấu phân cách
    text = text.replace(".", ",").replace(";", ",")
    text = re.sub(r",+", ",", text)
    text = text.lower()
    text = re.sub(r"[^\w\s,]", " ", text)
    text = re.sub(r"\s+",      " ", text).strip()

    # Tách thành phrases và dedup
    phrases = list(dict.fromkeys([p.strip() for p in text.split(",") if p.strip()]))

    cleaned = []
    for phrase in phrases:
        # Chuẩn hóa synonym
        for k, v in SYNONYM_MAP.items():
            phrase = re.sub(rf"\b{k}\b", v, phrase)

        # Bỏ stopwords và lemmatize
        tokens = [w for w in phrase.split() if w not in STOP_WORDS]
        lemmatized = [lemmatizer.lemmatize(w) for w in tokens]

        # Bỏ phrase rỗng hoặc quá dài
        if not lemmatized or len(lemmatized) > max_words:
            continue

        skill = " ".join(lemmatized)

        if len(skill) <= 1:
            continue

        # Filter theo whitelist nếu có
        if whitelist and skill not in whitelist:
            continue

        cleaned.append(skill)

    return ", ".join(dict.fromkeys(cleaned)).strip(", ")


def process_row(row: dict) -> tuple:
    # Wrapper cho multiprocessing
    return (
        process_job_title(row["job_title"]),
        process_job_skills(row["job_skills"])
    )