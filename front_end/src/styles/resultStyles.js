/**
 * Styling utilities for Result components
 * Extracted from inline styles to maintain consistency with Design System
 */

import { designSystem } from '../../styles/designSystem';

export const resultStyles = {
  skillTag: {
    existing: {
      backgroundColor: designSystem.colors.secondary[100],
      color: designSystem.colors.secondary[700],
      padding: '8px 14px',
      borderRadius: designSystem.radius.md,
      fontSize: '13px',
      fontWeight: designSystem.typography.weight.medium,
      border: `1px solid ${designSystem.colors.secondary[300]}`,
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
    },
    recommended: {
      backgroundColor: designSystem.colors.accent[100],
      color: designSystem.colors.accent[700],
      padding: '12px 14px',
      borderRadius: designSystem.radius.md,
      fontSize: '13px',
      fontWeight: designSystem.typography.weight.medium,
      border: `1px solid ${designSystem.colors.accent[300]}`,
    },
  },

  skillItem: {
    padding: '14px',
    backgroundColor: designSystem.colors.accent[50],
    borderLeft: `4px solid ${designSystem.colors.accent[500]}`,
    borderRadius: designSystem.radius.md,
    marginBottom: '12px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },

  badge: {
    fontSize: '12px',
    backgroundColor: designSystem.colors.accent[500],
    color: designSystem.colors.neutral[0],
    padding: '4px 10px',
    borderRadius: '4px',
    fontWeight: designSystem.typography.weight.semibold,
    whiteSpace: 'nowrap',
  },

  roadmapPhase: {
    marginBottom: '28px',
    padding: '18px',
    backgroundColor: designSystem.colors.accent[50],
    borderLeft: `4px solid ${designSystem.colors.accent[500]}`,
    borderRadius: designSystem.radius.md,
  },

  roadmapPhaseTitle: {
    fontSize: '15px',
    fontWeight: designSystem.typography.weight.bold,
    color: designSystem.colors.accent[700],
    margin: '0 0 14px 0',
  },

  taskItem: {
    fontSize: '14px',
    color: designSystem.colors.accent[800],
    marginLeft: '24px',
    marginBottom: '10px',
    position: 'relative',
    lineHeight: 1.5,
    '&:before': {
      content: '"→"',
      position: 'absolute',
      left: '-20px',
      color: designSystem.colors.accent[500],
    },
  },

  recommendationSection: {
    marginTop: '28px',
    padding: '24px',
    backgroundColor: designSystem.colors.secondary[50],
    borderRadius: designSystem.radius.lg,
    border: `1px solid ${designSystem.colors.secondary[200]}`,
  },

  recommendationTitle: {
    fontSize: '18px',
    fontWeight: designSystem.typography.weight.bold,
    color: designSystem.colors.neutral[900],
    marginBottom: '20px',
  },

  jobCard: {
    padding: '16px',
    backgroundColor: designSystem.colors.secondary[100],
    borderLeft: `4px solid ${designSystem.colors.secondary[600]}`,
    borderRadius: designSystem.radius.md,
    marginBottom: '14px',
    transition: designSystem.transition.fast,
  },

  jobHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '10px',
    gap: '12px',
  },

  jobTitle: {
    fontSize: '15px',
    fontWeight: designSystem.typography.weight.semibold,
    color: designSystem.colors.neutral[900],
    margin: '0',
  },

  salary: {
    fontSize: '14px',
    color: designSystem.colors.secondary[700],
    fontWeight: designSystem.typography.weight.bold,
    whiteSpace: 'nowrap',
  },

  timeline: {
    fontSize: '13px',
    color: designSystem.colors.neutral[700],
    marginTop: '6px',
    margin: '0',
  },

  careerInput: {
    marginTop: '16px',
    marginBottom: '16px',
    display: 'flex',
    gap: '12px',
  },

  careerInputField: {
    flex: 1,
    padding: '12px 16px',
    border: `1px solid ${designSystem.colors.neutral[300]}`,
    borderRadius: designSystem.radius.md,
    fontSize: '14px',
    fontFamily: 'inherit',
    transition: designSystem.transition.fast,
    backgroundColor: designSystem.colors.neutral[50],
    '&:focus': {
      outline: 'none',
      borderColor: designSystem.colors.primary[500],
      boxShadow: `0 0 0 3px ${designSystem.colors.primary[100]}`,
    },
  },

  careerButton: {
    padding: '12px 20px',
    backgroundColor: designSystem.colors.primary[600],
    color: designSystem.colors.neutral[0],
    border: 'none',
    borderRadius: designSystem.radius.md,
    fontSize: '14px',
    fontWeight: designSystem.typography.weight.semibold,
    cursor: 'pointer',
    transition: designSystem.transition.base,
  },
};

// Helper function to create skill tags
export const createSkillTag = (type = 'existing') => resultStyles.skillTag[type];

// Helper function for consistent roadmap rendering
export const getRoadmapPhaseStyle = (phaseIndex) => ({
  ...resultStyles.roadmapPhase,
  backgroundColor:
    phaseIndex % 2 === 0 ? designSystem.colors.accent[50] : designSystem.colors.primary[50],
  borderLeftColor:
    phaseIndex % 2 === 0 ? designSystem.colors.accent[500] : designSystem.colors.primary[600],
});
