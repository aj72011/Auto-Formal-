import { motion } from "framer-motion";

export type ThemeMode = "dark" | "light";

interface ThemeToggleProps {
  theme: ThemeMode;
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label="Toggle theme"
      className="flex items-center gap-2 rounded-full border border-border bg-panelAlt px-2.5 py-1.5 text-xs font-semibold text-textMuted shadow-sm transition hover:text-textMain"
    >
      <span className="inline-flex h-4 w-4 items-center justify-center">
        {isDark ? (
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
            <path d="M14.5 3.2a9 9 0 1 0 6.3 15.2 1 1 0 0 0-.9-1.7 7 7 0 0 1-8.9-9.1 1 1 0 0 0-1.7-.9 9 9 0 0 0 5.2 16.5 9 9 0 0 0 0-18z" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
            <path d="M12 5a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V6a1 1 0 0 1 1-1zm0 12a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1zm7-5a1 1 0 1 1 0 2h-1a1 1 0 1 1 0-2h1zM7 12a1 1 0 1 1 0 2H6a1 1 0 1 1 0-2h1zm9.66-4.95a1 1 0 0 1 1.41 1.41l-.71.71a1 1 0 0 1-1.41-1.41l.71-.71zM8.05 15.54a1 1 0 0 1 1.41 1.41l-.71.71a1 1 0 0 1-1.41-1.41l.71-.71zm9.32 2.12a1 1 0 0 1-1.41 0l-.71-.71a1 1 0 0 1 1.41-1.41l.71.71a1 1 0 0 1 0 1.41zM8.76 8.47a1 1 0 1 1-1.41-1.41l.71-.71a1 1 0 0 1 1.41 1.41l-.71.71zM12 9a3 3 0 1 1 0 6 3 3 0 0 1 0-6z" />
          </svg>
        )}
      </span>
      <div className="relative h-5 w-10 rounded-full border border-border bg-surface">
        <motion.span
          layout
          transition={{ duration: 0.2 }}
          className={`absolute top-0.5 h-4 w-4 rounded-full ${
            isDark ? "left-5 bg-accent" : "left-0.5 bg-warning"
          }`}
        />
      </div>
    </button>
  );
}
