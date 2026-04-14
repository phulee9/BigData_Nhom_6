import { designSystem } from './designSystem';

const primary = designSystem.colors.primary;
const secondary = designSystem.colors.secondary;
const neutral = designSystem.colors.neutral;
const accent = designSystem.colors.accent;

export const styles = {
  // Layout
  container: {
    minHeight: '100vh',
    fontFamily: designSystem.typography.body,
    position: 'relative',
    overflow: 'hidden',
    backgroundColor: neutral[50],
  },
  backgroundGradient: {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    background: `linear-gradient(135deg, ${neutral[50]} 0%, ${neutral[100]} 50%, ${primary[50]} 100%)`,
    backgroundSize: '400% 400%',
    animation: 'gradientShift 15s ease infinite',
    zIndex: 0,
  },
  content: {
    position: 'relative',
    zIndex: 1,
    padding: '60px 20px',
    maxWidth: '1000px',
    margin: '0 auto',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
  },
  step: {
    animation: 'slideUp 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
  },

  // Header
  header: {
    textAlign: 'center',
    marginBottom: '56px',
  },
  logoSection: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '24px',
  },
  logoIcon: {
    fontSize: '56px',
    marginRight: '16px',
  },
  title: {
    fontSize: '48px',
    fontWeight: designSystem.typography.weight.bold,
    color: neutral[900],
    margin: '0 0 16px 0',
    letterSpacing: '-1px',
    lineHeight: 1.1,
  },
  subtitle: {
    fontSize: '18px',
    color: neutral[600],
    margin: '0',
    fontWeight: designSystem.typography.weight.normal,
    lineHeight: 1.5,
  },

  // Card
  card: {
    background: neutral[0],
    backdropFilter: 'blur(20px)',
    border: `1px solid ${neutral[200]}`,
    borderRadius: '16px',
    padding: '48px',
    boxShadow: designSystem.shadow.lg,
    transition: designSystem.transition.base,
  },
  backButton: {
    display: 'flex',
    alignItems: 'center',
    background: 'transparent',
    border: 'none',
    color: neutral[600],
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: designSystem.typography.weight.medium,
    marginBottom: '28px',
    transition: designSystem.transition.fast,
    padding: '8px 0',
    '&:hover': {
      color: primary[600],
    },
  },

  // Tabs
  tabContainer: {
    display: 'flex',
    gap: '12px',
    marginBottom: '40px',
    borderBottom: `1px solid ${neutral[200]}`,
  },
  tab: {
    display: 'flex',
    alignItems: 'center',
    padding: '16px 20px',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: designSystem.typography.weight.medium,
    transition: designSystem.transition.base,
    color: neutral[600],
    borderBottom: `2px solid transparent`,
  },
  tabActive: {
    color: primary[600],
    borderBottomColor: primary[600],
  },
  tabInactive: {
    color: neutral[400],
    '&:hover': {
      color: neutral[700],
    },
  },

  // Upload Section
  uploadSection: {
    marginBottom: '40px',
  },
  dropZone: {
    border: `2px dashed ${primary[300]}`,
    borderRadius: '12px',
    padding: '64px 32px',
    textAlign: 'center',
    transition: designSystem.transition.base,
    backgroundColor: primary[50],
    marginBottom: '24px',
    cursor: 'pointer',
    '&:hover': {
      backgroundColor: primary[100],
      borderColor: primary[400],
    },
  },
  dropZoneLabel: {
    cursor: 'pointer',
    display: 'block',
  },
  dropZoneText: {
    fontSize: '18px',
    color: neutral[900],
    margin: '16px 0 8px 0',
    fontWeight: designSystem.typography.weight.semibold,
  },
  dropZoneSubtext: {
    fontSize: '14px',
    color: neutral[600],
    margin: '0',
  },
  highlight: {
    color: primary[600],
    fontWeight: designSystem.typography.weight.bold,
  },
  hiddenInput: {
    display: 'none',
  },
  fileSelected: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '14px 16px',
    backgroundColor: secondary[100],
    border: `1px solid ${secondary[300]}`,
    borderRadius: '8px',
    color: secondary[700],
    fontSize: '14px',
    fontWeight: designSystem.typography.weight.medium,
  },

  // Manual Input
  manualInputSection: {
    marginBottom: '40px',
  },
  textarea: {
    width: '100%',
    minHeight: '220px',
    padding: '16px',
    backgroundColor: neutral[50],
    border: `1px solid ${neutral[300]}`,
    borderRadius: '8px',
    color: neutral[900],
    fontSize: '14px',
    fontFamily: 'inherit',
    resize: 'vertical',
    outline: 'none',
    transition: designSystem.transition.fast,
    '&:focus': {
      borderColor: primary[500],
      boxShadow: `0 0 0 3px ${primary[100]}`,
    },
  },

  // Buttons
  primaryButton: {
    width: '100%',
    padding: '14px 24px',
    backgroundColor: primary[600],
    color: neutral[0],
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: designSystem.typography.weight.semibold,
    cursor: 'pointer',
    transition: designSystem.transition.base,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 2px 8px ${primary[600]}33`,
    '&:hover': {
      backgroundColor: primary[700],
      boxShadow: `0 4px 12px ${primary[600]}50`,
    },
    '&:active': {
      backgroundColor: primary[800],
    },
  },
  buttonDisabled: {
    backgroundColor: neutral[400],
    color: neutral[600],
    cursor: 'not-allowed',
    opacity: 0.6,
    boxShadow: 'none',
  },
  secondaryButton: {
    padding: '12px 24px',
    backgroundColor: 'transparent',
    border: `2px solid ${neutral[300]}`,
    color: neutral[700],
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: designSystem.typography.weight.semibold,
    cursor: 'pointer',
    transition: designSystem.transition.base,
    '&:hover': {
      backgroundColor: neutral[100],
      borderColor: neutral[400],
    },
  },

  // Profile
  profileSection: {
    display: 'flex',
    gap: '28px',
    alignItems: 'flex-start',
    marginBottom: '40px',
  },
  profileAvatar: {
    width: '100px',
    height: '100px',
    borderRadius: '14px',
    backgroundColor: primary[600],
    color: neutral[0],
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '40px',
    fontWeight: designSystem.typography.weight.bold,
    flexShrink: 0,
    boxShadow: `0 4px 12px ${primary[600]}33`,
  },
  profileName: {
    fontSize: '28px',
    fontWeight: designSystem.typography.weight.bold,
    color: neutral[900],
    margin: '0 0 8px 0',
  },
  profileEmail: {
    fontSize: '14px',
    color: neutral[600],
    margin: '0 0 6px 0',
  },
  profilePhone: {
    fontSize: '14px',
    color: neutral[600],
    margin: '0',
  },
  divider: {
    height: '1px',
    backgroundColor: neutral[200],
    margin: '40px 0',
  },

  // Section
  summarySection: {
    marginBottom: '40px',
  },
  sectionTitle: {
    fontSize: '16px',
    fontWeight: designSystem.typography.weight.bold,
    color: neutral[900],
    margin: '0 0 20px 0',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  summaryText: {
    fontSize: '15px',
    color: neutral[700],
    lineHeight: 1.6,
    margin: '0',
  },
  skillsSection: {
    marginBottom: '40px',
  },
  skillGroup: {
    marginBottom: '28px',
  },
  skillGroupTitle: {
    fontSize: '14px',
    fontWeight: designSystem.typography.weight.semibold,
    color: neutral[700],
    margin: '0 0 14px 0',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  skillsList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
  },
  skillTag: {
    padding: '8px 14px',
    backgroundColor: primary[100],
    color: primary[700],
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: designSystem.typography.weight.medium,
    border: `1px solid ${primary[200]}`,
    transition: designSystem.transition.fast,
    cursor: 'default',
    '&:hover': {
      backgroundColor: primary[200],
    },
  },

  // Options Grid
  optionsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '32px',
    marginBottom: '32px',
  },
  optionCard: {
    background: neutral[50],
    border: `2px solid ${neutral[200]}`,
    borderRadius: '14px',
    padding: '32px 28px',
    cursor: 'pointer',
    transition: designSystem.transition.base,
    display: 'flex',
    flexDirection: 'column',
    '&:hover': {
      borderColor: primary[400],
      backgroundColor: neutral[0],
      boxShadow: designSystem.shadow.md,
      transform: 'translateY(-4px)',
    },
  },
  optionIcon: {
    fontSize: '56px',
    marginBottom: '20px',
  },
  optionTitle: {
    fontSize: '18px',
    fontWeight: designSystem.typography.weight.bold,
    color: neutral[900],
    margin: '0 0 12px 0',
  },
  optionDescription: {
    fontSize: '14px',
    color: neutral[700],
    margin: '0 0 auto 0',
    lineHeight: 1.6,
  },
  optionFooter: {
    marginTop: '20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    color: neutral[600],
    fontSize: '12px',
    paddingTop: '16px',
    borderTop: `1px solid ${neutral[200]}`,
  },
  optionLabel: {
    fontWeight: designSystem.typography.weight.semibold,
  },

  // Loading
  loadingOverlay: {
    position: 'fixed',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '24px',
    zIndex: 100,
  },
  spinner: {
    width: '56px',
    height: '56px',
    border: `4px solid ${neutral[200]}`,
    borderTop: `4px solid ${primary[600]}`,
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },

  // Skills & Recommendations
  skillItem: {
    padding: '18px',
    backgroundColor: primary[50],
    borderLeft: `4px solid ${primary[600]}`,
    borderRadius: '8px',
    marginBottom: '16px',
    transition: designSystem.transition.fast,
  },
  skillItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  skillItemName: {
    fontSize: '15px',
    fontWeight: designSystem.typography.weight.semibold,
    color: neutral[900],
    margin: '0',
  },
  badge: {
    padding: '5px 12px',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: designSystem.typography.weight.bold,
    color: neutral[0],
  },
  skillItemReason: {
    fontSize: '14px',
    color: neutral[700],
    margin: '0',
  },
  phaseBlock: {
    marginBottom: '28px',
    padding: '20px',
    backgroundColor: '#fef3c7',
    border: `1px solid #fcd34d`,
    borderRadius: '10px',
    transition: designSystem.transition.fast,
  },
  phaseTitle: {
    fontSize: '15px',
    fontWeight: designSystem.typography.weight.bold,
    color: '#b45309',
    margin: '0 0 16px 0',
  },
  taskList: {
    listStyle: 'none',
    padding: '0',
    margin: '0',
  },
  taskItem: {
    fontSize: '14px',
    color: '#92400e',
    margin: '10px 0',
    paddingLeft: '24px',
    position: 'relative',
    lineHeight: 1.5,
  },

  // Career Analysis
  careerSection: {
    marginBottom: '0',
    padding: '20px',
    backgroundColor: primary[50],
    borderRadius: '10px',
    border: `1px solid ${primary[200]}`,
  },
  careerLabel: {
    fontSize: '12px',
    fontWeight: designSystem.typography.weight.semibold,
    color: neutral[700],
    margin: '0 0 8px 0',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  careerValue: {
    fontSize: '18px',
    color: primary[700],
    margin: '0',
    fontWeight: designSystem.typography.weight.bold,
  },

  // Recommendations
  recommendationsTitle: {
    fontSize: '18px',
    fontWeight: designSystem.typography.weight.bold,
    color: neutral[900],
    margin: '0 0 28px 0',
  },
  recommendationCard: {
    padding: '20px',
    backgroundColor: secondary[100],
    border: `2px solid ${secondary[300]}`,
    borderLeft: `4px solid ${secondary[600]}`,
    borderRadius: '10px',
    marginBottom: '18px',
    transition: designSystem.transition.fast,
    '&:hover': {
      boxShadow: designSystem.shadow.md,
    },
  },
  recHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '10px',
    gap: '12px',
  },
  recTitle: {
    fontSize: '16px',
    fontWeight: designSystem.typography.weight.semibold,
    color: neutral[900],
    margin: '0',
  },
  recSalary: {
    fontSize: '14px',
    color: secondary[700],
    fontWeight: designSystem.typography.weight.bold,
    whiteSpace: 'nowrap',
  },
  recTimeline: {
    fontSize: '13px',
    color: neutral[700],
    margin: '8px 0',
    fontWeight: designSystem.typography.weight.normal,
  },
  recRequirements: {
    fontSize: '13px',
    color: neutral[700],
    margin: '4px 0 0 0',
    fontWeight: designSystem.typography.weight.normal,
  },
  actionButtons: {
    display: 'flex',
    gap: '16px',
    marginTop: '40px',
    paddingTop: '32px',
    borderTop: `1px solid ${neutral[200]}`,
  },
};
