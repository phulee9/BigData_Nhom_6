import React, { useState } from 'react';
import { Header } from '../common/Header';
import { BackButton } from '../common/BackButton';
import { styles } from '../../styles/styles';

export function ResultStep({
  resultData,
  selectedOption,
  onBack,
  onSelectOtherAnalysis,
  onAnalyzeNewCV,
  cvData,
  onCareerAnalysis,
}) {
  const [jobTo, setJobTo] = useState('');

  // Show dialog nếu là career analysis và chưa có result
  const showDialog = selectedOption === 'careerAnalysis' && !resultData;

  const handleCareerSubmit = () => {
    if (!jobTo.trim()) {
      alert('Vui lòng nhập vị trí công việc mục tiêu');
      return;
    }
    onCareerAnalysis?.(jobTo.trim());
    setJobTo('');
  };

  const renderMissingSkills = () => (
    <div>
      {/* Vị trí công việc */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={styles.sectionTitle}>Vị Trí: {resultData.vi_tri_ung_tuyen}</h3>
        {resultData.job_titles_gan_nhat && resultData.job_titles_gan_nhat.length > 0 && (
          <div style={{ marginTop: '12px' }}>
            <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '8px' }}>
              Vị trí tương tự ({resultData.total_candidates} ứng viên):
            </p>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {resultData.job_titles_gan_nhat.map((title, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '6px',
                    fontSize: '14px',
                    color: '#1f2937',
                  }}
                >
                  {title}
                  {resultData.top_scores && resultData.top_scores[idx] && (
                    <span style={{ color: '#6366f1', marginLeft: '4px' }}>
                      ({(resultData.top_scores[idx] * 100).toFixed(1)}%)
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={styles.divider}></div>

      {/* Kỹ năng đã có */}
      {resultData.skills_da_co && resultData.skills_da_co.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={styles.sectionTitle}>Kỹ Năng Hiện Có</h3>
          <div style={styles.skillsList}>
            {resultData.skills_da_co.map((skill, idx) => (
              <span
                key={idx}
                style={{
                  ...styles.skillTag,
                  backgroundColor: '#d1fae5',
                  color: '#065f46',
                }}
              >
                ✓ {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={styles.divider}></div>

      {/* Kỹ năng gợi ý */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={styles.sectionTitle}>
          Kỹ Năng Được Gợi Ý ({resultData.skills_goi_y?.length || 0} skills)
        </h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '12px',
            marginTop: '12px',
          }}
        >
          {resultData.skills_goi_y?.map((item, idx) => (
            <div
              key={idx}
              style={{
                padding: '12px',
                backgroundColor: '#fef3c7',
                borderRadius: '8px',
                borderLeft: '4px solid #f59e0b',
              }}
            >
              <div
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                <span style={{ fontWeight: '500', color: '#1f2937' }}>{item.skill}</span>
                <span
                  style={{
                    fontSize: '12px',
                    backgroundColor: '#f59e0b',
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  {item.count} ứng viên
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderRoadmap = () => (
    <div>
      {/* Vị trí công việc */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={styles.sectionTitle}>Vị Trí: {resultData.job_title}</h3>
        <p style={{ fontSize: '14px', color: '#6b7280', marginTop: '8px' }}>
          Tìm thấy {resultData.total_jobs} công việc
        </p>
      </div>

      <div style={styles.divider}></div>

      {/* Kỹ năng hiện có */}
      {resultData.cv_skills && resultData.cv_skills.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={styles.sectionTitle}>Kỹ Năng Hiện Có</h3>
          <div style={styles.skillsList}>
            {resultData.cv_skills.map((skill, idx) => (
              <span
                key={idx}
                style={{
                  ...styles.skillTag,
                  backgroundColor: '#d1fae5',
                  color: '#065f46',
                }}
              >
                ✓ {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={styles.divider}></div>

      {/* Kỹ năng bắt buộc */}
      {resultData.must_have && resultData.must_have.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ ...styles.sectionTitle, color: '#dc2626' }}>⭐ Kỹ Năng Bắt Buộc</h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px',
              marginTop: '12px',
            }}
          >
            {resultData.must_have.map((item, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  backgroundColor: '#fee2e2',
                  borderRadius: '8px',
                  borderLeft: '4px solid #dc2626',
                }}
              >
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <span style={{ fontWeight: '600', color: '#991b1b' }}>{item.skill}</span>
                  <span
                    style={{
                      fontSize: '12px',
                      backgroundColor: '#dc2626',
                      color: 'white',
                      padding: '2px 8px',
                      borderRadius: '4px',
                    }}
                  >
                    {item.pct}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Kỹ năng nên có */}
      {resultData.should_have && resultData.should_have.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ ...styles.sectionTitle, color: '#f59e0b' }}>📌 Kỹ Năng Nên Có</h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px',
              marginTop: '12px',
            }}
          >
            {resultData.should_have.map((item, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  backgroundColor: '#fef3c7',
                  borderRadius: '8px',
                  borderLeft: '4px solid #f59e0b',
                }}
              >
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <span style={{ fontWeight: '500', color: '#92400e' }}>{item.skill}</span>
                  <span
                    style={{
                      fontSize: '12px',
                      backgroundColor: '#f59e0b',
                      color: 'white',
                      padding: '2px 8px',
                      borderRadius: '4px',
                    }}
                  >
                    {item.pct}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Kỹ năng tốt nếu có */}
      {resultData.nice_have && resultData.nice_have.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ ...styles.sectionTitle, color: '#10b981' }}>💡 Kỹ Năng Tốt Nếu Có</h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px',
              marginTop: '12px',
            }}
          >
            {resultData.nice_have.map((item, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  backgroundColor: '#d1fae5',
                  borderRadius: '8px',
                  borderLeft: '4px solid #10b981',
                }}
              >
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <span style={{ fontWeight: '500', color: '#065f46' }}>{item.skill}</span>
                  <span
                    style={{
                      fontSize: '12px',
                      backgroundColor: '#10b981',
                      color: 'white',
                      padding: '2px 8px',
                      borderRadius: '4px',
                    }}
                  >
                    {item.pct}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderCareerAnalysis = () => (
    <div>
      {resultData.error ? (
        <div
          style={{
            padding: '16px',
            backgroundColor: '#fee2e2',
            borderRadius: '8px',
            color: '#991b1b',
          }}
        >
          ⚠️ {resultData.error}
        </div>
      ) : (
        <>
          {/* Tiêu đề */}
          <div style={{ marginBottom: '24px' }}>
            <h3 style={styles.sectionTitle}>
              From: {resultData.job_from} → To: {resultData.job_to}
            </h3>
            <p style={{ fontSize: '16px', fontWeight: '600', color: '#6366f1', marginTop: '12px' }}>
              🎯 Match: {resultData.match_pct}% skills phù hợp
            </p>
          </div>

          <div style={styles.divider}></div>

          {/* Skills hiện có match với vị trí mới */}
          {resultData.cv_match && resultData.cv_match.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ ...styles.sectionTitle, color: '#10b981' }}>
                ✓ Kỹ Năng Hiện Có Phù Hợp
              </h3>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '12px',
                  marginTop: '12px',
                }}
              >
                {resultData.cv_match.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '12px',
                      backgroundColor: '#d1fae5',
                      borderRadius: '8px',
                      borderLeft: '4px solid #10b981',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontWeight: '600', color: '#065f46' }}>{item[0]}</span>
                      <span
                        style={{
                          fontSize: '12px',
                          backgroundColor: '#10b981',
                          color: 'white',
                          padding: '2px 8px',
                          borderRadius: '4px',
                        }}
                      >
                        {item[1]}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={styles.divider}></div>

          {/* Skills chung */}
          {resultData.common_skills && resultData.common_skills.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ ...styles.sectionTitle, color: '#0891b2' }}>
                🔗 Kỹ Năng Chung (Cả 2 vị trí)
              </h3>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '12px',
                  marginTop: '12px',
                }}
              >
                {resultData.common_skills.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '12px',
                      backgroundColor: '#ccf6ff',
                      borderRadius: '8px',
                      borderLeft: '4px solid #0891b2',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontWeight: '500', color: '#164e63' }}>{item[0]}</span>
                      <span
                        style={{
                          fontSize: '12px',
                          backgroundColor: '#0891b2',
                          color: 'white',
                          padding: '2px 8px',
                          borderRadius: '4px',
                        }}
                      >
                        {item[1]}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={styles.divider}></div>

          {/* Cần học */}
          {resultData.need_to_learn && resultData.need_to_learn.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ ...styles.sectionTitle, color: '#dc2626' }}>📚 Cần Học</h3>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '12px',
                  marginTop: '12px',
                }}
              >
                {resultData.need_to_learn.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '12px',
                      backgroundColor: '#fee2e2',
                      borderRadius: '8px',
                      borderLeft: '4px solid #dc2626',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontWeight: '600', color: '#991b1b' }}>{item[0]}</span>
                      <span
                        style={{
                          fontSize: '12px',
                          backgroundColor: '#dc2626',
                          color: 'white',
                          padding: '2px 8px',
                          borderRadius: '4px',
                        }}
                      >
                        {item[1]}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );

  return (
    <div style={styles.step}>
      {resultData ? (
        <>
          <BackButton onClick={onBack} label="Quay lại Chọn Phân Tích" />

          <Header
            title={
              selectedOption === 'careerAnalysis' && !resultData?.error
                ? `${resultData?.job_from} → ${resultData?.job_to}`
                : 'Kết Quả Phân Tích'
            }
            subtitle={
              selectedOption === 'careerAnalysis' && !resultData?.error
                ? 'Phân Tích Chuyển Hướng Nghề Nghiệp'
                : 'Các Kỹ Năng Được Đề Xuất'
            }
          />

          <div style={styles.card}>
            {selectedOption === 'missingSkills' && renderMissingSkills()}
            {selectedOption === 'roadmap' && renderRoadmap()}
            {selectedOption === 'careerAnalysis' && renderCareerAnalysis()}

            <div style={styles.actionButtons}>
              <button onClick={onAnalyzeNewCV} style={styles.secondaryButton}>
                Phân Tích CV Khác
              </button>
              <button onClick={onSelectOtherAnalysis} style={styles.primaryButton}>
                Chọn Phân Tích Khác
              </button>
            </div>
          </div>
        </>
      ) : null}

      {/* Dialog nhập job_to cho Career Switch */}
      {showDialog && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: '#ffffff',
              borderRadius: '12px',
              padding: '32px',
              maxWidth: '500px',
              width: '90%',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            }}
          >
            <h2
              style={{
                fontSize: '20px',
                fontWeight: '700',
                color: '#1f2937',
                margin: '0 0 12px 0',
              }}
            >
              Chuyển Hướng Nghề Nghiệp
            </h2>
            <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 24px 0' }}>
              Nhập vị trí công việc bạn muốn chuyển sang
            </p>

            <div style={{ marginBottom: '20px' }}>
              <label
                style={{
                  display: 'block',
                  marginBottom: '8px',
                  fontWeight: '500',
                  color: '#1f2937',
                }}
              >
                Vị Trí Mục Tiêu
              </label>
              <input
                type="text"
                value={jobTo}
                onChange={(e) => setJobTo(e.target.value)}
                placeholder="VD: Data Scientist, Machine Learning Engineer..."
                autoFocus
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontFamily: 'inherit',
                  boxSizing: 'border-box',
                  outline: 'none',
                  transition: 'border-color 0.2s',
                }}
                onFocus={(e) => (e.target.style.borderColor = '#6366f1')}
                onBlur={(e) => (e.target.style.borderColor = '#e5e7eb')}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') handleCareerSubmit();
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={() => {
                  setJobTo('');
                  onBack?.();
                }}
                style={{
                  flex: 1,
                  padding: '12px 24px',
                  backgroundColor: 'transparent',
                  border: '1px solid #e5e7eb',
                  color: '#6b7280',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Hủy
              </button>
              <button
                onClick={handleCareerSubmit}
                style={{
                  flex: 1,
                  padding: '12px 24px',
                  backgroundColor: '#6366f1',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Phân Tích
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
