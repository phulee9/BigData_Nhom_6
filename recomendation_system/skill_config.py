SKILL_NORMALIZE = {
    # ── Node ──────────────────────────────────────────
    "node.js"   : "node",
    "nodejs"    : "node",
    "node js"   : "node",

    # ── React ─────────────────────────────────────────
    "react.js"  : "react",
    "reactjs"   : "react",

    # ── Vue ───────────────────────────────────────────
    "vue.js"    : "vue",
    "vuejs"     : "vue",

    # ── Next ──────────────────────────────────────────
    "next.js"   : "next",
    "nextjs"    : "next",

    # ── Nuxt ──────────────────────────────────────────
    "nuxt.js"   : "nuxt",
    "nuxtjs"    : "nuxt",

    # ── Express ───────────────────────────────────────
    "express.js": "express",
    "expressjs" : "express",

    # ── Angular ───────────────────────────────────────
    "angular.js": "angular",
    "angularjs" : "angular",

    # ── NestJS ────────────────────────────────────────
    "nest.js"   : "nestjs",

    # ── TypeScript ────────────────────────────────────
    "typescript": "typescript",
    "ts"        : "typescript",

    # ── JavaScript ────────────────────────────────────
    "javascript": "javascript",
    "js"        : "javascript",

    # ── Python ────────────────────────────────────────
    "python3"   : "python",
    "python 2"  : "python",
    "python 3"  : "python",

    # ── Database ──────────────────────────────────────
    "postgresql"       : "postgres",
    "mongo"            : "mongodb",
    "mongo db"         : "mongodb",
    "microsoft sql server": "sql server",
    "ms sql"           : "sql server",
    "mssql"            : "sql server",

    # ── Cloud ─────────────────────────────────────────
    "amazon web services"  : "aws",
    "google cloud"         : "gcp",
    "google cloud platform": "gcp",
    "microsoft azure"      : "azure",

    # ── REST ──────────────────────────────────────────
    "rest api"    : "rest api",
    "rest apis"   : "rest api",
    "restful"     : "rest api",
    "restful api" : "rest api",
    "restful apis": "rest api",

    # ── CI/CD ─────────────────────────────────────────
    "ci/cd" : "cicd",
    "ci cd" : "cicd",

    # ── ML/AI ─────────────────────────────────────────
    "ml"                        : "machine learning",
    "dl"                        : "deep learning",
    "ai"                        : "artificial intelligence",
    "nlp"                       : "natural language processing",
    "cv"                        : "computer vision",
    "machine learning"          : "machine learning",
    "deep learning"             : "deep learning",

    # ── .NET ──────────────────────────────────────────
    ".net"  : "dotnet",
    "net"   : "dotnet",

    # ── Power BI ──────────────────────────────────────
    "power bi"                   : "power bi",
    "powerbi"                    : "power bi",
    "microsoft power bi"         : "power bi",
    "power business intelligence": "power bi",

    # ── Kubernetes ────────────────────────────────────
    "k8s": "kubernetes",

    # ── Spring ────────────────────────────────────────
    "springboot"  : "spring boot",
    "spring-boot" : "spring boot",

    # ── Statistics ────────────────────────────────────
    "statistic"   : "statistics",
    "statistical" : "statistics",

    # ── DevOps ────────────────────────────────────────
    "terraform"    : "terraform",
    "ansible"      : "ansible",
    "jenkins"      : "jenkins",

    # Excel
    "microsoft excel" : "excel",
}


SKILL_BLACKLIST = {
    # ── Ký tự đơn vô nghĩa ────────────────────────────
    "j", "k", "m", "n", "p", "q", "s", "t",
    "x", "y", "z", "a", "b", "d", "e", "f",
    "w", "h", "l", "o", "u", "v",

    # ── Mô tả công việc ───────────────────────────────
    "data analysis",
    "marketing",
    "data extraction",
    "data extraction",
    "data visualization",
    "data analytics",
    "data management",
    "data processing",
    "data collection",
    "data entry",
    "data quality",
    "data modeling",
    "data mining",
    "data reporting",
    "back end development",
    "front end development",
    "full stack development",
    "software development",
    "web development",
    "mobile development",
    "application development",
    "game development",
    "full stack",
    "back end",
    "front end",
    "reporting",
    "report",
    "reports",
    "analysis",
    "analytics",
    "research",
    "planning",
    "strategy",
    "implementation",
    "documentation",
    "testing",
    "monitoring",

    # ── Tên ngành/vị trí ──────────────────────────────
    "data science",
    "data engineering",
    "data analyst",
    "data scientist",
    "data interpretation",
    "software engineer",
    "data engineer",
    "business analyst",
    "product manager",
    "project manager",
    "machine learning engineering",
    "computer science",
    "information technology",
    "information system",

    # ── Quá chung chung ───────────────────────────────
    "development",
    "programming",
    "experience",
    "knowledge",
    "ability",
    "skill",
    "skills",
    "work",
    "working",
    "strong",
    "good",
    "excellent",
    "proficient",
    "familiar",
    "understanding",
    "basic",
    "advanced",
    "software",
    "computer",
    "technology",
    "system",
    "systems",
    "application",
    "service",
    "services",
    "platform",
    "framework",
    "frameworks",
    "tool",
    "tools",

    # ── Soft skills ───────────────────────────────────
    "communication",
    "communication skill",
    "communication skills",
    "verbal communication",
    "written communication",
    "teamwork",
    "team work",
    "leadership",
    "management",
    "organization",
    "analytical",
    "analytical skill",
    "analytical skills",
    "analytical thinking",
    "problem solving",
    "time management",
    "critical thinking",
    "attention to detail",
    "interpersonal skill",
    "interpersonal skills",
    "organizational skill",
    "organizational skills",
    "presentation",
    "presentation skill",
    "presentation skills",
    "writing skill",
    "writing skills",
    "collaboration",
    "adaptability",
    "creativity",
    "self motivation",
    "detail oriented",
    "multitasking",
    "fast learner",
    "business intelligence",
    "business analysis",
    "project management",
}


def normalize_skill(skill: str) -> str:
    """Normalize skill về dạng chuẩn"""
    s = skill.lower().strip()

    # Thử map trực tiếp
    if s in SKILL_NORMALIZE:
        return SKILL_NORMALIZE[s]

    # Thử bỏ dấu chấm rồi map
    s_no_dot = s.replace(".", "")
    if s_no_dot in SKILL_NORMALIZE:
        return SKILL_NORMALIZE[s_no_dot]

    return s


def is_valid_skill(skill: str) -> bool:
    """Kiểm tra skill có hợp lệ không"""
    s      = skill.lower().strip()
    s_norm = normalize_skill(s)

    # Rỗng
    if not s_norm:
        return False

    # Ký tự đơn
    if len(s_norm) == 1:
        return False

    # Chỉ là số
    if s_norm.isdigit():
        return False

    # Trong blacklist (check cả trước và sau normalize)
    if s in SKILL_BLACKLIST:
        return False
    if s_norm in SKILL_BLACKLIST:
        return False

    return True