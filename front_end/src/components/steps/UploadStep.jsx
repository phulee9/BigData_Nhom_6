import React from 'react';
import { Upload, FileText, Zap, Loader, AlertCircle } from 'lucide-react';
import { Header } from '../common/Header';
import { styles } from '../../styles/styles';

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
  return (
    <div style={styles.step}>
      <Header
        title="CV Analyzer"
        subtitle="Phân tích CV của bạn và nhận gợi ý phát triển sự nghiệp"
        showLogo={true}
      />

      <div style={styles.card}>
        {/* Error message */}
        {error && (
          <div
            style={{
              padding: '12px 16px',
              marginBottom: '16px',
              backgroundColor: '#fee2e2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              color: '#dc2626',
            }}
          >
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
            <Upload size={18} style={{ marginRight: '8px' }} />
            Tải File
          </button>
          <button
            onClick={() => setInputMode('manual')}
            style={{
              ...styles.tab,
              ...(inputMode === 'manual' ? styles.tabActive : styles.tabInactive),
            }}
          >
            <FileText size={18} style={{ marginRight: '8px' }} />
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
                <Upload size={48} style={{ color: '#6366f1', marginBottom: '12px' }} />
                <p style={styles.dropZoneText}>
                  Kéo thả file hoặc <span style={styles.highlight}>chọn file</span>
                </p>
                <p style={styles.dropZoneSubtext}>Hỗ trợ PDF, DOCX</p>
              </label>
            </div>
            {uploadedFile && (
              <div style={styles.fileSelected}>
                <FileText size={20} style={{ color: '#10b981' }} />
                <span>{uploadedFile.name}</span>
              </div>
            )}
          </div>
        )}

        {/* Nhập thông tin thủ công */}
        {inputMode === 'manual' && (
          <div style={styles.manualInputSection}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              {/* Cột 1: Job Title */}
              <div>
                <label
                  style={{
                    display: 'block',
                    marginBottom: '8px',
                    fontWeight: '500',
                    color: '#1f2937',
                  }}
                >
                  Vị trí công việc
                </label>
                <input
                  type="text"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="VD: Senior Software Engineer, Product Manager..."
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontFamily: 'inherit',
                    boxSizing: 'border-box',
                    transition: 'border-color 0.2s',
                  }}
                  onFocus={(e) => (e.target.style.borderColor = '#6366f1')}
                  onBlur={(e) => (e.target.style.borderColor = '#e5e7eb')}
                />
              </div>

              {/* Cột 2: Skills */}
              <div>
                <label
                  style={{
                    display: 'block',
                    marginBottom: '8px',
                    fontWeight: '500',
                    color: '#1f2937',
                  }}
                >
                  Các kỹ năng (cách nhau bằng dấu phẩy)
                </label>
                <textarea
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                  placeholder="VD: JavaScript, React, Node.js, REST APIs, Docker"
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    minHeight: '120px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontFamily: 'inherit',
                    boxSizing: 'border-box',
                    resize: 'vertical',
                    transition: 'border-color 0.2s',
                  }}
                  onFocus={(e) => (e.target.style.borderColor = '#6366f1')}
                  onBlur={(e) => (e.target.style.borderColor = '#e5e7eb')}
                />
                <p style={{ marginTop: '6px', fontSize: '12px', color: '#6b7280' }}>
                  💡 Nhập từng skill cách nhau bằng dấu phẩy (,) hoặc mỗi dòng một skill
                </p>
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
              <Loader
                size={18}
                style={{ marginRight: '8px', animation: 'spin 1s linear infinite' }}
              />
              Đang phân tích...
            </>
          ) : (
            <>
              <Zap size={18} style={{ marginRight: '8px' }} />
              Phân Tích CV
            </>
          )}
        </button>
      </div>
    </div>
  );
}
