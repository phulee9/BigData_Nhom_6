import React from 'react';
import { Header } from '../common/Header';
import { BackButton } from '../common/BackButton';
import { styles } from '../../styles/styles';

export function ResultStep({
  resultData,
  selectedOption,
  onBack,
  onSelectOtherAnalysis,
  onAnalyzeNewCV,
}) {
  if (!resultData) return null;

  const renderMissingSkills = () => (
    <div>
      {resultData.skills.map((item, idx) => (
        <div key={idx} style={styles.skillItem}>
          <div style={styles.skillItemHeader}>
            <h4 style={styles.skillItemName}>{item.skill}</h4>
            <span
              style={{
                ...styles.badge,
                backgroundColor: item.importance === 'Cao' ? '#ef4444' : '#f59e0b',
              }}
            >
              {item.importance}
            </span>
          </div>
          <p style={styles.skillItemReason}>{item.reason}</p>
        </div>
      ))}
    </div>
  );

  const renderRoadmap = () => (
    <div>
      {resultData.phases.map((phase, idx) => (
        <div key={idx} style={styles.phaseBlock}>
          <h4 style={styles.phaseTitle}>{phase.phase}</h4>
          <ul style={styles.taskList}>
            {phase.tasks.map((task, i) => (
              <li key={i} style={styles.taskItem}>
                {task}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );

  const renderCareerAnalysis = () => (
    <div>
      <div style={styles.careerSection}>
        <h4 style={styles.careerLabel}>Vị Trí Hiện Tại</h4>
        <p style={styles.careerValue}>{resultData.currentRole}</p>
      </div>

      <div style={styles.divider}></div>

      <div style={styles.careerSection}>
        <h4 style={styles.careerLabel}>Điểm Mạnh</h4>
        <p style={styles.careerValue}>{resultData.strengths}</p>
      </div>

      <div style={styles.divider}></div>

      <div style={styles.careerSection}>
        <h4 style={styles.careerLabel}>Cơ Hội</h4>
        <p style={styles.careerValue}>{resultData.opportunities}</p>
      </div>

      <div style={styles.divider}></div>

      <h4 style={styles.recommendationsTitle}>Các Vị Trí Được Đề Xuất</h4>
      {resultData.recommendations.map((rec, idx) => (
        <div key={idx} style={styles.recommendationCard}>
          <div style={styles.recHeader}>
            <h5 style={styles.recTitle}>{rec.title}</h5>
            <span style={styles.recSalary}>{rec.salary}</span>
          </div>
          <p style={styles.recTimeline}>
            Thời gian: <strong>{rec.timeline}</strong>
          </p>
          <p style={styles.recRequirements}>Yêu cầu: {rec.requirements}</p>
        </div>
      ))}
    </div>
  );

  return (
    <div style={styles.step}>
      <BackButton onClick={onBack} label="Quay lại Chọn Phân Tích" />

      <Header title={resultData.title} subtitle={resultData.description} />

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
    </div>
  );
}
