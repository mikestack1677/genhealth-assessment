import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { useTheme } from "../../providers/ThemeProvider";
import styles from "./Layout.module.css";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { resolvedTheme, setMode } = useTheme();

  const toggleTheme = () => {
    setMode(resolvedTheme === "dark" ? "light" : "dark");
  };

  return (
    <div className={styles.wrapper}>
      <nav className={styles.nav} aria-label="Main navigation">
        <Link to="/" className={styles.brand}>
          GenHealth
        </Link>
        <div className={styles.links}>
          <NavLink
            to="/"
            end
            className={({ isActive }) => (isActive ? styles.linkActive : styles.link)}
          >
            Orders
          </NavLink>
          <NavLink
            to="/activity"
            className={({ isActive }) => (isActive ? styles.linkActive : styles.link)}
          >
            Activity
          </NavLink>
        </div>
        <button
          type="button"
          onClick={toggleTheme}
          className={styles.themeToggle}
          aria-label="Toggle theme"
        >
          {resolvedTheme === "dark" ? "Light" : "Dark"}
        </button>
      </nav>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
