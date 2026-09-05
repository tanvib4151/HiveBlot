'use client';

import { useSyncExternalStore } from 'react';

type Theme = 'light' | 'dark';

const THEME_KEY = 'hiveblot-theme';

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  localStorage.setItem(THEME_KEY, theme);
  window.dispatchEvent(new Event('hiveblot-theme-change'));
}

function subscribeToTheme(onChange: () => void) {
  window.addEventListener('hiveblot-theme-change', onChange);
  window.addEventListener('storage', onChange);
  return () => {
    window.removeEventListener('hiveblot-theme-change', onChange);
    window.removeEventListener('storage', onChange);
  };
}

function getThemeSnapshot(): Theme {
  return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
}

function SunIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" focusable="false">
      <circle cx="10" cy="10" r="3.2" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.35 4.35l1.4 1.4M14.25 14.25l1.4 1.4M15.65 4.35l-1.4 1.4M5.75 14.25l-1.4 1.4" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" focusable="false">
      <path d="M15.6 12.9A6.4 6.4 0 0 1 7.1 4.4 6.4 6.4 0 1 0 15.6 12.9Z" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.5" />
    </svg>
  );
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeToTheme, getThemeSnapshot, () => null);

  const selectTheme = (nextTheme: Theme) => {
    applyTheme(nextTheme);
  };

  return (
    <div className="hb-theme-toggle" role="group" aria-label="Color theme">
      <button
        type="button"
        className={theme === 'light' ? 'is-active' : ''}
        onClick={() => selectTheme('light')}
        aria-pressed={theme === 'light'}
        aria-label="Use light theme"
      >
        <SunIcon />
        <span>Light</span>
      </button>
      <button
        type="button"
        className={theme === 'dark' ? 'is-active' : ''}
        onClick={() => selectTheme('dark')}
        aria-pressed={theme === 'dark'}
        aria-label="Use dark theme"
      >
        <MoonIcon />
        <span>Dark</span>
      </button>
    </div>
  );
}
