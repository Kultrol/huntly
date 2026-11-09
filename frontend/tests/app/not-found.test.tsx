import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { expect, it } from "vitest";
import NotFoundPage from "@/app/pages/NotFoundPage";

it("focuses the 404 heading and restores the page title after returning home", () => {
  const originalTitle = document.title;
  render(
    <MemoryRouter initialEntries={["/missing-page"]}>
      <Routes>
        <Route path="/" element={<h1>Home</h1>} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </MemoryRouter>,
  );

  const heading = screen.getByRole("heading", { name: "Page Not Found", level: 1 });
  expect(document.activeElement).toBe(heading);
  expect(document.title).toBe("Page not found | Huntly");

  fireEvent.click(screen.getByRole("link", { name: "Return to Home Page" }));
  expect(screen.getByRole("heading", { name: "Home" })).toBeTruthy();
  expect(document.title).toBe(originalTitle);
});
