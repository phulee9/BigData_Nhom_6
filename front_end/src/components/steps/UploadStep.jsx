import React from 'react';
import { Upload, FileText, Zap, Loader } from 'lucide-react';
import { Header } from '../common/Header';
import { styles } from '../../styles/styles';

export function UploadStep({
  inputMode,
  setInputMode,
  uploadedFile,
  manualInput,
  setManualInput,
  handleFileUpload,
  handleAnalyzeClick,
  isLoading,
}) {
  return (
    <div style={styles.step}>
      <Header
        title="CV Analyzer"
        subtitle="Phân tích CV của bạn và nhận gợi ý phát triển sự nghiệp"
        showLogo={true}
      />

      <div style={styles.card}>
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
            <textarea
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder="Nhập thông tin CV của bạn ở đây... (tên, kỹ năng, kinh nghiệm, học vấn, v.v.)"
              style={styles.textarea}
            />
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
