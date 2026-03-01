import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ThemeProvider } from "../../providers/ThemeProvider";
import { Layout } from "./Layout";

function renderLayout(children = <div>Page Content</div>) {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <Layout>{children}</Layout>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe("Layout", () => {
  it("renders children", () => {
    renderLayout(<p>Hello World</p>);
    expect(screen.getByText("Hello World")).toBeInTheDocument();
  });

  it("renders GenHealth brand link", () => {
    renderLayout();
    expect(screen.getByText("GenHealth")).toBeInTheDocument();
  });

  it("renders Orders nav link", () => {
    renderLayout();
    expect(screen.getByRole("link", { name: "Orders" })).toBeInTheDocument();
  });

  it("renders Activity nav link", () => {
    renderLayout();
    expect(screen.getByRole("link", { name: "Activity" })).toBeInTheDocument();
  });

  it("renders theme toggle button", () => {
    renderLayout();
    expect(screen.getByRole("button", { name: "Toggle theme" })).toBeInTheDocument();
  });

  it("toggles theme label when toggle button is clicked", async () => {
    renderLayout();
    const toggle = screen.getByRole("button", { name: "Toggle theme" });
    const initialLabel = toggle.textContent;
    await userEvent.click(toggle);
    expect(toggle.textContent).not.toBe(initialLabel);
  });
});
