# CV Analyzer Frontend

Ứng dụng phân tích CV và gợi ý phát triển sự nghiệp

## Yêu cầu

- Node.js >= 14.0.0
- npm hoặc yarn

## Cài đặt

### 1. Cài đặt thư viện

```bash
npm install
```

hoặc nếu dùng yarn:

```bash
yarn install
```

### 2. Khởi động server phát triển

```bash
npm run dev
```

hoặc:

```bash
yarn dev
```

Ứng dụng sẽ mở tự động tại `http://localhost:3000`

### 3. Build cho production

```bash
npm run build
```

Build file sẽ nằm trong folder `dist/`

## Cấu trúc Folder

```
src/
├── components/          # React Components
│   ├── common/         # Reusable components
│   │   ├── Header.jsx
│   │   └── BackButton.jsx
│   └── steps/          # Page-level components
│       ├── UploadStep.jsx
│       ├── AnalyzeStep.jsx
│       ├── OptionsStep.jsx
│       └── ResultStep.jsx
├── hooks/              # Custom Hooks
│   └── useCVAnalyzer.js
├── utils/              # Utility functions
│   └── api.js
├── constants/          # Constants & Mock Data
│   └── mockData.js
├── styles/             # Styling
│   ├── index.css
│   └── styles.js
├── App.jsx             # Main component
└── main.jsx            # Entry point
```

## Thư viện chính

- **React** - UI framework
- **Vite** - Build tool
- **lucide-react** - Icons library

## Tính năng

- ✅ Tải CV từ file hoặc nhập thông tin thủ công
- ✅ Phân tích CV và hiển thị kỹ năng
- ✅ Recommendation cho kỹ năng còn thiếu
- ✅ Lộ trình phát triển kỹ năng (6 tháng)
- ✅ Phân tích hướng phát triển sự nghiệp

## Environment Variables

Tạo file `.env` dựa trên `.env.example`:

```bash
cp .env.example .env
```

Sau đó chỉnh sửa theo nhu cầu.

## Phát triển

Các command hữu ích:

```bash
# Khởi động trong chế độ phát triển
npm run dev

# Build production
npm run build

# Xem preview build
npm run preview
```

## Lưu ý

- Mock data hiện tại được sử dụng để demo
- Cần kết nối API thực tế để sử dụng trong production
- Responsive design đang được phát triển

## Cải thiện tương lai

- [ ] Kết nối API thực tế
- [ ] Thêm authentication
- [ ] Unit & Integration Tests
- [ ] Responsive Design cho Mobile
- [ ] Dark/Light Mode Toggle
- [ ] Internationalization (i18n)
