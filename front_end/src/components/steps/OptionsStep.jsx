import React from 'react';
import { ChevronRight } from 'lucide-react';
import { Header } from '../common/Header';
import { BackButton } from '../common/BackButton';
import { styles } from '../../styles/styles';

export function OptionsStep({ onBack, onSelectOption, isLoading }) {
  const options = [
    {
      type: 'missingSkills',
      icon: '🎯',
      title: 'Kỹ Năng Còn Thiếu',
      description: 'Tìm hiểu những kỹ năng còn thiếu trong CV của bạn',
      label: '5-10 phút đọc',
    },
    {
      type: 'roadmap',
      icon: '🗺️',
      title: 'Lộ Trình Phát Triển',
      description: 'Nhận kế hoạch chi tiết để cải thiện kỹ năng',
      label: '6 tháng kế hoạch',
    },
    {
      type: 'careerAnalysis',
      icon: '💼',
      title: 'Phân Tích Sự Nghiệp',
      description: 'Khám phá các cơ hội phát triển sự nghiệp',
      label: 'Cơ hội mới',
    },
  ];

  return (
    <div style={styles.step}>
      <BackButton onClick={onBack} />

      <Header title="Chọn Loại Phân Tích" subtitle="Hãy chọn một trong ba lựa chọn dưới đây" />

      <div style={styles.optionsGrid}>
        {options.map((option) => (
          <div
            key={option.type}
            onClick={() => onSelectOption(option.type)}
            style={{
              ...styles.optionCard,
              pointerEvents: isLoading ? 'none' : 'auto',
              opacity: isLoading ? 0.5 : 1,
            }}
          >
            <div style={styles.optionIcon}>{option.icon}</div>
            <h3 style={styles.optionTitle}>{option.title}</h3>
            <p style={styles.optionDescription}>{option.description}</p>
            <div style={styles.optionFooter}>
              <span style={styles.optionLabel}>{option.label}</span>
              <ChevronRight size={20} />
            </div>
          </div>
        ))}
      </div>

      {isLoading && (
        <div style={styles.loadingOverlay}>
          <div style={styles.spinner}></div>
          <p>Đang xử lý...</p>
        </div>
      )}
    </div>
  );
}
