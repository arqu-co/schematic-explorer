/**
 * SVG icon components for the application.
 */

interface IconProps {
  /** Icon size in pixels (default: 16) */
  size?: number;
  /** Additional CSS class */
  className?: string;
}

/**
 * Sun icon - used for light theme indication.
 */
export function SunIcon({ size = 16, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
    >
      <path d="M8 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-1 0v-1A.5.5 0 0 1 8 1zm0 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm6.5-2.5a.5.5 0 0 1 0 1h-1a.5.5 0 0 1 0-1h1zm-12 0a.5.5 0 0 1 0 1h-1a.5.5 0 0 1 0-1h1zm9.743-4.036a.5.5 0 0 1 0 .707l-.707.707a.5.5 0 1 1-.707-.707l.707-.707a.5.5 0 0 1 .707 0zm-8.486 6.072a.5.5 0 0 1 0 .707l-.707.707a.5.5 0 1 1-.707-.707l.707-.707a.5.5 0 0 1 .707 0zm7.779 0a.5.5 0 0 1 .707 0l.707.707a.5.5 0 1 1-.707.707l-.707-.707a.5.5 0 0 1 0-.707zm-8.486-6.072a.5.5 0 0 1 .707 0l.707.707a.5.5 0 0 1-.707.707l-.707-.707a.5.5 0 0 1 0-.707zM8 13a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-1 0v-1A.5.5 0 0 1 8 13z" />
    </svg>
  );
}

/**
 * Moon icon - used for dark theme indication.
 */
export function MoonIcon({ size = 16, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
    >
      <path d="M6 0.278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278z" />
    </svg>
  );
}

interface ThemeToggleIconProps extends IconProps {
  /** Current theme */
  theme: 'light' | 'dark';
}

/**
 * Theme toggle icon - shows sun when dark (to switch to light),
 * shows moon when light (to switch to dark).
 */
export function ThemeToggleIcon({ theme, size = 16, className }: ThemeToggleIconProps) {
  // When in dark mode, show sun (to switch to light)
  // When in light mode, show moon (to switch to dark)
  return theme === 'dark' ? (
    <SunIcon size={size} className={className} />
  ) : (
    <MoonIcon size={size} className={className} />
  );
}
