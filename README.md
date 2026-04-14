# 🚀 Skill Recommender - Dự án phân tích kỹ năng việc làm

Dự án tổng hợp dữ liệu việc làm từ LinkedIn, phân tích kỹ năng yêu cầu, đề xuất lộ trình học tập và hỗ trợ chuyển đổi sự nghiệp bằng AI.

---

## 📋 Mục lục

1. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
2. [Cài đặt ban đầu](#cài-đặt-ban-đầu)
3. [Chạy Backend](#chạy-backend)
4. [Chạy Frontend](#chạy-frontend)
5. [API Integration](#api-integration)
6. [Cấu hình](#cấu-hình)
7. [Luồng hoạt động](#luồng-hoạt-động)
8. [Các vấn đề thường gặp](#các-vấn-đề-thường-gặp)
9. [Cấu trúc dự án](#cấu-trúc-dự-án)
10. [Ghi chú](#ghi-chú)

---

## ⚙️ Yêu cầu hệ thống

- **Python 3.8+**
- **Node.js 16+** (với npm)
- **Docker** & **Docker Compose**
- Groq API Key (để sử dụng LLM)

---

## 🔧 Cài đặt ban đầu

### 1. Clone project từ GitHub

```bash
git clone <link-repository>
cd BigData_Nhom_6
```

### 2. Tạo môi trường Python (venv)

```bash
python3 -m venv venv
```

### 3. Kích hoạt môi trường ảo

**Linux / MacOS:**

```bash
source venv/bin/activate
```

**Windows:**

```bash
venv\Scripts\activate
```

Sau khi kích hoạt thành công terminal sẽ hiện:

```
(venv)
```

### 4. Cài đặt thư viện chung

```bash
pip install -r requirements.txt
```

### 5. Khởi động Kafka bằng Docker

```bash
docker compose up -d
```

Lệnh này sẽ chạy các container Kafka cần thiết.

---

## 🔙 Chạy Backend

### 1. Cài đặt dependencies Backend

```bash
cd recommendation
pip install -r requirements_backend.txt
```

### 2. Chạy server FastAPI

```bash
python server.py
```

**Output mong đợi:**

```
============================================================
  🚀 Starting Skill Recommender API Server
============================================================
  📍 Server: http://0.0.0.0:8000
  📖 Docs:   http://localhost:8000/docs
============================================================
```

Backend sẽ chạy tại: **http://localhost:8000**

---

## 🎨 Chạy Frontend

### 1. Cài đặt dependencies Frontend

```bash
cd front_end
npm install
```

### 2. Chạy dev server

```bash
npm run dev
```

Frontend sẽ chạy tại: **http://localhost:5173**

---

## 6️⃣ Chạy Producer (Kafka)

```bash
python producer.py
```

Producer sẽ gửi dữ liệu vào Kafka.

---

## 📡 API Integration

Frontend đã được cấu hình để gọi backend qua các endpoints:

### **1. Upload CV**

```javascript
// POST /api/upload-cv
const data = await uploadCVFile(file);
// Response: { vi_tri_ung_tuyen, skills, message }
```

### **2. Manual Input**

```javascript
// POST /api/manual-info
const data = await submitManualInfo(jobTitle, ['python', 'sql']);
// Response: { vi_tri_ung_tuyen, skills, message }
```

### **3. Get Skill Recommendations**

```javascript
// POST /api/recommend-skills
const result = await getSkillRecommendations(jobTitle, skills);
// Response: { skills_goi_y: [...], job_titles_gan_nhat, ... }
```

### **4. Get Skill Roadmap**

```javascript
// POST /api/skill-roadmap
const result = await getSkillRoadmap(jobTitle, skills);
// Response: { must_have: [...], should_have: [...], nice_have: [...] }
```

### **5. Career Switch Analysis**

```javascript
// POST /api/career-switch
const result = await getCareerAnalysis(jobFrom, jobTo, skills);
// Response: { match_pct, cv_match, need_to_learn, ... }
```

---

## 🔧 Cấu hình

### Environment Variables

**Frontend (.env)**

```
REACT_APP_API_URL=http://localhost:8000
```

**Backend (parent .env)**

```
GROQ_API_KEY=your_key_here
GROQ_API_KEY_1=your_key_here
```

---

## 📋 Luồng hoạt động

```
1. User mở Frontend (http://localhost:5173)
   ↓
2. User upload CV hoặc nhập thông tin manual
   ↓
3. Frontend gọi POST /api/upload-cv hoặc POST /api/manual-info
   ↓
4. Backend xử lý CV qua Groq LLM
   ↓
5. Frontend nhận { vi_tri_ung_tuyen, skills }
   ↓
6. User chọn loại phân tích (Skills / Roadmap / Career)
   ↓
7. Frontend gọi API endpoint tương ứng
   ↓
8. Backend dùng FAISS để tìm job tương tự
   ↓
9. Backend trả kết quả
   ↓
10. Frontend hiển thị kết quả cho user
```

---

## 🧪 Test API

Truy cập **http://localhost:8000/docs** để test các endpoints trong Swagger UI

---

## 📁 Cấu trúc dự án

```
BigData_Nhom_6/
├── recommendation/              # Backend FastAPI
│   ├── server.py               # Main FastAPI app
│   ├── app.py                  # App configuration
│   ├── models.py               # Pydantic schemas
│   ├── requirements_backend.txt # Backend dependencies
│   ├── routers/                # API routes
│   │   ├── cv_router.py
│   │   ├── recommendations_router.py
│   │   ├── career_router.py
│   │   └── roadmap_router.py
│   ├── core/                   # Business logic
│   │   ├── recommend.py
│   │   ├── roadmap.py
│   │   ├── career_switch.py
│   │   ├── loader.py
│   │   ├── models_cache.py
│   │   └── skill_config.py
│   ├── cv/                     # CV extraction
│   │   └── cv_extractor.py
│   └── data/                   # FAISS index + metadata
│       ├── faiss_index.bin
│       ├── job_metadata.pkl
│       ├── embeddings.npy
│       └── skill_whitelist.json
│
├── front_end/                  # Frontend React + Vite
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── hooks/              # Custom hooks
│   │   │   └── useCVAnalyzer.js
│   │   ├── utils/              # Utility functions
│   │   │   └── api.js          # API client
│   │   ├── components/         # React components
│   │   │   ├── common/
│   │   │   │   ├── Header.jsx
│   │   │   │   └── BackButton.jsx
│   │   │   └── steps/
│   │   │       ├── UploadStep.jsx
│   │   │       ├── UploadStep.jsx
│   │   │       ├── AnalyzeStep.jsx
│   │   │       ├── OptionsStep.jsx
│   │   │       └── ResultStep.jsx
│   │   ├── constants/          # Mock data
│   │   │   └── mockData.js
│   │   └── styles/            # CSS files
│   │       ├── index.css
│   │       └── styles.js
│   ├── package.json
│   ├── vite.config.js
│   └── .env                   # Environment config
│
├── etl/                        # Data processing scripts
│   ├── bronze_to_silver.py
│   ├── silver_to_gold.py
│   ├── update_silver.py
│   ├── build_skill_whitelist.py
│   └── nlp_utils.py
│
├── scraper/                    # Web scraper
│   ├── crawler.py
│   ├── crawl_monster/
│   │   ├── crawler_all.py
│   │   └── monster_jobs_with_skills_chunk_1.json
│   └── utils/
│       ├── check_job_exists.py
│       ├── now_time.py
│       └── save_csv.py
│
├── producer/                   # Kafka producer
│   └── kafkal_producer.py
│
├── storage/                    # Storage utilities
│   ├── create_bucket.py
│   └── upload_bronze.py
│
├── data/                       # Raw data files
│   ├── job_skills.csv
│   ├── job_summary.csv
│   └── linkedin_job_postings.csv
│
├── api/                        # API utilities
├── docs/                       # Documentation
├── docker-compose.yml          # Docker configuration
├── requirements.txt            # Python dependencies
├── .env                        # Root environment config
├── INTEGRATION_GUIDE.md        # Integration guide
└── README.md                   # This file
```

---

## ❌ Các vấn đề thường gặp

### Backend port 8000 đã được sử dụng

```bash
netstat -ano | findstr :8000  # Tìm process
taskkill /PID <PID> /F        # Kill process
```

### Frontend không kết nối được backend

- Kiểm tra `.env` trong `front_end/`: `REACT_APP_API_URL=http://localhost:8000`
- Khởi động lại dev server sau khi thay đổi `.env`

### Lỗi CORS

Backend đã bật CORS cho tất cả origins (`*`). Hãy thay đổi trong production.

### Lỗi Groq API

Đảm bảo `GROQ_API_KEY` được set trong root `.env`

### Docker container không chạy

```bash
# Kiểm tra trạng thái
docker compose ps

# Xem logs
docker compose logs -f

# Restart
docker compose restart
```

### Lỗi thư viện Python

```bash
# Cài lại dependencies
pip install -r requirements.txt
pip install -r recommendation/requirements_backend.txt
```

---

## 📝 Ghi chú

- **Cần cài đặt Docker** trước khi chạy project
- **Không cần tạo lại thư mục `venv`** nếu đã có sẵn
- **Groq API Key** cần thiết để sử dụng LLM
- **Frontend và Backend chạy trên port khác nhau**: Frontend (5173), Backend (8000)
- Trong production, hãy thay đổi CORS policy từ `*` sang domain cụ thể

---

## 📞 Tác giả

**Nhóm 6 - Big Data**

---

**Giờ bạn đã sẵn sàng để chạy toàn bộ dự án!** 🎉
