import { MOCK_ANALYSIS_RESULTS, MOCK_CV_DATA } from '../constants/mockData';

// Simulate CV parsing
export const analyzeCVData = async (source, input) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const cvData =
        source === 'manual'
          ? {
              ...MOCK_CV_DATA,
              summary: input || MOCK_CV_DATA.summary,
            }
          : MOCK_CV_DATA;

      resolve(cvData);
    }, 1500);
  });
};

// Simulate API call for different analysis types
export const callAnalysisAPI = async (type) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const results = {
        missingSkills: MOCK_ANALYSIS_RESULTS.missingSkills,
        roadmap: MOCK_ANALYSIS_RESULTS.roadmap,
        careerAnalysis: MOCK_ANALYSIS_RESULTS.careerAnalysis,
      };

      resolve(results[type] || null);
    }, 2000);
  });
};
