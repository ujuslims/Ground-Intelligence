"use client";

import { useEffect } from "react";
import { applyTheme, getStoredTheme } from "@/lib/theme";

/** Applies the viewer's stored theme to <html> on first load. Renders nothing. */
export default function ThemeInit() {
  useEffect(() => {
    applyTheme(getStoredTheme());
  }, []);
  return null;
}
