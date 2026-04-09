import React from 'react';
import { ChevronRight } from 'lucide-react';
import { Header } from '../common/Header';
import { BackButton } from '../common/BackButton';
import { styles } from '../../styles/styles';

export function AnalyzeStep({ cvData, onBack, onContinue }) {
  if (!cvData) return null;

  // Kiểm tra xem là manual input (chỉ có vi_tri_ung_tuyen + skills) hay upload file
  const isManualInput = !cvData.name && cvData.vi_tri_ung_tuyen && Array.isArray(cvData.skills);

  return (
    <div style={styles.step}>
      <BackButton onClick={onBack} />

      <Header title="Thông Tin CV" subtitle="Các kỹ năng đã phát hiện" />

      <div style={styles.card}>
        {/* Nếu là manual input - hiển thị phiên bản đơn giản */}
        {isManualInput ? (
          <>
            <div style={{ marginBottom: '24px' }}>
              <h3 style={styles.sectionTitle}>Vị Trí Công Việc</h3>
              <p
                style={{
                  fontSize: '16px',
                  color: '#1f2937',
                  padding: '12px 16px',
                  backgroundColor: '#f3f4f6',
                  borderRadius: '8px',
                  margin: '8px 0',
                }}
              >
                {cvData.vi_tri_ung_tuyen}
              </p>
            </div>

            <div style={styles.skillsSection}>
              <h3 style={styles.sectionTitle}>Các Kỹ Năng Hiện Có</h3>
              <div style={styles.skillsList}>
                {cvData.skills.map((skill, idx) => (
                  <span key={idx} style={styles.skillTag}>
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </>
        ) : (
          // Nếu là upload file - hiển thị chi tiết
          <>
            <div style={styles.profileSection}>
              <div style={styles.profileAvatar}>{cvData.name?.charAt(0).toUpperCase()}</div>
              <div>
                <h2 style={styles.profileName}>{cvData.name}</h2>
                <p style={styles.profileEmail}>{cvData.email}</p>
                <p style={styles.profilePhone}>{cvData.phone}</p>
              </div>
            </div>

            <div style={styles.divider}></div>

            <div style={styles.summarySection}>
              <h3 style={styles.sectionTitle}>Tóm Tắt Kinh Nghiệm</h3>
              <p style={styles.summaryText}>{cvData.experience}</p>
            </div>

            <div style={styles.skillsSection}>
              <h3 style={styles.sectionTitle}>Các Kỹ Năng</h3>
              {cvData.skills.map((skillGroup, idx) => (
                <div key={idx} style={styles.skillGroup}>
                  <h4 style={styles.skillGroupTitle}>{skillGroup.category}</h4>
                  <div style={styles.skillsList}>
                    {skillGroup.items.map((skill, i) => (
                      <span key={i} style={styles.skillTag}>
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        <button onClick={onContinue} style={styles.primaryButton}>
          Tiếp Tục Phân Tích
          <ChevronRight size={18} style={{ marginLeft: '8px' }} />
        </button>
      </div>
    </div>
  );
}
