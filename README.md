# Hướng dẫn chạy project

## 1. Clone project từ GitHub

```bash
git clone <link-repository>
cd BigData_Nhom_6
```

---

## 2. Tạo môi trường Python (venv)

```bash
python3 -m venv venv
```

---

## 3. Kích hoạt môi trường ảo

Linux / MacOS:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

Sau khi kích hoạt thành công terminal sẽ hiện:

```
(venv)
```

---

## 4. Cài đặt các thư viện cần thiết

```bash
pip install -r requirements.txt
```

---

## 5. Khởi động Kafka bằng Docker

```bash
docker compose up -d
```

Lệnh này sẽ chạy các container Kafka cần thiết.

---

## 6. Chạy chương trình Producer

```bash
python producer.py
```

Producer sẽ gửi dữ liệu vào Kafka.

---

# Lưu ý

- Cần cài đặt **Docker** trước khi chạy project.
- Không cần tạo lại thư mục `venv` nếu đã có sẵn.
- Nếu gặp lỗi thư viện hãy cài lại bằng `requirements.txt`.

---

# Tác giả

Nhóm 6 - Big Data
