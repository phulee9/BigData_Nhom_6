import React from 'react';
import { Upload, FileText, Zap, Loader, AlertCircle } from 'lucide-react';
import { Header } from '../common/Header';
import { styles } from '../../styles/styles';
import { designSystem } from '../../styles/designSystem';

const inputStyle = {
  width: '100%',
  padding: '12px 16px',
  border: `1px solid ${designSystem.colors.neutral[300]}`,
  borderRadius: '8px',
  fontSize: '14px',
  fontFamily: 'inherit',
  boxSizing: 'border-box',
  transition: designSystem.transition.fast,
  backgroundColor: designSystem.colors.neutral[50],
};

const inputFocusStyle = {
  ...inputStyle,
  borderColor: designSystem.colors.primary[500],
  boxShadow: `0 0 0 3px ${designSystem.colors.primary[100]}`,
};

const labelStyle = {
  display: 'block',
  marginBottom: '10px',
  fontWeight: designSystem.typography.weight.semibold,
  color: designSystem.colors.neutral[900],
  fontSize: '14px',
};

const hintStyle = {
  marginTop: '8px',
  fontSize: '12px',
  color: designSystem.colors.neutral[600],
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
};

const errorStyle = {
  padding: '14px 16px',
  marginBottom: '20px',
  backgroundColor: '#fee2e2',
  border: `1px solid #fecaca`,
  borderRadius: '8px',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  color: '#dc2626',
};

export function UploadStep({
  inputMode,
  setInputMode,
  uploadedFile,
  jobTitle,
  setJobTitle,
  skillsInput,
  setSkillsInput,
  handleFileUpload,
  handleAnalyzeClick,
  isLoading,
  error,
}) {
  const [jobTitleFocused, setJobTitleFocused] = React.useState(false);
  const [skillsFocused, setSkillsFocused] = React.useState(false);

  return (
    <div style={styles.step}>
      <Header
        title="CV Analyzer Pro"
        subtitle="Phân tích CV của bạn và khám phá những cơ hội phát triển sự nghiệp"
        showLogo={true}
      />

      <div style={styles.card}>
        {/* Error message */}
        {error && (
          <div style={errorStyle}>
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        {/* Tab chọn chế độ */}
        <div style={styles.tabContainer}>
          <button
            onClick={() => setInputMode('upload')}
            style={{
              ...styles.tab,
              ...(inputMode === 'upload' ? styles.tabActive : styles.tabInactive),
            }}
          >
            <Upload size={18} />
            Tải File
          </button>
          <button
            onClick={() => setInputMode('manual')}
            style={{
              ...styles.tab,
              ...(inputMode === 'manual' ? styles.tabActive : styles.tabInactive),
            }}
          >
            <FileText size={18} />
            Nhập Thông Tin
          </button>
        </div>

        {/* Upload file */}
        {inputMode === 'upload' && (
          <div style={styles.uploadSection}>
            <div style={styles.dropZone}>
              <input
                type="file"
                onChange={handleFileUpload}
                accept=".pdf,.docx"
                style={styles.hiddenInput}
                id="fileInput"
              />
              <label htmlFor="fileInput" style={styles.dropZoneLabel}>
                <Upload
                  size={56}
                  style={{ color: designSystem.colors.primary[600], marginBottom: '16px' }}
                />
                <p style={styles.dropZoneText}>
                  Kéo thả file hoặc <span style={styles.highlight}>chọn file</span>
                </p>
                <p style={styles.dropZoneSubtext}>Hỗ trợ PDF, DOCX (Tối đa 10MB)</p>
              </label>
            </div>
            {uploadedFile && (
              <div style={styles.fileSelected}>
                <FileText size={20} />
                <span>{uploadedFile.name}</span>
              </div>
            )}
          </div>
        )}

        {/* Nhập thông tin thủ công */}
        {inputMode === 'manual' && (
          <div style={styles.manualInputSection}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              {/* Cột 1: Job Title */}
              <div>
                <label style={labelStyle}>Vị trí công việc</label>
                <input
                  type="text"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  onFocus={() => setJobTitleFocused(true)}
                  onBlur={() => setJobTitleFocused(false)}
                  placeholder="VD: Senior Software Engineer, Product Manager..."
                  style={jobTitleFocused ? inputFocusStyle : inputStyle}
                />
                <p style={hintStyle}>📝 Nhập rõ vị trí bạn đang làm hoặc muốn apply</p>
              </div>

              {/* Cột 2: Skills */}
              <div>
                <label style={labelStyle}>Các kỹ năng (cách nhau bằng dấu phẩy)</label>
                <textarea
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                  onFocus={() => setSkillsFocused(true)}
                  onBlur={() => setSkillsFocused(false)}
                  placeholder="VD: JavaScript, React, Node.js, REST APIs, Docker"
                  style={{
                    ...inputStyle,
                    minHeight: '120px',
                    resize: 'vertical',
                    ...(skillsFocused
                      ? {
                          borderColor: designSystem.colors.primary[500],
                          boxShadow: `0 0 0 3px ${designSystem.colors.primary[100]}`,
                        }
                      : {}),
                  }}
                />
                <p style={hintStyle}>💡 Mỗi skill cách nhau bằng dấu phẩy (,)</p>
              </div>
            </div>
          </div>
        )}

        <button
          onClick={handleAnalyzeClick}
          disabled={isLoading}
          style={{
            ...styles.primaryButton,
            ...(isLoading ? styles.buttonDisabled : {}),
          }}
        >
          {isLoading ? (
            <>
              <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
              Đang phân tích...
            </>
          ) : (
            <>
              <Zap size={18} />
              {inputMode === 'upload' ? 'Phân Tích CV' : 'Phân Tích'}
            </>
          )}
        </button>
      </div>
    </div>
  );
}
