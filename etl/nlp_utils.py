import re
import json
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from pathlib import Path
from skill_config import normalize_skill

# Setup NLTK
for pkg in ["wordnet", "omw-1.4", "stopwords"]:
    try:
        nltk.data.find(f"corpora/{pkg}")
    except Exception:
        nltk.download(pkg, quiet=True)

lemmatizer = WordNetLemmatizer()
STOP_WORDS = set(stopwords.words("english"))

WHITELIST_PATH = Path(__file__).parent.parent / "recommendation" / "data" / "skill_whitelist.json"

SYNONYM_MAP = {
    # Cap bac
    "sr": "senior", "jr": "junior", "mid": "mid",
    "lead": "senior", "principal": "senior",
    "intern": "intern", "trainee": "junior",
    # Chuc danh
    "mgr": "manager", "mngr": "manager",
    "dir": "director", "vp": "vice president",
    "assoc": "associate", "asst": "assistant",
    "rep": "representative", "exec": "executive",
    "admin": "administrator",
    # Ky thuat
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
    # Khac
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

# Lazy load whitelist — chi doc file 1 lan
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


def reload_whitelist() -> set:
    # Reset cache va doc lai tu file
    # Dung sau khi update_whitelist() them skills moi
    global _WHITELIST
    _WHITELIST = None
    return get_whitelist()


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

    # Dung spaCy NER loai bo ten to chuc, dia diem
    nlp = get_nlp()
    doc = nlp(text.strip())
    remove_spans = [
        (ent.start_char, ent.end_char)
        for ent in doc.ents
        if ent.label_ in ["ORG", "GPE", "LOC", "NORP"]
    ]
    for start, end in sorted(remove_spans, reverse=True):
        text = text[:start] + " " + text[end:]

    # Lowercase va loai bo noise patterns
    text = text.lower()
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+",     " ", text).strip()

    # Chuan hoa synonym
    for k, v in SYNONYM_MAP.items():
        text = re.sub(rf"\b{k}\b", v, text)

    # Bo stopwords va lemmatize
    tokens = [w for w in text.split() if w not in STOP_WORDS]
    text   = " ".join(lemmatizer.lemmatize(w) for w in tokens).strip()

    if not text or text in NOT_JOB_TITLE:
        return ""
    if len(text.split()) == 1 and text not in VALID_SINGLE_WORD:
        return ""

    return text


def process_job_skills(
    text: str,
    max_words: int = 4,
    use_whitelist: bool = True
) -> str:
    if not isinstance(text, str):
        return ""

    # Lay whitelist neu can filter
    whitelist = get_whitelist() if use_whitelist else set()

    # Chuan hoa dau phan cach
    text = text.replace(".", ",").replace(";", ",")
    text = re.sub(r",+", ",", text)
    text = text.lower()
    text = re.sub(r"[^\w\s,]", " ", text)
    text = re.sub(r"\s+",      " ", text).strip()

    # Tach thanh phrases va dedup
    phrases = list(dict.fromkeys([
        p.strip() for p in text.split(",") if p.strip()
    ]))

    cleaned = []
    for phrase in phrases:
        # Chuan hoa synonym
        for k, v in SYNONYM_MAP.items():
            phrase = re.sub(rf"\b{k}\b", v, phrase)

        # Bo stopwords va lemmatize
        tokens     = [w for w in phrase.split() if w not in STOP_WORDS]
        lemmatized = [lemmatizer.lemmatize(w) for w in tokens]

        if not lemmatized or len(lemmatized) > max_words:
            continue

        skill = " ".join(lemmatized)

        if len(skill) <= 1:
            continue

        # Normalize truoc khi filter whitelist
        skill_norm = normalize_skill(skill)

        # Filter theo whitelist (dung normalized version)
        if use_whitelist and whitelist and skill_norm not in whitelist:
            continue

        # Luu normalized version
        cleaned.append(skill_norm)

    return ", ".join(dict.fromkeys(cleaned)).strip(", ")


def process_row(row: dict) -> tuple:
    # Dung cho bronze_to_silver.py
    # Clean ca title lan skills (co filter whitelist)
    return (
        process_job_title(row["job_title"]),
        process_job_skills(row["job_skills"], use_whitelist=True)
    )


def process_row_title_only(row: dict) -> tuple:
    # Dung cho bronze_to_silver_new.py
    # Chi clean title, giu nguyen skills tho
    # Skills se duoc validate + filter sau boi update_whitelist() va filter_skills()
    return (
        process_job_title(row["job_title"]),
        row["job_skills"]
    )