import re
import nltk
import spacy
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

# ── Setup NLTK ─────────────────────────────────────────
for pkg in ["wordnet", "omw-1.4", "stopwords"]:
    try:
        nltk.data.find(f"corpora/{pkg}")
    except:
        nltk.download(pkg, quiet=True)

# ── Setup spaCy ────────────────────────────────────────
try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    from spacy.cli import download
    download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

lemmatizer = WordNetLemmatizer()
STOP_WORDS  = set(stopwords.words("english"))

SYNONYM_MAP = {
    "sr": "senior", "jr": "junior", "mid": "mid",
    "lead": "senior", "principal": "senior", "staff": "senior",
    "intern": "intern", "trainee": "junior",
    "mgr": "manager", "mngr": "manager", "dir": "director",
    "vp": "vice president", "svp": "senior vice president",
    "assoc": "associate", "asst": "assistant",
    "rep": "representative", "exec": "executive",
    "admin": "administrator",
    "dev": "developer", "eng": "engineer",
    "swe": "software engineer",
    "frontend": "front end", "backend": "back end",
    "fullstack": "full stack", "full-stack": "full stack",
    "qa": "quality assurance",
    "sdet": "software development engineer in test",
    "ml": "machine learning", "ai": "artificial intelligence",
    "ds": "data scientist", "de": "data engineer",
    "fe": "front end", "be": "back end",
    "analyst": "analyst", "analytics": "analyst",
    "bi": "business intelligence",
    "biz": "business", "bd": "business development",
    "ba": "business analyst", "pm": "project manager",
    "pdm": "product manager", "ae": "account executive",
    "am": "account manager",
    "mkt": "marketing", "seo": "search engine optimization",
    "sem": "search engine marketing",
    "hr": "human resources",
    "hrbp": "human resources business partner",
    "cs": "customer service",
    "csr": "customer service representative",
    "rn": "registered nurse", "lpn": "licensed practical nurse",
    "np": "nurse practitioner", "pa": "physician assistant",
    "md": "medical doctor",
    "ops": "operations", "coo": "chief operating officer",
    "cto": "chief technology officer",
    "ceo": "chief executive officer",
    "&": "and", "/": " ",
    "pt": "part time", "ft": "full time",
}

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
    "coordinator", "administrator", "director", "officer"
}

NOISE_PATTERNS = [
    r'\b(remote|hybrid|onsite|on.site)\b',
    r'\b(part.time|full.time|contract|temp|temporary)\b',
    r'\b(urgent|immediate|opening|opportunity|hiring|wanted)\b',
    r'\b(vietnam|ho chi minh|hanoi|da nang|singapore|'
    r'london|new york|california|texas|florida|'
    r'chicago|boston|seattle|austin)\b',
    r'\b(f/m/d|m/f/d|w/m/d|m/w/d)\b',
    r'\b\d+\+?\s*(year|yr|month|week)s?\b',
    r'[-|\\]+.*$',
    r'\(.*?\)',
    r'\[.*?\]',
]


def process_job_title(text: str) -> str:
    """spaCy NER xóa ORG/GPE/LOC + synonym + lemmatize"""
    if not isinstance(text, str):
        return ""

    # 1. spaCy NER
    doc = nlp(text.strip())
    remove_spans = [
        (ent.start_char, ent.end_char)
        for ent in doc.ents
        if ent.label_ in ["ORG", "GPE", "LOC", "NORP"]
    ]
    for start, end in sorted(remove_spans, reverse=True):
        text = text[:start] + " " + text[end:]

    # 2. Lowercase + noise patterns
    text = text.lower()
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    # 3. Bỏ ký tự đặc biệt
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # 4. Synonym
    for k, v in SYNONYM_MAP.items():
        text = re.sub(rf"\b{k}\b", v, text)

    # 5. Stopword + lemmatize
    tokens     = [w for w in text.split() if w not in STOP_WORDS]
    lemmatized = [lemmatizer.lemmatize(w) for w in tokens]
    text       = " ".join(lemmatized).strip()

    # 6. Filter
    if not text or text in NOT_JOB_TITLE:
        return ""
    if len(text.split()) == 1 and text not in VALID_SINGLE_WORD:
        return ""

    return text


def process_job_skills(text: str, max_words: int = 5) -> str:
    """Regex + synonym + lemmatize (không cần spaCy)"""
    if not isinstance(text, str):
        return ""

    # 1. Chuẩn hóa dấu
    text = text.replace(".", ",").replace(";", ",")
    text = re.sub(r",+", ",", text)

    # 2. Lowercase + bỏ ký tự đặc biệt
    text = text.lower()
    text = re.sub(r"[^\w\s,]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # 3. Tách phrases + dedup
    phrases = list(dict.fromkeys([
        p.strip() for p in text.split(",") if p.strip()
    ]))

    # 4. Xử lý từng phrase
    cleaned = []
    for phrase in phrases:
        for k, v in SYNONYM_MAP.items():
            phrase = re.sub(rf"\b{k}\b", v, phrase)
        tokens     = [w for w in phrase.split() if w not in STOP_WORDS]
        lemmatized = [lemmatizer.lemmatize(w) for w in tokens]
        if 0 < len(lemmatized) <= max_words:
            cleaned.append(" ".join(lemmatized))

    return ", ".join(dict.fromkeys(cleaned)).strip(", ")


def process_row(row: dict) -> tuple:
    """Wrapper cho multiprocessing"""
    return (
        process_job_title(row["job_title"]),
        process_job_skills(row["job_skills"])
    )