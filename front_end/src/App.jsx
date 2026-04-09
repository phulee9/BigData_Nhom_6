import React from 'react';
import { useCVAnalyzer } from './hooks/useCVAnalyzer';
import { UploadStep } from './components/steps/UploadStep';
import { AnalyzeStep } from './components/steps/AnalyzeStep';
import { OptionsStep } from './components/steps/OptionsStep';
import { ResultStep } from './components/steps/ResultStep';
import { styles } from './styles/styles';
import './styles/index.css';

export default function CVAnalyzerApp() {
  const cv = useCVAnalyzer();

  return (
    <div style={styles.container}>
      <div style={styles.backgroundGradient}></div>

      <div style={styles.content}>
        {/* STEP 1: Upload CV */}
        {cv.currentStep === 'upload' && (
          <UploadStep
            inputMode={cv.inputMode}
            setInputMode={cv.setInputMode}
            uploadedFile={cv.uploadedFile}
            jobTitle={cv.jobTitle}
            setJobTitle={cv.setJobTitle}
            skillsInput={cv.skillsInput}
            setSkillsInput={cv.setSkillsInput}
            handleFileUpload={cv.handleFileUpload}
            handleAnalyzeClick={cv.handleAnalyzeClick}
            isLoading={cv.isLoading}
            error={cv.error}
          />
        )}

        {/* STEP 2: Display CV Info */}
        {cv.currentStep === 'analyze' && cv.cvData && (
          <AnalyzeStep
            cvData={cv.cvData}
            onBack={cv.resetToUpload}
            onContinue={() => cv.setCurrentStep('options')}
          />
        )}

        {/* STEP 3: Select Analysis Type */}
        {cv.currentStep === 'options' && cv.cvData && !cv.selectedOption && (
          <OptionsStep
            onBack={() => cv.setCurrentStep('analyze')}
            onSelectOption={cv.handleAnalysisOption}
            isLoading={cv.isLoading}
          />
        )}

        {/* STEP 4: Display Results */}
        {cv.currentStep === 'result' && cv.cvData && (
          <ResultStep
            resultData={cv.resultData}
            selectedOption={cv.selectedOption}
            cvData={cv.cvData}
            onBack={() => cv.setCurrentStep('options')}
            onSelectOtherAnalysis={() => {
              cv.setSelectedOption(null);
              cv.setCurrentStep('options');
            }}
            onAnalyzeNewCV={cv.resetToUpload}
            onCareerAnalysis={cv.handleCareerAnalysis}
          />
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes gradientShift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
      `}</style>
    </div>
  );
}
