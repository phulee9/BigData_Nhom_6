import re
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
import spacy
from spacy.cli import download
import re

try:
    nlp = spacy.load("en_core_web_lg")
except OSError:
    print("Model en_core_web_lg chưa có, đang tải...")
    download("en_core_web_lg")
    nlp = spacy.load("en_core_web_lg")

for pkg in ['wordnet', 'omw-1.4', 'stopwords']:
    try:
        nltk.data.find(f'corpora/{pkg}')
    except:
        nltk.download(pkg)

lemmatizer = WordNetLemmatizer()
STOP_WORDS = set(stopwords.words('english'))

SYNONYM_MAP = {
    # ===== LEVEL =====
    "sr": "senior",
    "jr": "junior",
    "mid": "mid",
    "lead": "senior",
    "principal": "senior",
    "staff": "senior",
    "intern": "intern",
    "trainee": "junior",

    # ===== ROLE COMMON =====
    "mgr": "manager",
    "mngr": "manager",
    "dir": "director",
    "vp": "vice president",
    "svp": "senior vice president",
    "assoc": "associate",
    "asst": "assistant",
    "rep": "representative",
    "exec": "executive",
    "officer": "officer",
    "admin": "administrator",

    # ===== TECH =====
    "dev": "developer",
    "eng": "engineer",
    "swe": "software engineer",
    "frontend": "front end",
    "backend": "back end",
    "fullstack": "full stack",
    "full-stack": "full stack",
    "qa": "quality assurance",
    "sdet": "software development engineer in test",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "ds": "data scientist",
    "de": "data engineer",
    "fe": "front end",
    "be": "back end",

    # ===== DATA =====
    "analyst": "analyst",
    "analytics": "analyst",
    "bi": "business intelligence",
    "data analyst": "data analyst",
    "data analytics": "data analyst",

    # ===== BUSINESS =====
    "biz": "business",
    "bd": "business development",
    "bdr": "business development representative",
    "ba": "business analyst",
    "pm": "project manager",
    "pdm": "product manager",

    # ===== SALES =====
    "ae": "account executive",
    "am": "account manager",
    "sales rep": "sales representative",
    "salesperson": "sales representative",

    # ===== MARKETING =====
    "mkt": "marketing",
    "seo": "search engine optimization",
    "sem": "search engine marketing",
    "smm": "social media marketing",

    # ===== FINANCE =====
    "acct": "accountant",
    "acc": "accountant",
    "cpa": "certified public accountant",
    "fp&a": "financial planning analysis",

    # ===== HR =====
    "hr": "human resources",
    "hrbp": "human resources business partner",
    "recruiter": "recruiter",
    "talent": "talent acquisition",

    # ===== HEALTHCARE =====
    "rn": "registered nurse",
    "lpn": "licensed practical nurse",
    "np": "nurse practitioner",
    "pa": "physician assistant",
    "md": "medical doctor",
    "dr": "doctor",

    # ===== ENGINEERING (NON-IT) =====
    "mech": "mechanical",
    "elec": "electrical",
    "civil": "civil",
    "arch": "architect",
    "tech": "technician",

    # ===== OPERATIONS =====
    "ops": "operations",
    "coo": "chief operating officer",
    "logistics": "logistics",
    "supply chain": "supply chain",

    # ===== EDUCATION =====
    "prof": "professor",
    "lect": "lecturer",
    "ta": "teaching assistant",

    # ===== CUSTOMER =====
    "cs": "customer service",
    "csr": "customer service representative",
    "support": "support",

    # ===== GENERIC CLEAN =====
    "&": "and",
    "/": " ",
    "pt":'part time',
    'ft':'full time',
}

def dedup_text(text):
    phrases = [p.strip() for p in text.split(',') if p.strip()]
    return ', '.join(dict.fromkeys(phrases))


def cut_noise(text, max_words_per_phrase=5):
    # normalize dấu
    text = text.replace('.', ',').replace(';', ',')
    text = re.sub(r',+', ',', text) 
    
    phrases = [p.strip() for p in text.split(',') if p.strip()]
    
    phrases = [p for p in phrases if len(p.split()) <= max_words_per_phrase]
    
    return ', '.join(phrases)

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)  
    text = " ".join(text.split())
    return text

def remove_stop_words(text, stop_words=None):
    if stop_words is None or len(stop_words) == 0:
        stop_words = STOP_WORDS
    
    tokens = text.split()
    tokens = [w for w in tokens if w not in stop_words]
    
    return " ".join(tokens)

def lemmatize(text):
    return " ".join(lemmatizer.lemmatize(w) for w in text.split())

def normalize_synonym_phrase(text):
    for k, v in SYNONYM_MAP.items():
        text = re.sub(rf"\b{k}\b", v, text)
    return text
    
def remove_org_loc(text):
    """
    Remove ORG và location (GPE, LOC) bằng spaCy NER
    """
    doc = nlp(text)
    remove_spans = [(ent.start_char, ent.end_char) for ent in doc.ents if ent.label_ in ["ORG", "GPE", "LOC"]]

    for start, end in sorted(remove_spans, reverse=True):
        text = text[:start] + text[end:]
    return ' '.join(text.split())
    
def clean_text(text, max_words_per_phrase=5):
    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = re.sub(r"[/&\-]", " ", text)  # convert / & - → space
    text = re.sub(r"[^\w\s,]", " ", text)  # loại ký tự đặc biệt khác
    text = re.sub(r'\s+', ' ', text).strip()

    phrases = [p.strip() for p in text.split(',') if p.strip()]

    cleaned_phrases = []
    for phrase in phrases:
        for k, v in SYNONYM_MAP.items():
            phrase = re.sub(rf"\b{k}\b", v, phrase)

        tokens = [w for w in phrase.split() if w not in STOP_WORDS]
        if not tokens:
            continue

        lemmatized = [lemmatizer.lemmatize(w) for w in tokens]

        if len(lemmatized) <= max_words_per_phrase:
            cleaned_phrases.append(' '.join(lemmatized))

    dedup_phrases = list(dict.fromkeys(cleaned_phrases))

    return ', '.join(dedup_phrases).strip(', ')