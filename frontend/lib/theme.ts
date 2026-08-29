"use client";

/**
 * Light / Warm / Dark theme, matching the "Ground Intelligence Look and
 * Feel" design canvas. Applied as a data-theme attribute on <html>; the
 * actual color tokens live in globals.css. Persisted client-side only
 * (localStorage) -- this is a per-viewer display preference, not project
 * data, so it deliberately does not round-trip through the backend.
 */
export type GiTheme = "light" | "warm" | "dark";

const STORAGE_KEY = "gi-theme";
const DEFAULT_THEME: GiTheme = "warm";

export function getStoredTheme(): GiTheme {
  if (typeof window === "undefined") return DEFAULT_THEME;
  const v = window.localStorage.getItem(STORAGE_KEY);
  return v === "light" || v === "warm" || v === "dark" ? v : DEFAULT_THEME;
}

export function applyTheme(theme: GiTheme) {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", theme);
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // localStorage unavailable (private mode, etc.) -- theme still applies for this load.
  }
}
