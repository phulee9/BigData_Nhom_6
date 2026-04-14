/**
 * Design System for CV Analyzer Pro
 * Professional SaaS theme with modern aesthetics
 */

export const designSystem = {
  // Color Palette - Professional & Modern
  colors: {
    // Primary: Professional Blue
    primary: {
      50: '#f0f7ff',
      100: '#e0effe',
      200: '#bae6fd',
      300: '#7dd3fc',
      400: '#38bdf8',
      500: '#0ea5e9',
      600: '#0284c7',
      700: '#0369a1',
      800: '#075985',
      900: '#0c3d66',
    },
    // Secondary: Corporate Green (for success states)
    secondary: {
      50: '#f0fdf4',
      100: '#dcfce7',
      200: '#bbedf0',
      300: '#86efac',
      400: '#4ade80',
      500: '#22c55e',
      600: '#16a34a',
      700: '#15803d',
      800: '#166534',
      900: '#145231',
    },
    // Accent: Warm Orange (for CTAs)
    accent: {
      50: '#fff7ed',
      100: '#ffedd5',
      200: '#fed7aa',
      300: '#fdba74',
      400: '#fb923c',
      500: '#f97316',
      600: '#ea580c',
      700: '#c2410c',
      800: '#92400e',
      900: '#78350f',
    },
    // Neutral: Gray Scale
    neutral: {
      0: '#ffffff',
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      300: '#d1d5db',
      400: '#9ca3af',
      500: '#6b7280',
      600: '#4b5563',
      700: '#374151',
      800: '#1f2937',
      900: '#111827',
    },
    // Semantic
    success: '#22c55e',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#0ea5e9',
  },

  // Typography
  typography: {
    // Font families
    display: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    body: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',

    // Font sizes (mobile-first)
    fontSize: {
      xs: '12px',
      sm: '14px',
      base: '16px',
      lg: '18px',
      xl: '20px',
      '2xl': '24px',
      '3xl': '30px',
      '4xl': '36px',
      '5xl': '48px',
    },

    // Font weights
    weight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
      extrabold: 800,
    },

    // Line heights
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.75,
      loose: 2,
    },

    // Letter spacing
    letterSpacing: {
      tight: '-0.5px',
      normal: '0px',
      wide: '0.5px',
      wider: '1px',
    },
  },

  // Spacing system (8px base)
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
    '2xl': '32px',
    '3xl': '48px',
    '4xl': '64px',
  },

  // Border radius
  radius: {
    none: '0px',
    xs: '2px',
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    '2xl': '20px',
    full: '9999px',
  },

  // Shadows
  shadow: {
    none: 'none',
    xs: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    sm: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.05)',
  },

  // Transitions & Animations
  transition: {
    fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
    base: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
    slow: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
  },

  // Z-index scale
  zIndex: {
    hide: -1,
    auto: 'auto',
    base: 0,
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modal: 1040,
    popover: 1060,
    tooltip: 1070,
  },

  // Component-level tokens
  components: {
    button: {
      base: {
        padding: '10px 16px',
        fontSize: '14px',
        fontWeight: 500,
        borderRadius: '8px',
        border: 'none',
        cursor: 'pointer',
        transition: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        fontFamily: 'Inter, sans-serif',
      },
      primary: {
        backgroundColor: '#0ea5e9',
        color: '#ffffff',
        boxShadow: '0 1px 3px 0 rgba(14, 165, 233, 0.3)',
        '&:hover': {
          backgroundColor: '#0284c7',
          boxShadow: '0 4px 6px -1px rgba(14, 165, 233, 0.4)',
        },
        '&:active': {
          backgroundColor: '#0369a1',
        },
      },
      secondary: {
        backgroundColor: '#f3f4f6',
        color: '#1f2937',
        border: '1px solid #e5e7eb',
        '&:hover': {
          backgroundColor: '#e5e7eb',
        },
      },
      danger: {
        backgroundColor: '#ef4444',
        color: '#ffffff',
        '&:hover': {
          backgroundColor: '#dc2626',
        },
      },
      disabled: {
        backgroundColor: '#d1d5db',
        color: '#9ca3af',
        cursor: 'not-allowed',
        opacity: 0.6,
      },
    },

    input: {
      base: {
        padding: '10px 12px',
        fontSize: '14px',
        borderRadius: '8px',
        border: '1px solid #d1d5db',
        fontFamily: 'Inter, sans-serif',
        transition: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
        '&:focus': {
          outline: 'none',
          borderColor: '#0ea5e9',
          boxShadow: '0 0 0 3px rgba(14, 165, 233, 0.1)',
        },
        '&::placeholder': {
          color: '#9ca3af',
        },
      },
    },

    card: {
      base: {
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
        padding: '20px',
        transition: '200ms ease',
      },
      hover: {
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
      },
    },

    tab: {
      base: {
        padding: '10px 16px',
        fontSize: '14px',
        fontWeight: 500,
        fontFamily: 'Inter, sans-serif',
        border: 'none',
        cursor: 'pointer',
        transition: '200ms ease',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        borderBottom: '2px solid transparent',
      },
      active: {
        color: '#0ea5e9',
        borderBottomColor: '#0ea5e9',
      },
      inactive: {
        color: '#6b7280',
        '&:hover': {
          color: '#374151',
        },
      },
    },

    badge: {
      base: {
        display: 'inline-flex',
        alignItems: 'center',
        fontSize: '12px',
        fontWeight: 600,
        fontFamily: 'Inter, sans-serif',
        padding: '4px 10px',
        borderRadius: '6px',
      },
      success: {
        backgroundColor: '#dcfce7',
        color: '#15803d',
      },
      warning: {
        backgroundColor: '#fef3c7',
        color: '#b45309',
      },
      error: {
        backgroundColor: '#fee2e2',
        color: '#dc2626',
      },
      info: {
        backgroundColor: '#e0effe',
        color: '#0369a1',
      },
    },
  },
};

// Utility function to merge styles
export const mergeStyles = (...styles) => {
  return Object.assign({}, ...styles);
};

// Helper function for responsive design
export const responsive = {
  mobile: {
    maxWidth: '640px',
  },
  tablet: {
    minWidth: '640px',
    maxWidth: '1024px',
  },
  desktop: {
    minWidth: '1024px',
  },
};
