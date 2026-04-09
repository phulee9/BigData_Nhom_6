# CV Analyzer Frontend

Cấu trúc folder chuẩn React project:

```
src/
├── components/          # React Components
│   ├── common/         # Reusable components (Header, Button, etc.)
│   │   ├── Header.jsx
│   │   └── BackButton.jsx
│   └── steps/          # Page-level components
│       ├── UploadStep.jsx
│       ├── AnalyzeStep.jsx
│       ├── OptionsStep.jsx
│       └── ResultStep.jsx
├── hooks/              # Custom React Hooks
│   └── useCVAnalyzer.js
├── utils/              # Utility functions & API calls
│   └── api.js
├── constants/          # Constants & Mock Data
│   └── mockData.js
├── styles/             # Styling
│   ├── index.css
│   └── styles.js       # CSS-in-JS object
├── App.jsx             # Main App component
└── README.md           # This file
```

## Tính năng chính:

1. **Upload CV** - Tải file hoặc nhập thông tin thủ công
2. **Phân tích CV** - Hiển thị kỹ năng được phát hiện
3. **Các loại phân tích**:
   - Kỹ Năng Còn Thiếu
   - Lộ Trình Phát Triển
   - Phân Tích Sự Nghiệp

## Bắt đầu:

```bash
npm install
npm start
```

## Cải thiện trong tương lai:

- [ ] Kết nối API thực tế
- [ ] Thêm Unit Tests
- [ ] Tối ưu hóa Performance
- [ ] Responsive Design cho Mobile
