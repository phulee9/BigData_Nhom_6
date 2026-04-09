import { MOCK_ANALYSIS_RESULTS, MOCK_CV_DATA } from '../constants/mockData';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Upload CV File ──────────────────────────────────────
export const uploadCVFile = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/api/upload-cv`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Upload CV error:', error);
    throw error;
  }
};

// ── Manual CV Input ─────────────────────────────────────
export const submitManualInfo = async (jobTitle, skills) => {
  try {
    const response = await fetch(`${API_BASE}/api/manual-info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        job_title: jobTitle,
        skills: skills,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Manual info error:', error);
    throw error;
  }
};

// ── Recommend Skills ────────────────────────────────────
export const getSkillRecommendations = async (jobTitle, skills) => {
  try {
    const response = await fetch(`${API_BASE}/api/recommend-skills`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        job_title: jobTitle,
        skills: skills,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Skill recommendation error:', error);
    throw error;
  }
};

// ── Skill Roadmap ───────────────────────────────────────
export const getSkillRoadmap = async (jobTitle, skills) => {
  try {
    const response = await fetch(`${API_BASE}/api/skill-roadmap`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        job_title: jobTitle,
        skills: skills,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Skill roadmap error:', error);
    throw error;
  }
};

// ── Career Switch Analysis ──────────────────────────────
export const getCareerAnalysis = async (jobFrom, jobTo, skills) => {
  try {
    const response = await fetch(`${API_BASE}/api/career-switch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        job_from: jobFrom,
        job_to: jobTo,
        skills: skills,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Career analysis error:', error);
    throw error;
  }
};

// ── Legacy Functions (for CV Analysis) ──────────────────
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
