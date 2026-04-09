import { useState } from 'react';
import { analyzeCVData, callAnalysisAPI } from '../utils/api';

export const useCVAnalyzer = () => {
  const [currentStep, setCurrentStep] = useState('upload');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [cvData, setCvData] = useState(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [resultData, setResultData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [manualInput, setManualInput] = useState('');
  const [inputMode, setInputMode] = useState('upload');

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (
      file &&
      (file.type === 'application/pdf' ||
        file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    ) {
      setUploadedFile(file);
      setInputMode('upload');
    }
  };

  const handleAnalyzeClick = async () => {
    if (inputMode === 'upload' && !uploadedFile) {
      alert('Vui lòng chọn file CV');
      return;
    }
    if (inputMode === 'manual' && !manualInput.trim()) {
      alert('Vui lòng nhập thông tin CV');
      return;
    }
    await simulateCVAnalysis(inputMode);
  };

  const simulateCVAnalysis = async (source) => {
    setIsLoading(true);
    const data = await analyzeCVData(source, manualInput);
    setCvData(data);
    setCurrentStep('analyze');
    setIsLoading(false);
  };

  const handleAnalysisOption = async (type) => {
    setIsLoading(true);
    const result = await callAnalysisAPI(type);
    setResultData(result);
    setSelectedOption(type);
    setCurrentStep('result');
    setIsLoading(false);
  };

  const resetToUpload = () => {
    setCurrentStep('upload');
    setUploadedFile(null);
    setManualInput('');
    setCvData(null);
    setSelectedOption(null);
    setResultData(null);
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
    inputMode,
    setInputMode,
    handleFileUpload,
    handleAnalyzeClick,
    handleAnalysisOption,
    resetToUpload,
  };
};
