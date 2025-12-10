/**
 * Custom hook for managing theme state.
 */

import { useState, useCallback } from 'react';

type Theme = 'light' | 'dark';

const THEME_STORAGE_KEY = 'theme';

interface UseThemeReturn {
  /** Current theme */
  theme: Theme;
  /** Toggle between light and dark theme */
  toggleTheme: () => void;
}

/**
 * Get the initial theme from localStorage or system preference.
 */
function getInitialTheme(): Theme {
  if (typeof window === 'undefined') {
    return 'dark';
  }

  const saved = localStorage.getItem(THEME_STORAGE_KEY);
  if (saved === 'light' || saved === 'dark') {
    return saved;
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Hook for managing theme state with localStorage persistence.
 *
 * Initializes from localStorage or system preference.
 * Persists changes to localStorage.
 */
export function useTheme(): UseThemeReturn {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const newTheme = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem(THEME_STORAGE_KEY, newTheme);
      return newTheme;
    });
  }, []);

  return {
    theme,
    toggleTheme,
  };
}
