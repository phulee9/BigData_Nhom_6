import { useState } from 'react';
import {
  uploadCVFile,
  submitManualInfo,
  getSkillRecommendations,
  getSkillRoadmap,
  getCareerAnalysis,
} from '../utils/api';

export const useCVAnalyzer = () => {
  const [currentStep, setCurrentStep] = useState('upload');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [cvData, setCvData] = useState(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [resultData, setResultData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [manualInput, setManualInput] = useState('');
  const [inputMode, setInputMode] = useState('upload');
  const [error, setError] = useState(null);

  // Separate states for manual input (2 columns)
  const [jobTitle, setJobTitle] = useState('');
  const [skillsInput, setSkillsInput] = useState('');

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (
      file &&
      (file.type === 'application/pdf' ||
        file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    ) {
      setUploadedFile(file);
      setInputMode('upload');
      setError(null);
    }
  };

  const handleAnalyzeClick = async () => {
    if (inputMode === 'upload' && !uploadedFile) {
      setError('Vui lòng chọn file CV');
      return;
    }
    if (inputMode === 'manual' && !jobTitle.trim()) {
      setError('Vui lòng nhập Job Title');
      return;
    }
    if (inputMode === 'manual' && !skillsInput.trim()) {
      setError('Vui lòng nhập ít nhất một skill');
      return;
    }
    await analyzeCVFromSource(inputMode);
  };

  const analyzeCVFromSource = async (source) => {
    setIsLoading(true);
    setError(null);
    try {
      let data;
      if (source === 'upload') {
        data = await uploadCVFile(uploadedFile);
      } else {
        // Parse skills: split by comma and clean
        const skills = skillsInput
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length > 0);

        data = await submitManualInfo(jobTitle.trim(), skills);
      }

      setCvData(data);
      setCurrentStep('analyze');
    } catch (err) {
      setError(err.message || 'Lỗi phân tích CV');
      console.error('CV Analysis error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalysisOption = async (type) => {
    if (!cvData) {
      setError('Không có dữ liệu CV');
      return;
    }

    // Nếu là career analysis, chỉ cần set selectedOption để hiển thị dialog
    // Dialog sẽ handler phần nhập job_to
    if (type === 'careerAnalysis') {
      setSelectedOption(type);
      setCurrentStep('result');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const jobTitleData = cvData.vi_tri_ung_tuyen || '';
      const skills = cvData.skills || [];

      let result;
      if (type === 'missingSkills') {
        result = await getSkillRecommendations(jobTitleData, skills);
      } else if (type === 'roadmap') {
        result = await getSkillRoadmap(jobTitleData, skills);
      }

      setResultData(result);
      setSelectedOption(type);
      setCurrentStep('result');
    } catch (err) {
      setError(err.message || 'Lỗi xử lý yêu cầu');
      console.error('Analysis error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCareerAnalysis = async (jobTo) => {
    if (!cvData) {
      setError('Không có dữ liệu CV');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const jobFrom = cvData.vi_tri_ung_tuyen || '';
      const skills = cvData.skills || [];

      const result = await getCareerAnalysis(jobFrom, jobTo, skills);

      setResultData(result);
      setCurrentStep('result');
    } catch (err) {
      setError(err.message || 'Lỗi xử lý yêu cầu');
      console.error('Career analysis error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const resetToUpload = () => {
    setCurrentStep('upload');
    setUploadedFile(null);
    setManualInput('');
    setJobTitle('');
    setSkillsInput('');
    setCvData(null);
    setSelectedOption(null);
    setResultData(null);
    setError(null);
  };

  return {
    currentStep,
    setCurrentStep,
    uploadedFile,
    setUploadedFile,
    cvData,
    setCvData,
    selectedOption,
    resultData,
    isLoading,
    manualInput,
    setManualInput,
    jobTitle,
    setJobTitle,
    skillsInput,
    setSkillsInput,
    inputMode,
    setInputMode,
    error,
    setError,
    handleFileUpload,
    handleAnalyzeClick,
    handleAnalysisOption,
    handleCareerAnalysis,
    resetToUpload,
  };
};
