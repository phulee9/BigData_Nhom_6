export const MOCK_CV_DATA = {
  name: 'Nguyễn Văn A',
  email: 'nguyenvan@example.com',
  phone: '+84 123456789',
  skills: [
    { category: 'Frontend', items: ['React', 'JavaScript', 'CSS', 'HTML'] },
    { category: 'Backend', items: ['Node.js', 'Express', 'MongoDB'] },
    { category: 'Tools', items: ['Git', 'Docker', 'AWS'] },
  ],
  experience: '5 năm phát triển web',
  summary: 'Senior Developer with expertise in full-stack development',
};

export const MOCK_ANALYSIS_RESULTS = {
  missingSkills: {
    title: '🎯 Kỹ Năng Còn Thiếu',
    description: 'Các kỹ năng được yêu cầu trong ngành nhưng bạn chưa có',
    skills: [
      {
        skill: 'TypeScript',
        importance: 'Cao',
        reason: 'Ngôn ngữ được sử dụng rộng rãi trong dự án hiện đại',
      },
      {
        skill: 'GraphQL',
        importance: 'Trung bình',
        reason: 'Thay thế REST API trong các ứng dụng mới',
      },
      {
        skill: 'React Native',
        importance: 'Cao',
        reason: 'Phát triển ứng dụng mobile từ code React',
      },
      { skill: 'Next.js', importance: 'Cao', reason: 'Framework phổ biến cho React apps' },
      {
        skill: 'Testing (Jest, Cypress)',
        importance: 'Trung bình',
        reason: 'Đảm bảo chất lượng code',
      },
    ],
  },
  roadmap: {
    title: '🗺️ Lộ Trình Phát Triển Kỹ Năng',
    description: 'Kế hoạch 6 tháng để nâng cao kỹ năng',
    phases: [
      {
        phase: 'Tháng 1-2: Nền Tảng',
        tasks: ['Học TypeScript cơ bản (2 tuần)', 'Hoàn thành 3 dự án TypeScript nhỏ (4 tuần)'],
      },
      {
        phase: 'Tháng 3-4: Framework & Tools',
        tasks: ['Học Next.js (3 tuần)', 'Xây dựng 1 ứng dụng Next.js hoàn chỉnh (3 tuần)'],
      },
      {
        phase: 'Tháng 5-6: Advanced Topics',
        tasks: ['Học GraphQL (2 tuần)', 'Thực hành với React Native (4 tuần)'],
      },
    ],
  },
  careerAnalysis: {
    title: '💼 Phân Tích Hướng Phát Triển Sự Nghiệp',
    description: 'Gợi ý các vị trí phù hợp và hướng phát triển',
    currentRole: 'Full-stack Developer',
    recommendations: [
      {
        title: 'Senior Full-stack Developer',
        timeline: '1-2 năm',
        requirements: 'Thêm TypeScript, GraphQL, System Design',
        salary: '3000-5000 USD',
      },
      {
        title: 'Tech Lead',
        timeline: '2-3 năm',
        requirements: 'Kỹ năng quản lý, mentoring, kiến trúc hệ thống',
        salary: '4000-7000 USD',
      },
      {
        title: 'Freelancer/Entrepreneur',
        timeline: 'Ngay lập tức',
        requirements: 'Kỹ năng kinh doanh, marketing, quản lý dự án',
        salary: 'Tùy vào thị trường',
      },
    ],
    strengths: 'Nền tảng vững chắc ở cả frontend và backend',
    opportunities: 'Các công ty startup đang tìm developer full-stack',
  },
};
