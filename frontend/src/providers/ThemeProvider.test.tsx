import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeProvider";

const STORAGE_KEY = "genhealth-theme";

function ThemeConsumer() {
  const { mode, resolvedTheme, setMode } = useTheme();
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <span data-testid="resolved">{resolvedTheme}</span>
      <button type="button" onClick={() => setMode("dark")}>
        Set Dark
      </button>
      <button type="button" onClick={() => setMode("light")}>
        Set Light
      </button>
    </div>
  );
}

function OutsideProvider() {
  useTheme();
  return null;
}

describe("ThemeProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to system mode when nothing is stored", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );
    expect(screen.getByTestId("mode")).toHaveTextContent("system");
  });

  it("loads stored dark theme from localStorage", () => {
    localStorage.setItem(STORAGE_KEY, "dark");
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );
    expect(screen.getByTestId("mode")).toHaveTextContent("dark");
  });

  it("loads stored light theme from localStorage", () => {
    localStorage.setItem(STORAGE_KEY, "light");
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );
    expect(screen.getByTestId("mode")).toHaveTextContent("light");
  });

  it("persists new mode to localStorage when setMode is called", async () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Set Dark" }));
    expect(localStorage.getItem(STORAGE_KEY)).toBe("dark");
    expect(screen.getByTestId("mode")).toHaveTextContent("dark");
  });

  it("resolves to the explicit mode when not system", async () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Set Light" }));
    expect(screen.getByTestId("resolved")).toHaveTextContent("light");
  });

  it("throws when useTheme is used outside ThemeProvider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<OutsideProvider />)).toThrow(
      "useTheme must be used within a ThemeProvider",
    );
    spy.mockRestore();
  });
});
